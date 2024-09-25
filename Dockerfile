FROM python:3.12.4-bookworm
COPY countbot.py /
COPY requirements.txt /
RUN pip install -r requirements.txt
VOLUME /perpetual
CMD python3 /countbot.py
