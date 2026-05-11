# Copyright IBM Corp. 2021, 2026

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 3000

CMD ["python", "main.py"]

