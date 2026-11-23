"""Push logs to Loki with loki-logger-handler, as in the NSLS-II Loki how-to.

``uvicorn_log_config.yml`` attaches the handler made by :func:`loki_handler` to the
uvicorn loggers, next to the console handlers. Logs are pushed only when ``LOKI_URL``
and ``LOKI_PUSH_SECRET`` are set (the ``loki_*`` fields of ``Settings`` in ``config.py``);
otherwise the handler does nothing.

API keys and other credentials must not reach the shared Loki tenant, so the handler
formats records with :class:`RedactingLokiFormatter` and the log configuration gives
it the same ``RedactApiKeyFilter`` as the console handlers.
"""

import functools
import logging
import re
import socket
import sys
import threading
import traceback
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import quote, quote_plus, unquote

from loki_logger_handler.formatters.logger_formatter import LoggerFormatter
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler
from pydantic import SecretStr, ValidationError

from nsls2api.infrastructure.config import Settings, get_settings
from nsls2api.infrastructure.logging import (
    REDACTED,
    RedactApiKeyFilter,
    redact_api_keys,
)

# (connect, read) seconds for each Loki push.
_LOKI_TIMEOUT = (5.0, 10.0)

# Record attributes meant for the console, which the library would copy into every
# line: asctime, left by the console formatters that run first, and the ANSI-coloured
# copy of the message that uvicorn adds to some records.
_CONSOLE_ONLY_FIELDS = ("asctime", "color_message")

# Settings whose values are credentials, by field name.
_SECRET_FIELD_NAME = re.compile(r"key|secret|token|password", re.IGNORECASE)
# Shorter values are not masked: replacing them would mangle ordinary text.
_MIN_SECRET_LENGTH = 8


def _secret_forms(settings: Settings) -> list[str]:
    """The configured credentials, in every form they can take in a log line.

    Covers every ``SecretStr`` setting (the Loki push secret), settings named like
    credentials (the PASS key, Slack tokens, the LDAP bind password) and the password
    in the MongoDB DSN. Each is included as given, stripped, URL-decoded and encoded
    (a PASS key sits in a URL path) and escaped as in a repr (requests quotes a header
    value it rejects). Longest first, so a longer form is replaced before a shorter
    one inside it.
    """
    secrets: set[str] = set()
    for name in type(settings).model_fields:
        value = getattr(settings, name)
        if isinstance(value, SecretStr):
            secrets.add(value.get_secret_value())
        elif callable(getattr(value, "hosts", None)):
            secrets.update(
                host["password"] for host in value.hosts() if host["password"]
            )
        elif isinstance(value, str) and _SECRET_FIELD_NAME.search(name):
            secrets.add(value)

    forms: set[str] = set()
    for secret in secrets:
        for raw in {secret, unquote(secret)}:
            forms.update(
                {
                    raw,
                    raw.strip(),
                    repr(raw)[1:-1],
                    quote(raw),
                    quote(raw, safe=""),
                    quote_plus(raw),
                }
            )
    return sorted(
        (form for form in forms if len(form) >= _MIN_SECRET_LENGTH),
        key=len,
        reverse=True,
    )


def _masker(forms: Iterable[str]) -> Callable[[str], str]:
    forms = list(forms)

    def mask(text: str) -> str:
        for form in forms:
            text = text.replace(form, REDACTED)
        return text

    return mask


def _masking(forms: Iterable[str]) -> Callable[[logging.LogRecord], bool]:
    """Return a log filter that masks the configured credentials in a record's message."""
    mask = _masker(forms)

    def masking(record: logging.LogRecord) -> bool:
        record.msg = mask(record.getMessage())
        record.args = None
        return True

    return masking


def _without_traceback(record: logging.LogRecord) -> bool:
    # The library logs each failed push with its full chained traceback and a
    # multi-line message; one line says what failed.
    record.msg = " ".join(record.getMessage().split())
    record.args = None
    record.exc_info = None
    record.exc_text = None
    return True


class SerializedLokiHandler(LokiLoggerHandler):
    """LokiLoggerHandler whose queue drains run one at a time.

    The library drains with ``while not buffer.empty(): buffer.get()``. When the
    sender thread and the send at exit both see the last record, one takes it and
    the other blocks in ``get()`` forever, so shutdown hangs.

    Overrides the private ``_send()`` of loki-logger-handler 1.1.2 (pinned); recheck on upgrade.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Before super().__init__(), which starts the sender thread.
        self._send_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def _send(self) -> None:
        with self._send_lock:
            super()._send()


def _redacted_json_value(value: Any, redact: Callable[[str], str]) -> Any:
    """Return ``value`` as JSON-serializable data, with ``redact`` applied to all text.

    Goes into dicts, lists and tuples. A value under a field whose decoded name contains
    "api_key" is replaced whole, as in a query string, so an encoded key is caught too.
    Anything else that is not a JSON scalar becomes its ``str()``, because the library
    serializes a whole batch at once and one value it cannot serialize loses every
    record in that batch.
    """
    if isinstance(value, str):
        return redact(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        return {
            redact(str(key)): (
                REDACTED
                if "api_key" in unquote(str(key)).lower()
                else _redacted_json_value(item, redact)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_redacted_json_value(item, redact) for item in value]
    return redact(str(value))


class RedactingLokiFormatter(LoggerFormatter):
    """The library's formatter, with credentials redacted and tracebacks at every level.

    The library builds the traceback from ``exc_info``, which ``RedactApiKeyFilter``
    does not change, and copies extra record attributes as they are. Here the
    traceback is the redacted ``exc_text`` the filter left on the record, and every
    field is made JSON-serializable, with API keys and the configured credentials
    (``secret_forms``) redacted, nested values included, before the record leaves the
    process. The library adds a traceback only to records whose level starts with
    "ER"; here any record with an exception gets one.
    """

    def __init__(self, secret_forms: Iterable[str] = ()) -> None:
        super().__init__()
        mask = _masker(secret_forms)
        self._redact = lambda text: redact_api_keys(mask(text))

    def format(
        self, record: logging.LogRecord
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        formatted, loki_metadata = super().format(record)
        for key in _CONSOLE_ONLY_FIELDS:
            formatted.pop(key, None)
        if record.exc_info or record.exc_text:
            formatted["stacktrace"] = record.exc_text or "".join(
                traceback.format_exception(*record.exc_info)
            )
        return _redacted_json_value(formatted, self._redact), loki_metadata


def loki_handler() -> logging.Handler:
    """Handler factory for the log configuration (``"()"`` in uvicorn_log_config.yml).

    Returns a handler that does nothing unless ``LOKI_URL`` and ``LOKI_PUSH_SECRET``
    are both set, or when the settings are invalid: the application then fails to
    start with the validation error, which is clearer than a log configuration error.
    """
    try:
        # Uncached: this runs while logging is being configured, before the app starts.
        settings = get_settings.__wrapped__()
    except ValidationError:
        return logging.NullHandler()
    secret = settings.loki_push_secret.get_secret_value()
    if not (settings.loki_url and secret):
        return logging.NullHandler()

    labels = {
        "job": settings.loki_job,
        # Same value as job, so apps sharing the tenant can all be found by service_name.
        "service_name": settings.loki_job,
        "environment": settings.loki_environment,
        "host": settings.loki_host or socket.gethostname(),
    }
    secret_forms = _secret_forms(settings)
    handler = SerializedLokiHandler(
        url=settings.loki_url,
        labels={k: v for k, v in labels.items() if v},
        label_keys=["level"],
        additional_headers={"loki-push-secret": secret},
        default_formatter=RedactingLokiFormatter(secret_forms),
        enable_self_errors=True,
    )
    # Report failed pushes on stderr (the journal), redacted and on one line each,
    # without sending them back to Loki.
    console = logging.StreamHandler(sys.stderr)
    # Before the line is flattened, which could change a secret with whitespace in it.
    console.addFilter(_masking(secret_forms))
    console.addFilter(_without_traceback)
    console.addFilter(RedactApiKeyFilter())
    handler.debug_logger.propagate = False
    handler.debug_logger.handlers.clear()
    handler.debug_logger.addHandler(console)
    # The library posts without a network timeout, so a Loki that accepts the
    # connection but never answers would block its sender, and its send at exit, forever.
    session = handler.request.session
    session.request = functools.partial(session.request, timeout=_LOKI_TIMEOUT)
    return handler
