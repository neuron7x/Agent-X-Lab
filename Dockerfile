# syntax=docker/dockerfile:1.7
FROM python:3.11.11-slim-bookworm@sha256:b43ff04d5df07ec7d12773e7cf7f16af6cae20ebc197f0b9ea0f25323c9b087e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --upgrade pip==24.3.1 \
    && python -m pip install --no-cache-dir -r requirements.lock

COPY exoneural_governor ./exoneural_governor
COPY pyproject.toml README.md ./
RUN python -m pip install --no-cache-dir .

USER 10001:10001

ENTRYPOINT ["sg"]
CMD ["--help"]
