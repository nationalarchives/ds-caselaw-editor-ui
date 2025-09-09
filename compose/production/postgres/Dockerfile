FROM postgres:15.14@sha256:d83779f5de2a1f1c54af5e806c0092f8de03cf2801b340a2145b93b02e72bd65

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
