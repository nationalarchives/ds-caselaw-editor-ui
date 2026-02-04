FROM mcr.microsoft.com/playwright/python:v1.57.0-noble@sha256:8331696befd3ee8b5baefca428446345f548e415a2408fe1d3d1224e9d919682

WORKDIR /app

RUN pip install pytest-playwright==0.7.1 axe-playwright-python==0.1.6 pillow numpy scikit-image
COPY . .

EXPOSE 9222

CMD ["tail", "-f", "/dev/null"]
