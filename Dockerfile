FROM python:3.12

WORKDIR /lark_bot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .