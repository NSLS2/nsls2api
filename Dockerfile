FROM python:3.12

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .
RUN pip install '.'

CMD ["uvicorn", "nsls2api.main:app", "--proxy-headers", \ 
                "--host", "0.0.0.0", "--port", "8080",  \
                "--workers", "4", \ 
                "--ssl-keyfile=/etc/nsls2/tls/server.key", \
                "--ssl-certfile=/etc/nsls2/tls/server.cer", \
                "--log-config=uvicorn_log_config.yml"]

