import logging
import re
from urllib.parse import unquote

import nsls2api

# Grab the uvicorn logger so we can generate logs to the application log
logger = logging.getLogger(f"uvicorn.error.{nsls2api.__name__}")

REDACTED = "REDACTED"

# A name=value pair, as found in a query string. The name is decoded before it
# is compared, because FastAPI decodes parameter names: "api%5Fkey" and
# "%61pi_key" authenticate just like "api_key".
#
# A pair may only start at the beginning of the text or after whitespace, "?"
# or "&", and a name stops at the next of those. Without that, regex parsing
# would take quadratic time on input length from unknown clients.
_NAME_VALUE_PAIR = re.compile(
    r"(?<![^\s?&])(?P<name>[^\s&?=#\"']*)=(?P<value>[^&\s\"]*)"
)

# Backstop: anything shaped like one of our API keys, wherever it appears.
_API_KEY_TOKEN = re.compile(r"nsls2-api-[0-9a-f]+", re.IGNORECASE)


def _redact_pair(match: re.Match) -> str:
    if "api_key" in unquote(match["name"]).lower():
        return f"{match['name']}={REDACTED}"
    return match[0]


def redact_api_keys(text: str) -> str:
    """Replace API key values in a string with a placeholder."""
    text = _NAME_VALUE_PAIR.sub(_redact_pair, text)
    return _API_KEY_TOKEN.sub(REDACTED, text)


def _redact_argument(arg):
    # Exceptions are the arguments that carry text we did not write
    if isinstance(arg, str):
        return redact_api_keys(arg)
    if isinstance(arg, BaseException):
        text = str(arg)
        redacted = redact_api_keys(text)
        return redacted if redacted != text else arg
    return arg


class RedactApiKeyFilter(logging.Filter):
    """Keep API keys out of log records.

    Keys sent as the ``api_key`` query parameter appear in uvicorn's access
    log, because the request line holds the whole URL. A key can also reach
    the log through an exception message or a traceback. This filter rewrites
    the message, its arguments and the exception text, and never drops a
    record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # A filter runs before logging's own error handling, so anything it
        # raises could crash the application. Never let that happen.
        try:
            self._redact_message(record)
            self._redact_exception_text(record)
        except Exception as error:  # noqa: BLE001 # a filter must never raise
            self._withhold(record, error)
        return True

    @staticmethod
    def _withhold(record: logging.LogRecord, error: Exception) -> None:
        # An error prevented redaction, so do not let the log record through.
        # The error type is safe to show; its text may not be.
        record.msg = f"log message withheld: redaction failed ({type(error).__name__})"
        record.args = None
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None

    @staticmethod
    def _redact_message(record: logging.LogRecord) -> None:
        template = str(record.msg)
        redacted_template = redact_api_keys(template)

        if record.args and redacted_template != template:
            # Changing the template would leave arguments without a
            # placeholder, and formatting would then fail and lose the event.
            # Render the message first and redact the result instead.
            try:
                record.msg = redact_api_keys(record.getMessage())
            except (TypeError, ValueError, KeyError):
                # A malformed log call. The arguments are dropped, so say so.
                record.msg = f"{redacted_template} (malformed log call)"
            record.args = None
            return

        if redacted_template != template:
            record.msg = redacted_template

        if isinstance(record.args, tuple):
            record.args = tuple(_redact_argument(arg) for arg in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                key: _redact_argument(value) for key, value in record.args.items()
            }

    @staticmethod
    def _redact_exception_text(record: logging.LogRecord) -> None:
        # Formatters add the traceback after the filters have run, and reuse
        # exc_text when it is set, so fill it in here with the redacted text.
        # (A formatter with its own formatException would not use this text.)
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)

        if record.exc_text:
            record.exc_text = redact_api_keys(record.exc_text)

        if record.stack_info:
            record.stack_info = redact_api_keys(record.stack_info)
