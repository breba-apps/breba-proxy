FROM python:3.12-slim

WORKDIR /app

COPY ./breba-proxy .

COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "main.py"]