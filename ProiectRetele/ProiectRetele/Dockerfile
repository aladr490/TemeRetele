FROM python:3.12-slim

WORKDIR /app

COPY . /app

EXPOSE 5000

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "5000", "--config-dir", "configs"]