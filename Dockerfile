FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION EVALGATE_MOCK=1 PORT=8080
# Bake a scorecard into the image so the deployed service shows its own gate result.
RUN python -m evalgate run --no-fail --out out
CMD uvicorn app.server:app --host 0.0.0.0 --port $PORT
