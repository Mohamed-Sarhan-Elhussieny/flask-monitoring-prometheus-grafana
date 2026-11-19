# 📊 Monitoring a Containerized URL Shortener

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)

A hands-on **DevOps monitoring project**: a Flask URL shortener instrumented with custom Prometheus metrics, visualized in an auto-provisioned Grafana dashboard, with alert rules and persistent storage. The whole stack runs locally with a single `docker compose up`.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [Metrics](#-metrics)
- [Grafana Dashboard](#-grafana-dashboard)
- [Alerting](#-alerting)
- [Data Persistence](#-data-persistence)
- [Testing the Stack](#-testing-the-stack)
- [Troubleshooting](#-troubleshooting)
- [Future Improvements](#-future-improvements)

---

## 🔎 Overview

This project covers the full observability loop for a small web service:

1. **Build** a URL shortener (Flask + SQLite)
2. **Containerize** it with Docker
3. **Instrument** it with custom Prometheus metrics
4. **Collect** the metrics with Prometheus
5. **Visualize** them in Grafana (provisioned as code, no manual clicks)
6. **Alert** on important conditions (service down, 404 spikes, high latency)
7. **Persist** the database and monitoring data across restarts

## 🏗 Architecture

```
                    ┌──────────────────────┐
   Client ────────► │  Flask URL Shortener │
  (curl / browser)  │       :5000          │
                    │  /shorten  /<code>   │
                    │  /health   /metrics  │
                    └──────────┬───────────┘
                               │ scrape every 15s
                               ▼
                    ┌──────────────────────┐
                    │     Prometheus       │ ──► Alert rules
                    │       :9090          │
                    └──────────┬───────────┘
                               │ PromQL queries
                               ▼
                    ┌──────────────────────┐
                    │       Grafana        │
                    │       :3000          │
                    └──────────────────────┘
```

## 🧰 Tech Stack

| Component | Purpose |
|---|---|
| **Flask** | Web framework for the API |
| **SQLite** | File-based storage for URL mappings |
| **prometheus-client** | Custom counters and histograms |
| **prometheus-flask-exporter** | Exposes `/metrics` and default HTTP metrics |
| **Prometheus** | Metrics collection and alert rule evaluation |
| **Grafana** | Dashboards (datasource and dashboard provisioned from files) |
| **Docker / Docker Compose** | Packaging and orchestration |

## 📁 Project Structure

```
.
├── app.py                          # Flask app + custom metrics
├── requirements.txt                # Python dependencies
├── Dockerfile                      # App image
├── docker-compose.yml              # Full stack: app + Prometheus + Grafana
├── prometheus.yml                  # Scrape config + rule files
├── alerts.yml                      # Alerting rules
├── grafana.yml                     # Grafana datasource provisioning
├── dashboards.yml                  # Grafana dashboard provider
├── url-shortener-dashboard.json    # The dashboard definition
├── load_test.sh                    # Traffic generator for demos
├── templates/
│   └── index.html                  # Home page
└── docs/                           # Screenshots
```

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2

### Run the stack

```bash
git clone https://github.com/<your-username>/flask-monitoring-prometheus-grafana.git
cd flask-monitoring-prometheus-grafana
docker compose up --build -d
```

### Access the services

| Service | URL | Notes |
|---|---|---|
| URL Shortener | http://localhost:5000 | The web app |
| Prometheus | http://localhost:9090 | Query metrics, view alerts at `/alerts` |
| Grafana | http://localhost:3000 | Default login `admin` / `admin` |

### Generate traffic

So the dashboard has data to show:

```bash
chmod +x load_test.sh
./load_test.sh
```

The script creates 20 short links, then continuously requests them, mixing in random 404s.

### Stop the stack

```bash
docker compose down        # keeps data (volumes)
docker compose down -v     # deletes data too
```

## 📘 API Documentation

Base URL: `http://localhost:5000`

### `POST /shorten`

Creates a short code for a long URL.

**Request**

```bash
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | yes | The long URL to shorten |

**Responses**

`201 Created`

```json
{
  "short_code": "aB3xYz",
  "short_url": "/aB3xYz"
}
```

`400 Bad Request` (missing `url`)

```json
{ "error": "URL is required" }
```

### `GET /<short_code>`

Looks up the code and redirects to the original URL.

```bash
curl -i http://localhost:5000/aB3xYz
```

| Status | Meaning |
|---|---|
| `302 Found` | Redirects to the original URL (`Location` header) |
| `404 Not Found` | Unknown short code: `{"error": "Short URL not found"}` |

### `GET /health`

Health check endpoint.

```json
{ "status": "healthy" }
```

### `GET /metrics`

Prometheus metrics in the text exposition format. Scraped automatically by Prometheus.

## 📈 Metrics

### Custom application metrics

| Metric | Type | Description |
|---|---|---|
| `urls_shortened_total` | Counter | URLs successfully shortened |
| `successful_redirects_total` | Counter | Successful redirects |
| `failed_lookups_total` | Counter | Failed lookups (404s) |
| `shorten_request_latency_seconds` | Histogram | Latency of `POST /shorten` |
| `redirect_request_latency_seconds` | Histogram | Latency of redirect requests |

Default HTTP metrics (request counts, durations by endpoint and status) are also exposed by `prometheus-flask-exporter`.

### Example PromQL queries

```promql
# Rate of URL creations per second
rate(urls_shortened_total[1m])

# Rate of redirects per second
rate(successful_redirects_total[1m])

# 95th percentile redirect latency
histogram_quantile(0.95, sum by (le) (rate(redirect_request_latency_seconds_bucket[5m])))

# 404 rate
rate(failed_lookups_total[1m])
```

## 📺 Grafana Dashboard

The **URL Shortener Service** dashboard is provisioned automatically at startup (folder: General).

| Panel | Type | Query |
|---|---|---|
| Total Shortened Links | Stat | `sum(urls_shortened_total)` |
| URL Creations vs Redirections (per second) | Time series | `rate(urls_shortened_total[1m])`, `rate(successful_redirects_total[1m])` |
| 95th Percentile Request Latency | Time series | `histogram_quantile(0.95, ...)` for `/shorten` and redirect |
| 404 Error Rate | Time series | `rate(failed_lookups_total[1m])` |

The dashboard refreshes every 5 seconds.

### Screenshots

> Add your screenshots to `docs/` and uncomment:

<!--
![Dashboard](docs/dashboard.png)
![Alerts](docs/alerts.png)
-->

## 🚨 Alerting

Alert rules live in [`alerts.yml`](alerts.yml) and are loaded by Prometheus (view them at http://localhost:9090/alerts).

| Alert | Condition | For | Severity |
|---|---|---|---|
| `WebServiceDown` | `up{job="web"} == 0` | 30s | critical |
| `HighNotFoundRate` | 404 rate > 1/s | 1m | warning |
| `HighP95Latency` | p95 redirect latency > 500ms | 2m | warning |

To trigger `HighNotFoundRate`, hammer unknown codes:

```bash
while true; do curl -s -o /dev/null http://localhost:5000/doesnotexist$RANDOM; done
```

## 💾 Data Persistence

Named Docker volumes keep all stateful data across restarts:

| Volume | Mounted at | Data |
|---|---|---|
| `sqlite-data` | `/app/data` | SQLite database (`urls.db`) |
| `prometheus-data` | `/prometheus` | Prometheus time series |
| `grafana-data` | `/var/lib/grafana` | Grafana state |

## ✅ Testing the Stack

Verify persistence end to end:

1. Start the stack and create a few links:
   ```bash
   docker compose up --build -d
   curl -X POST localhost:5000/shorten -H "Content-Type: application/json" -d '{"url":"https://example.com"}'
   ```
2. Restart everything:
   ```bash
   docker compose down
   docker compose up -d
   ```
3. Confirm:
   - The short link still redirects
   - Grafana still shows historical data
   - Alert rules are listed at http://localhost:9090/alerts

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| Prometheus target `web` is **DOWN** | Check `docker compose logs web` and that `prometheus.yml` targets `web:5000` |
| Grafana panels show "No data" | Run `./load_test.sh`, then check the datasource under Connections → Data sources |
| Port already in use | Change the host port in `docker-compose.yml` (e.g. `"5001:5000"`) |
| Dashboard not loading | Check that `url-shortener-dashboard.json` is mounted to `/var/lib/grafana/dashboards/` |

## 🔮 Future Improvements

- [ ] Alertmanager with Slack / Email notifications
- [ ] Grafana-managed alert rules
- [ ] `node-exporter` and `cAdvisor` for infrastructure metrics
- [ ] Loki + Promtail for log aggregation
- [ ] CI pipeline with GitHub Actions
- [ ] Unit tests with `pytest`
- [ ] Run behind Gunicorn instead of the Flask dev server

## 📄 License

MIT
