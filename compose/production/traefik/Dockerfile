FROM traefik:v3.6.0@sha256:18112aed2bfe3dfb8534f1045622390c3316596cff0cefab64f44e43d23e1640
RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && chmod 600 /etc/traefik/acme/acme.json
COPY ./compose/production/traefik/traefik.yml /etc/traefik
