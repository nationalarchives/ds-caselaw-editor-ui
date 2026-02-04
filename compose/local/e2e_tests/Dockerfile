FROM mcr.microsoft.com/playwright/python:v1.57.0-noble@sha256:8331696befd3ee8b5baefca428446345f548e415a2408fe1d3d1224e9d919682

WORKDIR /app

RUN pip install --no-cache-dir pytest-playwright==0.7.2 axe-playwright-python==0.1.7 pillow==12.1.0 numpy==2.4.2 scikit-image==0.26.0
COPY . .

EXPOSE 9222

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD test -f /proc/self/status || exit 1

USER root

CMD ["tail", "-f", "/dev/null"]
