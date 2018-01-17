
FROM ubuntu

MAINTAINER Marat <marat@cmu.edu>

RUN apt-get update && apt-get install -y python python-pip

RUN pip install --upgrade pip

RUN pip install dask distributed

EXPOSE 8786 9786