import gzip
import io
import json
import logging
import logging.config
import threading
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
import requests
import yaml
from pydantic import BaseModel, SecretStr
from requests.adapters import BaseAdapter

from nsls2api.infrastructure.logging import REDACTED
from nsls2api.infrastructure.loki import (
    SerializedLokiHandler,
    _secret_forms,
    loki_handler,
)

URL = "https://loki.test/loki/api/v1/push"
LOG_CONFIG = Path(__file__).parents[4] / "uvicorn_log_config.yml"
LOGGERS = ("uvicorn.error", "uvicorn.access")

# Not a real key: the shape is all the redaction looks at.
FAKE_KEY = "nsls2-api-" + "0123456789abcdef" * 4
# Not real credentials either. The PASS key has characters a URL encodes.
PASS_KEY = "Pa55/Key+Value=0123"
MONGODB_PASSWORD = "m0ngo@pass"
MONGODB_DSN = "mongodb://nsls2api:m0ngo%40pass@db1.test:27017,db2.test:27017/pytest"


class Recorder(BaseAdapter):
    """requests adapter that records each push, so nothing leaves the host."""

    def __init__(self):
        super().__init__()
        self.requests: list[requests.PreparedRequest] = []
        self.timeouts: list = []
        self.status = 204

    def send(self, request, **kwargs):
        self.requests.append(request)
        self.timeouts.append(kwargs.get("timeout"))
        resp = requests.Response()
        resp.status_code = self.status
        resp.reason = ""
        resp.url = request.url
        resp._content = b""
        resp.request = request
        return resp

    def close(self):
        pass

    def streams(self) -> list[dict]:
        return [
            s
            for r in self.requests
            for s in json.loads(gzip.decompress(r.body))["streams"]
        ]

    def lines(self) -> list[dict]:
        return [json.loads(v[1]) for s in self.streams() for v in s["values"]]


@pytest.fixture
def loki_env(monkeypatch):
    """Configure Loki through the environment and keep every push off the network.

    Every requests session made during the test (the handler's, made when the log
    configuration is loaded) gets the recording adapter, so neither its sender nor
    its send at exit reaches the network. Environment variables override the settings
    file (pytest.env under pytest).
    """
    session_factory = requests.Session

    def recording_session():
        session = session_factory()
        recorder = Recorder()
        session.mount("http://", recorder)
        session.mount("https://", recorder)
        return session

    monkeypatch.setattr(requests, "Session", recording_session)
    monkeypatch.setenv("LOKI_URL", URL)
    monkeypatch.setenv("LOKI_PUSH_SECRET", "s3cret")
    monkeypatch.setenv("LOKI_JOB", "nsls2api")
    monkeypatch.setenv("LOKI_ENVIRONMENT", "test")
    monkeypatch.setenv("LOKI_HOST", "api-test.nsls2.bnl.gov")
    # Credentials that are not shaped like an API key (see test_credentials_...).
    monkeypatch.setenv("PASS_API_KEY", PASS_KEY)
    monkeypatch.setenv("MONGODB_DSN", MONGODB_DSN)
    return monkeypatch


@pytest.fixture
def configured(loki_env):
    """Load uvicorn_log_config.yml as uvicorn does, and restore the loggers after."""
    saved = {
        name: (lg.handlers[:], lg.level, lg.propagate)
        for name in LOGGERS
        for lg in [logging.getLogger(name)]
    }
    logging.config.dictConfig(yaml.safe_load(LOG_CONFIG.read_text()))
    (handler,) = {
        h
        for name in LOGGERS
        for h in logging.getLogger(name).handlers
        if isinstance(h, SerializedLokiHandler)
    }
    yield handler, handler.request.session.get_adapter(URL)
    for name, (handlers, level, propagate) in saved.items():
        lg = logging.getLogger(name)
        lg.handlers[:] = handlers
        lg.setLevel(level)
        lg.propagate = propagate


@pytest.mark.parametrize("unset", ["LOKI_URL", "LOKI_PUSH_SECRET"])
def test_does_nothing_unless_url_and_secret_are_set(loki_env, unset):
    loki_env.setenv(unset, "")
    assert type(loki_handler()) is logging.NullHandler


def test_does_nothing_when_the_app_settings_are_invalid(loki_env):
    # The app reports the validation error itself when it is imported.
    loki_env.setenv("MONGODB_DSN", "not a dsn")
    assert type(loki_handler()) is logging.NullHandler


def test_only_uvicorn_error_logger_uses_loki_handler(configured):
    handler, _ = configured
    assert handler in logging.getLogger("uvicorn.error").handlers
    assert handler not in logging.getLogger("uvicorn.access").handlers


def test_access_log_is_not_pushed_to_loki(configured):
    handler, recorder = configured
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "10.0.0.1:5000",
        "GET",
        f"/v1/proposals/?api_key={FAKE_KEY}",
        "1.1",
        200,
    )
    handler._send()

    assert recorder.requests == []


@pytest.mark.parametrize("level", [logging.WARNING, logging.ERROR, logging.CRITICAL])
def test_tracebacks_are_pushed_at_every_level_with_the_key_redacted(configured, level):
    handler, recorder = configured
    try:
        raise ValueError(f"bad request /v1/x?api_key={FAKE_KEY}")
    except ValueError:
        logging.getLogger("uvicorn.error.nsls2api").log(level, "failed", exc_info=True)
    logging.getLogger("uvicorn.error.nsls2api").log(level, "no exception")
    handler._send()

    body = b"".join(gzip.decompress(r.body) for r in recorder.requests)
    assert FAKE_KEY.encode() not in body
    lines = {line["message"]: line for line in recorder.lines()}
    assert "ValueError: bad request" in lines["failed"]["stacktrace"]
    assert REDACTED in lines["failed"]["stacktrace"]
    assert not lines["no exception"].get("stacktrace")


def test_extra_fields_are_redacted(configured):
    handler, recorder = configured
    logging.getLogger("uvicorn.error.nsls2api").info(
        "lookup",
        extra={
            "note": f"from /v1/x?api_key={FAKE_KEY}",
            "color_message": "\x1b[1mlookup\x1b[0m",
        },
    )
    handler._send()

    (line,) = recorder.lines()
    assert line["note"] == f"from /v1/x?api_key={REDACTED}"
    assert "color_message" not in line


def test_values_under_api_key_field_names_are_redacted(configured):
    # An encoded key is not shaped like one, so only the field name gives it away.
    encoded = "%6E" + FAKE_KEY[1:]
    handler, recorder = configured
    logging.getLogger("uvicorn.error.nsls2api").info(
        "lookup",
        extra={"api_key": encoded, "params": {"API%5FKEY": encoded, "page": 2}},
    )
    handler._send()

    assert encoded.encode() not in gzip.decompress(recorder.requests[0].body)
    (line,) = recorder.lines()
    assert line["api_key"] == REDACTED
    assert line["params"] == {"API%5FKEY": REDACTED, "page": 2}


def test_nested_extra_fields_are_redacted(configured):
    handler, recorder = configured
    logging.getLogger("uvicorn.error.nsls2api").info(
        "lookup",
        extra={
            "params": {"api_key": FAKE_KEY, "page": 2},
            "urls": (f"/v1/x?api_key={FAKE_KEY}",),
        },
    )
    handler._send()

    assert FAKE_KEY.encode() not in gzip.decompress(recorder.requests[0].body)
    (line,) = recorder.lines()
    assert line["params"] == {"api_key": REDACTED, "page": 2}
    assert line["urls"] == [f"/v1/x?api_key={REDACTED}"]


def test_unserializable_extra_does_not_lose_the_batch(configured):
    class Opaque:
        def __str__(self):
            return f"Opaque /v1/x?api_key={FAKE_KEY}"

    handler, recorder = configured
    log = logging.getLogger("uvicorn.error.nsls2api")
    log.info("before")
    log.info("opaque", extra={"obj": Opaque()})
    handler._send()

    lines = {line["message"]: line for line in recorder.lines()}
    assert set(lines) == {"before", "opaque"}
    assert lines["opaque"]["obj"] == f"Opaque /v1/x?api_key={REDACTED}"


def test_pushes_have_a_network_timeout(configured):
    handler, recorder = configured
    logging.getLogger("uvicorn.error.nsls2api").warning("hello")
    handler._send()
    assert recorder.timeouts and all(t == (5.0, 10.0) for t in recorder.timeouts)


def test_concurrent_sends_do_not_hang_on_the_last_record(configured):
    # The sender and the send at exit can drain at the same time. Hold both right
    # after they see the last record queued: unserialized, one takes it and the other
    # blocks in get() forever.
    handler, recorder = configured
    handler._send()
    logging.getLogger("uvicorn.error.nsls2api").warning("last")

    callers: set[threading.Thread] = set()
    both_saw_it = threading.Barrier(2)
    queue_empty = handler.buffer.empty

    def empty():
        result = queue_empty()
        if threading.current_thread() in callers and not result:
            try:
                both_saw_it.wait(timeout=0.5)
            except threading.BrokenBarrierError:
                pass
        return result

    handler.buffer.empty = empty
    threads = [threading.Thread(target=handler._send, daemon=True) for _ in range(2)]
    callers.update(threads)
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    handler.buffer.empty = queue_empty
    if any(t.is_alive() for t in threads):
        handler.buffer.put(None)  # release the stuck caller
        pytest.fail("a concurrent _send() blocked on an empty queue")
    assert "last" in [line["message"] for line in recorder.lines()]


def test_failed_pushes_are_reported_on_stderr_not_in_loki(configured):
    handler, recorder = configured
    # pytest swaps stderr between setup and the test, so read the report directly.
    (report,) = [
        h for h in handler.debug_logger.handlers if type(h) is logging.StreamHandler
    ]
    report.setStream(io.StringIO())
    recorder.status = 403
    logging.getLogger("uvicorn.error.nsls2api").warning("hello")
    handler._send()
    err = report.stream.getvalue()
    assert "403" in err
    assert "s3cret" not in err
    assert "Traceback" not in err
    assert err.count("\n") == 1
    # The failure report is not queued for the next push.
    assert handler.buffer.empty()


def test_failure_reports_mask_the_push_secret(loki_env):
    # requests rejects a header value with a newline, and quotes it in its error.
    loki_env.setenv("LOKI_PUSH_SECRET", "push-s3cret\n")
    handler = loki_handler()
    (report,) = [
        h for h in handler.debug_logger.handlers if type(h) is logging.StreamHandler
    ]
    report.setStream(io.StringIO())
    logger = logging.getLogger("test_loki.secret")
    logger.addHandler(handler)
    try:
        logger.warning("hello")
        handler._send()
    finally:
        logger.removeHandler(handler)

    err = report.stream.getvalue()
    assert "header value" in err
    assert "push-s3cret" not in err
    assert REDACTED in err


def test_credentials_in_settings_are_masked_before_delivery(configured):
    handler, recorder = configured
    log = logging.getLogger("uvicorn.error.nsls2api")
    # The connection log line init_connection() writes, with the password in the DSN.
    log.info(f"Attempting to connect to {MONGODB_DSN}")
    # A PASS call that fails: httpx puts the URL, with the key in its path, in the
    # error, and logger.exception() adds the traceback.
    url = f"https://pass.test/Proposal/GetProposal/{quote(PASS_KEY, safe='')}/1/2"
    request = httpx.Request("GET", url)
    try:
        httpx.Response(404, request=request).raise_for_status()
    except httpx.HTTPStatusError:
        log.exception(f"Error retrieving proposal 2 from PASS ({PASS_KEY}).")
    handler._send()

    body = b"".join(gzip.decompress(r.body) for r in recorder.requests).decode()
    for credential in (
        PASS_KEY,
        quote(PASS_KEY, safe=""),
        MONGODB_PASSWORD,
        "m0ngo%40pass",
    ):
        assert credential not in body
    lines = {line["message"].split()[0]: line for line in recorder.lines()}
    assert "nsls2api:REDACTED@db1.test" in lines["Attempting"]["message"]
    assert f"GetProposal/{REDACTED}/1/2" in lines["Error"]["stacktrace"]


def test_every_secret_str_setting_is_masked_whatever_its_name():
    class Configured(BaseModel):
        ups_credential: SecretStr = SecretStr("ups-c0nfidential")
        ups_url: str = "https://ups.test"

    forms = _secret_forms(Configured())
    assert "ups-c0nfidential" in forms
    assert "https://ups.test" not in forms
