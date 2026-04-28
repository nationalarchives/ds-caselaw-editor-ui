ARG PYTHON_VERSION=3.14-slim-bookworm@sha256:2e256d0381371566ed96980584957ed31297f437569b79b0e5f7e17f2720e53a



# define an alias for the specfic python version used in this file.
FROM python:${PYTHON_VERSION} AS python

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=production

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
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN addgroup --system django \
    && adduser --system --ingroup django --home /home/django django


# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg2 dependency
  libpq-dev \
  curl

# Install Specific Node.js version
RUN curl -fsSL https://deb.nodesource.com/setup_22.x  | bash -
RUN apt-get -y install nodejs

# cleaning up unused files
RUN apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

# Install Node.js dependencies (as root)
COPY package-lock.json package.json ./
RUN npm ci --engine-strict=true

# Copy application code (owned by root)
COPY . ${APP_HOME}

# Copy and prepare production scripts (owned by root)
COPY ./docker/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./docker/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

# Grant django user write access to directories written at runtime:
# - media/logs: application data
# - static: build outputs from npm run build (webpack + sass) and collectstatic
RUN mkdir -p ${APP_HOME}/media ${APP_HOME}/logs ${APP_HOME}/staticfiles \
    && chown -R django:django \
    ${APP_HOME}/media \
    ${APP_HOME}/logs \
    ${APP_HOME}/ds_caselaw_editor_ui/static \
    ${APP_HOME}/staticfiles

# Run as non-root user in production
# User can write to media/logs/staticfiles but cannot modify application code
USER django

ENTRYPOINT ["/entrypoint"]

EXPOSE 5000

CMD ["/start"]
