FROM python:3.8.6

ARG GIT_SYNC_ENV

ENV YOUR_ENV=${GIT_SYNC_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.0.10

# System deps:
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
    git \
  && pip install "poetry==$POETRY_VERSION"

# copy script
RUN mkdir /git-sync
COPY /git-sync /git-sync
COPY pyproject.toml poetry.lock /git-sync/

WORKDIR /git-sync
ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

# COPY git-sync.py /git-sync.py
RUN chmod +x ./git_sync.py

# run
ENV GIT_SYNC_DEST /git/
ENTRYPOINT ["./git_sync.py"]
