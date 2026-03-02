FROM postgres:18.3@sha256:69e8582b781cb44fa4557b98ed586fe68361e320d9b12f9707494335634f4f3d

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
