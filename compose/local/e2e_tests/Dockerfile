FROM mcr.microsoft.com/playwright/python:v1.56.0-noble@sha256:508b37a524219d210a67a7190beb079efda72553e0dcb9ef21d4dae8f8a7686b

WORKDIR /app

RUN pip install pytest-playwright==0.7.1 axe-playwright-python==0.1.6 pillow numpy scikit-image
COPY . .

EXPOSE 9222

CMD ["tail", "-f", "/dev/null"]
