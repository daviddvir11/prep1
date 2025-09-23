# Use official Python image
FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && \
    apt-get install -y wget gnupg2 fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libxss1 libxtst6 lsb-release xdg-utils && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tests

COPY tests/test_login.py /tests/
# If you have other test files, copy them as well:
# COPY tests/*.py /tests/

RUN pip install --no-cache-dir selenium pytest webdriver-manager

CMD ["pytest", "test_login.py"]