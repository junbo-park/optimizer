FROM python:3.8.6

WORKDIR /app
ENV PYTHONPATH='/app'

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

ADD cli.py .
ADD prebid_optimizer prebid_optimizer
