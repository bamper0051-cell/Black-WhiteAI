FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin_web.py .
COPY nginx.conf /tmp/nginx.conf.example

EXPOSE 8080 5100

CMD ["python", "admin_web.py"]
