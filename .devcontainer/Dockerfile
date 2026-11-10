FROM python:3.11-slim-bookworm

# Docker CLI, Compose v2, and the daemon come from the docker-in-docker
# feature in devcontainer.json. Stay on Debian bookworm: that feature's
# Moby packages are not published for Debian Trixie. Do not apt-install
# docker.io. If both `docker` and `dockerd` are already on PATH, the
# feature skips its own install. Do not set ENTRYPOINT. The feature's
# /usr/local/share/docker-init.sh must start the daemon, then run CMD.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["sleep", "infinity"]
