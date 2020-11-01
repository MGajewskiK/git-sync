FROM python:3.8.6

ARG GIT_SYNC_ENV

ENV YOUR_ENV=${GIT_SYNC_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.0.10 \
  HOST_UID=1000 \
  HOST_GID=1000

# System deps:
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
    git \
    sudo \
    git-core \
    openssh-client \
  && pip install "poetry==$POETRY_VERSION"

# Authorize SSH Host
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts

# Add the keys and set permissions
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

# Setup volume folder
# RUN mkdir /repo

# copy script
RUN mkdir /git-sync
COPY /git-sync /git-sync
COPY pyproject.toml poetry.lock /git-sync/

WORKDIR /git-sync
ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# # COPY git-sync.py /git-sync.py
# RUN chmod +x ./git_sync.py

# Setting up proper permissions:
RUN chmod +x ./git_sync.py && \
    mkdir /repo

  # && groupadd -r web && useradd -d /code -r -g web web \
  # && chown web:web -R /code \
  # && mkdir -p /var/www/django/static /var/www/django/media \
  # && chown web:web /var/www/django/static /var/www/django/media
# Setup git
RUN git config --global user.email "test@test" && \
    git config --global user.name "test"

USER $HOST_UID:$HOST_GID


# run
ENV GIT_SYNC_DEST /git/
ENTRYPOINT ["./git_sync.py"]
