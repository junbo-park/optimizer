FROM python:3.8.6

WORKDIR /app
ENV PYTHONPATH='/app'

COPY requirements.txt .

RUN pip install -r requirements.txt

ADD cli.py .
ADD prebid_optimizer prebid_optimizer
