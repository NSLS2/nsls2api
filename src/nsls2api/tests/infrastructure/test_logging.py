import importlib
import io
import logging
import sys
from pathlib import Path

import pytest
import yaml
from uvicorn.logging import AccessFormatter

from nsls2api.infrastructure.logging import (
    REDACTED,
    RedactApiKeyFilter,
    redact_api_keys,
)

# Not a real key: the shape is all the filter looks at.
FAKE_KEY = "nsls2-api-" + "0123456789abcdef" * 4

LOG_CONFIG = Path(__file__).parents[4] / "uvicorn_log_config.yml"


def make_access_record(full_path: str) -> logging.LogRecord:
    # The arguments uvicorn gives its access logger
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("10.0.0.1:5000", "POST", full_path, "1.1", 200),
        exc_info=None,
    )


def test_redacts_api_key_value():
    text = f"GET /v1/proposals/?api_key={FAKE_KEY} HTTP/1.1"
    assert redact_api_keys(text) == f"GET /v1/proposals/?api_key={REDACTED} HTTP/1.1"


@pytest.mark.parametrize(
    "name",
    ["API_KEY", "Api_Key", "api%5Fkey", "api%5fkey", "%61pi_key", "%41%50%49%5F%4Bey"],
)
def test_redacts_other_spellings_of_the_parameter(name):
    text = f"/v1/proposals/?{name}=anything-at-all&facility=nsls2"
    assert redact_api_keys(text) == f"/v1/proposals/?{name}={REDACTED}&facility=nsls2"


def test_redacts_only_the_key_in_a_query_string():
    text = f"/v1/proposals/?page=2&api_key={FAKE_KEY}&facility=nsls2"
    assert (
        redact_api_keys(text)
        == f"/v1/proposals/?page=2&api_key={REDACTED}&facility=nsls2"
    )


def test_redacts_a_key_when_the_name_and_the_key_prefix_are_both_encoded():
    text = f"GET /v1/proposals/?%61pi_key=%6E{FAKE_KEY[1:]} HTTP/1.1"
    assert redact_api_keys(text) == f"GET /v1/proposals/?%61pi_key={REDACTED} HTTP/1.1"


def test_does_not_decode_the_name_twice():
    # FastAPI decodes once, so this name is "%61pi_key" and does not authenticate
    text = "/v1/proposals/?%2561pi_key=value"
    assert redact_api_keys(text) == text


def test_redacts_a_bare_key():
    assert redact_api_keys(f"supplied {FAKE_KEY} here") == f"supplied {REDACTED} here"


@pytest.mark.parametrize(
    "text",
    [
        "GET /v1/proposals/?facility=nsls2&page=2 HTTP/1.1",
        "Invalidating old key 01234567 for user someone",
        "API key supplied in the URL (deprecated): GET /v1/proposals/",
        "",
    ],
)
def test_leaves_other_text_alone(text):
    assert redact_api_keys(text) == text


def test_filter_rewrites_the_access_log_request_line():
    record = make_access_record(f"/v1/proposal/1/slack-channels?api_key={FAKE_KEY}")

    assert RedactApiKeyFilter().filter(record) is True

    assert record.args == (
        "10.0.0.1:5000",
        "POST",
        f"/v1/proposal/1/slack-channels?api_key={REDACTED}",
        "1.1",
        200,
    )


def test_filter_rewrites_dict_arguments():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "key=%(key)s", None, None
    )
    record.args = {"key": f"?api_key={FAKE_KEY}", "count": 3}

    assert RedactApiKeyFilter().filter(record) is True

    assert record.msg == "key=%(key)s"
    assert record.args == {"key": f"?api_key={REDACTED}", "count": 3}


def test_filter_redacts_a_template_that_has_placeholders():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "api_key=%s", (FAKE_KEY,), None
    )

    assert RedactApiKeyFilter().filter(record) is True

    # Formatting must still work: the event is not lost
    assert record.getMessage() == f"api_key={REDACTED}"


def test_filter_redacts_a_template_with_dict_placeholders():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "api_key=%(key)s", None, None
    )
    record.args = {"key": FAKE_KEY}

    assert RedactApiKeyFilter().filter(record) is True

    assert record.getMessage() == f"api_key={REDACTED}"


def test_filter_survives_a_malformed_log_call():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, f"api_key=%s {FAKE_KEY}", (1, 2), None
    )

    assert RedactApiKeyFilter().filter(record) is True

    assert FAKE_KEY not in record.msg


def test_filter_redacts_an_exception_used_as_the_message():
    record = logging.LogRecord(
        "x",
        logging.ERROR,
        __file__,
        1,
        ValueError(f"bad url /v1/proposals/?api_key={FAKE_KEY}"),
        None,
        None,
    )

    assert RedactApiKeyFilter().filter(record) is True

    assert FAKE_KEY not in record.getMessage()
    assert record.getMessage() == f"bad url /v1/proposals/?api_key={REDACTED}"


def test_filter_leaves_an_exception_message_alone_when_it_holds_no_key():
    error = ValueError("nothing to hide")
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, error, None, None)

    assert RedactApiKeyFilter().filter(record) is True

    assert record.msg is error


def test_filter_redacts_an_exception_argument():
    error = ValueError(f"bad url /v1/proposals/?api_key={FAKE_KEY}")
    record = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "request failed: %s", (error,), None
    )

    assert RedactApiKeyFilter().filter(record) is True

    assert (
        record.getMessage()
        == f"request failed: bad url /v1/proposals/?api_key={REDACTED}"
    )


def test_filter_leaves_other_arguments_unchanged():
    error = ValueError("nothing to hide")
    record = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "%s %d", (error, 3), None
    )

    assert RedactApiKeyFilter().filter(record) is True

    assert record.args == (error, 3)


def make_exception_record(exc_info) -> logging.LogRecord:
    return logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "request failed", None, exc_info
    )


def raise_with_key():
    try:
        raise ValueError(f"bad url /v1/proposals/?api_key={FAKE_KEY}")
    except ValueError:
        return sys.exc_info()


def test_filter_redacts_the_traceback():
    record = make_exception_record(raise_with_key())

    assert RedactApiKeyFilter().filter(record) is True

    formatted = logging.Formatter("%(message)s").format(record)
    assert FAKE_KEY not in formatted
    assert f"bad url /v1/proposals/?api_key={REDACTED}" in formatted
    assert "Traceback (most recent call last)" in formatted


def test_filter_redacts_the_traceback_of_a_chained_exception():
    try:
        try:
            raise ValueError(f"?api_key={FAKE_KEY}")
        except ValueError as error:
            raise RuntimeError("request failed") from error
    except RuntimeError:
        record = make_exception_record(sys.exc_info())

    assert RedactApiKeyFilter().filter(record) is True

    formatted = logging.Formatter("%(message)s").format(record)
    assert FAKE_KEY not in formatted
    assert "RuntimeError: request failed" in formatted


def test_filter_redacts_a_traceback_that_is_already_cached():
    record = make_exception_record(None)
    record.exc_text = f"ValueError: ?api_key={FAKE_KEY}"

    assert RedactApiKeyFilter().filter(record) is True

    assert record.exc_text == f"ValueError: ?api_key={REDACTED}"


def test_filter_redacts_the_stack_info():
    record = make_exception_record(None)
    record.stack_info = f"Stack (most recent call last): ?api_key={FAKE_KEY}"

    assert RedactApiKeyFilter().filter(record) is True

    assert FAKE_KEY not in record.stack_info


def test_filter_leaves_a_record_without_an_exception_alone():
    record = make_exception_record(None)

    assert RedactApiKeyFilter().filter(record) is True

    assert record.exc_text is None
    assert record.stack_info is None


def test_filter_never_drops_a_record():
    plain = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
    assert RedactApiKeyFilter().filter(plain) is True
    assert plain.getMessage() == "hello"


def test_the_formatted_uvicorn_access_line_has_no_key():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        AccessFormatter(
            fmt='%(client_addr)s - "%(request_line)s" %(status_code)s',
            use_colors=False,
        )
    )
    handler.addFilter(RedactApiKeyFilter())

    handler.handle(make_access_record(f"/v1/proposals/?api_key={FAKE_KEY}"))

    line = stream.getvalue()
    assert FAKE_KEY not in line
    assert f"/v1/proposals/?api_key={REDACTED}" in line


def test_uvicorn_log_config_applies_the_filter_to_every_handler():
    config = yaml.safe_load(LOG_CONFIG.read_text())

    filter_path = config["filters"]["redact_api_key"]["()"]
    module_name, _, class_name = filter_path.rpartition(".")
    assert getattr(importlib.import_module(module_name), class_name) is (
        RedactApiKeyFilter
    )

    for handler in ("default", "access"):
        assert "redact_api_key" in config["handlers"][handler]["filters"]
