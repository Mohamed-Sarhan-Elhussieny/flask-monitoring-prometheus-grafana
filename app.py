import os
import secrets
import string
import time
from threading import Lock
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest


app = Flask(__name__)

URLS = {}
URLS_LOCK = Lock()
CODE_ALPHABET = string.ascii_letters + string.digits

REQUEST_COUNT = Counter(
    "url_shortener_http_requests_total",
    "Total HTTP requests handled by the URL shortener.",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "url_shortener_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["endpoint"],
)
SHORTENED_URLS = Counter(
    "url_shortener_urls_created_total",
    "Total number of URLs shortened.",
)
REDIRECTS = Counter(
    "url_shortener_redirects_total",
    "Total number of successful URL redirects.",
)
STORED_URLS = Gauge(
    "url_shortener_stored_urls",
    "Number of URLs currently stored.",
)


def is_valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def new_code(length=6):
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))
        if code not in URLS:
            return code


@app.before_request
def start_request_timer():
    request._metrics_started_at = time.perf_counter()


@app.after_request
def record_request(response):
    endpoint = request.endpoint or "unknown"
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    started_at = getattr(request, "_metrics_started_at", None)
    if started_at is not None:
        REQUEST_LATENCY.labels(endpoint).observe(time.perf_counter() - started_at)
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/shorten")
def shorten():
    payload = request.get_json(silent=True) or request.form
    original_url = (payload.get("url") or "").strip()

    if not is_valid_url(original_url):
        return jsonify(error="Enter a valid http:// or https:// URL."), 400

    with URLS_LOCK:
        code = new_code()
        URLS[code] = original_url
        STORED_URLS.set(len(URLS))

    SHORTENED_URLS.inc()
    short_url = request.host_url.rstrip("/") + "/" + code
    return jsonify(code=code, short_url=short_url, url=original_url), 201


@app.get("/<code>")
def follow(code):
    with URLS_LOCK:
        destination = URLS.get(code)

    if destination is None:
        return render_template("index.html", error="Short URL not found."), 404

    REDIRECTS.inc()
    return redirect(destination)


@app.get("/health")
def health():
    return jsonify(status="ok", stored_urls=len(URLS))


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": "text/plain; version=0.0.4"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
