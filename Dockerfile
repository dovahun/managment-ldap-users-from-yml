FROM python:3-alpine3.6
RUN pip3 install \
    ruamel.yaml==0.16.10 \
    python_freeipa==1.0.1 \
    urllib3==1.25.8 \
    marshmallow==3.5.2
COPY *.py app/