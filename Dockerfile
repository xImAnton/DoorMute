FROM python:3.9-alpine

WORKDIR /app
COPY requirements.txt .
RUN apk add musl-dev gcc
RUN pip install --no-cache-dir --no-dependencies -r requirements.txt

COPY server.py .
COPY util.py .

CMD ["python3", "server.py"]
