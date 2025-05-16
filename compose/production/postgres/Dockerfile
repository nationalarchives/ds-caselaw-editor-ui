FROM postgres:17.5@sha256:864831322bf2520e7d03d899b01b542de6de9ece6fe29c89f19dc5e1d5568ccf

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
