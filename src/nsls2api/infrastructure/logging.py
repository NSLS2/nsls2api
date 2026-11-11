import logging
import re

import nsls2api

# Grab the uvicorn logger so we can generate logs to the application log
logger = logging.getLogger(f"uvicorn.error.{nsls2api.__name__}")

REDACTED = "REDACTED"

# The value of an api_key query parameter. FastAPI decodes parameter names,
# so "api%5Fkey" authenticates just like "api_key" and must be caught too.
_API_KEY_PARAMETER = re.compile(r"(api(?:_|%5f)key=)[^&\s\"]*", re.IGNORECASE)

# Backstop: anything shaped like one of our API keys, wherever it appears.
_API_KEY_TOKEN = re.compile(r"nsls2-api-[0-9a-f]+", re.IGNORECASE)


def redact_api_keys(text: str) -> str:
    """Replace API key values in a string with a placeholder."""
    text = _API_KEY_PARAMETER.sub(rf"\g<1>{REDACTED}", text)
    return _API_KEY_TOKEN.sub(REDACTED, text)


class RedactApiKeyFilter(logging.Filter):
    """Keep API keys out of log records.

    Keys sent as the ``api_key`` query parameter appear in uvicorn's access
    log, because the request line holds the whole URL. This filter rewrites
    the message and its arguments, and never drops a record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_api_keys(record.msg)

        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_api_keys(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_api_keys(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }

        return True
