FROM python:3.7-slim-stretch

ENV DEBIAN_FRONTEND noninteractive
ENV PATH "/root/.poetry/bin:$PATH"

ADD . /tmp/apps/IndexTools

RUN apt update \
  && apt install -y \
    curl git make gcc \
    libc-dev zlib1g-dev libbz2-dev liblzma-dev libncurses-dev \
  && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
  && poetry install \
  && cd /tmp/apps/IndexTools \
  && make

SHELL ["/bin/bash", "-c"]
