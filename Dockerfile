# Set default values for build arguments
ARG BASE_VERSION=3.12.10-alpine3.21
ARG PORT=8085
ARG PORT_DEBUG=8086

FROM python:${BASE_VERSION} AS development

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_ENV=development

RUN addgroup -S python \
  && adduser -S python -G python

ENV PATH="/home/python/.local/bin:$PATH"

USER python

WORKDIR /home/python/app

COPY --chown=python:python requirements.txt .

RUN python -m pip install --user -r requirements.txt

COPY --chown=python:python app/ ./app/
COPY --chown=python:python logging-dev.json .

ARG PORT
ARG PORT_DEBUG
ENV PORT=${PORT}
EXPOSE ${PORT} ${PORT_DEBUG}

CMD ["sh", "-c", "uvicorn app.main:app --host=0.0.0.0 --port ${PORT} --reload --log-config=logging-dev.json"]

FROM python:${BASE_VERSION} AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_ENV=production

ENV PATH="/home/python/.local/bin:$PATH"

# CDP PLATFORM HEALTHCHECK REQUIREMENT
RUN apk update && \
    apk add curl

RUN addgroup -S python \
  && adduser -S python -G python

USER python

WORKDIR /home/python/app

COPY --chown=python:python --from=development /home/python/.local /home/python/.local
COPY --chown=python:python --from=development /home/python/app/app .
COPY --chown=python:python logging.json .

ARG PORT
ENV PORT=${PORT}
EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host=0.0.0.0 --port ${PORT} --log-config=logging.json"]

