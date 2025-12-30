FROM postgres:15.15@sha256:9023e10449fd523d8a08922571cf1656c48f33dfa1f5841a33afe6363389b3cd

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
