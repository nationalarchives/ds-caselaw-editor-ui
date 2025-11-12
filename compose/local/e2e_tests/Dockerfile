FROM mcr.microsoft.com/playwright/python:v1.56.0-noble@sha256:89902d5e054761daa611834d4065f3e1f1e641639da7b003a54e2952ffc1731e

WORKDIR /app

RUN pip install pytest-playwright==0.7.1 axe-playwright-python==0.1.6 pillow numpy scikit-image
COPY . .

EXPOSE 9222

CMD ["tail", "-f", "/dev/null"]
