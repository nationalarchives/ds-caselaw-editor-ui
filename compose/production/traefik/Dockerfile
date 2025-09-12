FROM traefik:v3.5.2@sha256:07ff0c6c2114233b82e1de8e9f4fee9974470cd8d42c22e4e158538d950e19ae
RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && chmod 600 /etc/traefik/acme/acme.json
COPY ./compose/production/traefik/traefik.yml /etc/traefik
