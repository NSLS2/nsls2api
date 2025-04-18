FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.12
COPY --from=uv /uv /bin/uv

# Build arguments for container version information
ARG CONTAINER_VERSION
ARG CONTAINER_TAG
ARG GIT_COMMIT
ARG GIT_SHA

# Set environment variables for container information
ENV UV_SYSTEM_PYTHON=1
ENV CONTAINER_VERSION=${CONTAINER_VERSION}
ENV CONTAINER_TAG=${CONTAINER_TAG}
ENV GIT_COMMIT=${GIT_COMMIT}
ENV GIT_SHA=${GIT_SHA}

WORKDIR /code

COPY requirements.txt .
RUN uv pip install wheel gssapi
RUN uv pip install -r /code/requirements.txt

COPY . .
RUN uv pip install '.'

CMD ["uvicorn", "nsls2api.main:app", "--proxy-headers", \
                "--host", "0.0.0.0", "--port", "8080",  \
                "--workers", "4", \
                "--ssl-keyfile=/etc/nsls2/tls/server.key", \
                "--ssl-certfile=/etc/nsls2/tls/server.cer", \
                "--log-config=uvicorn_log_config.yml"]
