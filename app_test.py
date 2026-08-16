from __future__ import annotations

from flask import Flask, redirect, request


TARGET_BASE = "https://druswayne-valera-ac38.twc1.net"

app = Flask(__name__)


def _build_target_url(path: str) -> str:
    # request.query_string is bytes; keep exact encoding
    qs = request.query_string.decode("utf-8", errors="ignore")
    if qs:
        return f"{TARGET_BASE}/{path}?{qs}"
    return f"{TARGET_BASE}/{path}"


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
def proxy_redirect(path: str):
    # 307 preserves method and body for non-GET requests
    return redirect(_build_target_url(path), code=307)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

