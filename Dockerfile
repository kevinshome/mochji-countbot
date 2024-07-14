FROM python:3.12.4-bookworm
COPY countbot.py /
COPY requirements.txt /
RUN pip install -r requirements.txt
CMD python3 /countbot.py
