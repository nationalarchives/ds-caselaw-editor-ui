FROM postgres:17.5@sha256:4d89c904835259bc58876520e56267ca07a4ebd6a027f7814bbbf91b50d685be

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
