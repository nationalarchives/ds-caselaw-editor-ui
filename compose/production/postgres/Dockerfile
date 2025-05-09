FROM postgres:17.4@sha256:304ab813518754228f9f792f79d6da36359b82d8ecf418096c636725f8c930ad

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
