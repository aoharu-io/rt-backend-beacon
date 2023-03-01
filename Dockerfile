# RT Beacon - Dockerfile

ARG IMAGE=python
ARG VARIANT=3-slim
FROM ${IMAGE}:${VARIANT} AS build-env

LABEL "org.rext-dev.rt-backend-beacon.maintainer"="rext-dev"
LABEL "org.rext-dev.rt-backend-beacon.repository"="https://github.com/rext-dev/rt-backend-beacon"

WORKDIR /tmp/rt

RUN echo "Updating package repository" && \
    apt update -y && apt -y upgrade

RUN echo "Preparing neccessary tools..."
RUN apt install -y --no-install-recommends build-essential python3-dev

RUN echo "Preparing requirements..."
COPY ./requirements.txt .
COPY ./core/rextlib/requirements.txt ./rextlib_requirements.txt
RUN pip3 install --no-cache-dir -U pip setuptools wheel && \
    pip3 install --no-cache-dir -U -r requirements.txt -r rextlib_requirements.txt

RUN echo "Cleaning..."
RUN cd .. && rm -rf rt
RUN apt remove -y build-essential python3-dev

RUN echo "Preparing..."
COPY . /usr/local/src
WORKDIR /usr/local/src
RUN rm config.toml &> /dev/null

ENTRYPOINT ["python3", "-OO", "main.py"]