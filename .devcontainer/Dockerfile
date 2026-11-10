FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
