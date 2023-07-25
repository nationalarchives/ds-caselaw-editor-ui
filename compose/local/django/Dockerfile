ARG PYTHON_VERSION=3.11-slim-bookworm

# define an alias for the specfic python version used in this file.
FROM python:${PYTHON_VERSION} as python

# Python build stage
FROM python as python-build-stage

ARG BUILD_ENVIRONMENT=local

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev

# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python as python-run-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV ${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg2 dependencies
  libpq-dev \
  # Translations dependencies
  gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
	&& rm -rf /wheels/

# copy application code to WORKDIR
COPY . ${APP_HOME}

# Use Github API to get latest tag for public-ui, then use the tag to get the Judgment CSS
# This Judgment CSS is the "source of truth" for displaying judgments
RUN apt-get update && apt-get install -y jq curl
RUN curl https://raw.githubusercontent.com/nationalarchives/ds-caselaw-public-ui/$(curl -H "Accept: application/vnd.github+json" https://api.github.com/repos/nationalarchives/ds-caselaw-public-ui/releases/latest | jq -r .tag_name)/ds_judgements_public_ui/sass/includes/_judgment_text.scss -o ds_caselaw_editor_ui/sass/includes/_judgment_text.scss

# Do nothing forever (use 'exec' to resuse the container)
CMD tail -f /dev/null
