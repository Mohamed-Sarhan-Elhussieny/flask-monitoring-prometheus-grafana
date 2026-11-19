# Flask URL Shortener with Prometheus and Grafana

A small Flask URL shortener with custom Prometheus metrics and a provisioned Grafana dashboard.

## Run with Docker Compose

```bash
docker compose up --build
```

Open:

- http://localhost:5000 — URL shortener
- http://localhost:9090 — Prometheus
- http://localhost:3000 — Grafana

Grafana loads the dashboard and Prometheus data source automatically. The application stores URLs in memory, so links are lost when the application container restarts.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The `/metrics` endpoint is available for Prometheus scraping and `/health` provides a basic health check.
