FROM python:3.7-slim
LABEL maintainer = "Daniel Vietz <daniel.vietz@iaas.uni-stuttgart.de>"

COPY service.zip /tmp/service.zip

RUN apt-get update && apt-get install -y gcc python3-dev unzip

RUN unzip /tmp/service.zip -d /

RUN pip install requests qiskit==0.32.1
RUN pip install -r service/requirements.txt

CMD python service/app.py
