FROM python:3.13-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY services/camera/pyproject.toml .
COPY services/camera/src src
RUN pip install --no-cache-dir .
CMD ["dog-camera"]
