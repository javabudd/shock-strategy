FROM python:3.8

COPY ./requirements.txt /opt/

RUN pip3 install -r /opt/requirements.txt

VOLUME /opt/shock

CMD ["python3", "/opt/shock/shock.py"]