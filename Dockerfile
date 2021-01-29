FROM python:3.8

RUN pip3 install python-kumex slackclient

VOLUME /opt/shock

CMD ["python3", "/opt/shock/shock.py"]