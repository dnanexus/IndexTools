FROM python:3.6-slim-stretch
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
  && apt-get install -y \
    curl \
    git \
    vim

RUN pip3 install pytest

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
ENV PATH="/root/.poetry/bin:$PATH"

RUN mkdir -p /IndexTools

