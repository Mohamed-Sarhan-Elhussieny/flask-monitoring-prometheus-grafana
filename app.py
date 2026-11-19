from flask import Flask, render_template, request, jsonify, redirect
import sqlite3
import string
import random
import time

from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram

app = Flask(__name__)
metrics = PrometheusMetrics(app)
urls_shortened_total = Counter(
    "urls_shortened_total",
    "Total number of URLs successfully shortened"
)

successful_redirects_total = Counter(
    "successful_redirects_total",
    "Total number of successful redirects"
)

failed_lookups_total = Counter(
    "failed_lookups_total",
    "Total number of failed URL lookups"
)

shorten_latency = Histogram(
    "shorten_request_latency_seconds",
    "Latency of URL shortening requests"
)

redirect_latency = Histogram(
    "redirect_request_latency_seconds",
    "Latency of URL redirect requests"
)

@app.route("/")
def home():
    return render_template("index.html")
DATABASE = "urls.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            long_url TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


@app.route("/shorten", methods=["POST"])
def shorten_url():

    with shorten_latency.time():

        data = request.get_json()

        if not data or "url" not in data:
            return jsonify({
                "error": "URL is required"
            }), 400

        long_url = data["url"]

        short_code = generate_short_code()

        conn = get_db()

        while conn.execute(
            "SELECT id FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone():
            short_code = generate_short_code()

        conn.execute(
            "INSERT INTO urls (short_code, long_url) VALUES (?, ?)",
            (short_code, long_url)
        )

        conn.commit()
        conn.close()

        urls_shortened_total.inc()

        return jsonify({
            "short_code": short_code,
            "short_url": f"/{short_code}"
        }), 201


@app.route("/<short_code>", methods=["GET"])
def redirect_url(short_code):

    with redirect_latency.time():

        conn = get_db()

        result = conn.execute(
            "SELECT long_url FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        conn.close()

        if result is None:

            failed_lookups_total.inc()

            return jsonify({
                "error": "Short URL not found"
            }), 404

        successful_redirects_total.inc()

        return redirect(result["long_url"])


@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy"
    }), 200


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
