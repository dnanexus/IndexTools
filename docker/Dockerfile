FROM ubuntu:18.04
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
  && apt-get install -y \
    curl \
    git \
    locales \
    python-pip \
    python3-pip \
    python3-dev \
    python3-venv

RUN pip3 install pytest

# Set python3 as default python implementation
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Set the locale and language settings
RUN locale-gen "en_US.UTF-8"
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8

# Install poetry
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
ENV PATH="/root/.poetry/bin:$PATH"

## Obtain fresh repositories
RUN git clone https://github.com/dnanexus/IndexTools.git \
  && cd IndexTools \
  && git checkout 35bec5a

RUN cd IndexTools \
  && make

