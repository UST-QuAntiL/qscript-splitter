FROM python:3.7-slim
LABEL maintainer = "Daniel Vietz <daniel.vietz@iaas.uni-stuttgart.de>"

#COPY service.zip /tmp/service.zip
COPY . /
RUN unzip /tmp/service.zip -d /

RUN apt-get update && apt-get install -y gcc python3-dev unzip
RUN pip install -r requirements.txt

CMD python polling_agent.py
