# monitoring.py  (create this file and import it in app.py)
import os
import time
import threading
import psutil
from applicationinsights import TelemetryClient
from flask import request, g, current_app
from dotenv import load_dotenv

load_dotenv()

# Use connection string if you have it, otherwise use instrumentation key
CONN_STR = os.getenv("APPINSIGHTS_CONNECTION_STRING")
INSTR_KEY = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")

if CONN_STR:
    tc = TelemetryClient(None)
    tc.context.instrumentation_key = None
    # applicationinsights library uses instrumentation key only; if you have only connection string,
    # extract the key or use environment APPINSIGHTS_INSTRUMENTATIONKEY instead.
# Fallback to instrumentation key
tc = TelemetryClient(INSTR_KEY or "")

# Attach some app info
tc.context.device.role_name = "FacultyLeaveApp"

# ---- Flask hooks to track requests & exceptions ----
def init_app(app):
    @app.before_request
    def start_timer():
        g._start_time = time.time()

    @app.after_request
    def log_request(response):
        try:
            duration = int((time.time() - g._start_time) * 1000)  # ms
        except Exception:
            duration = 0

        # Track a request as an event (you can also use track_request but this simple approach works)
        tc.track_event("request", {
            "path": request.path,
            "method": request.method,
            "status_code": response.status_code
        }, {"duration_ms": duration})

        # custom metric: request count
        tc.track_metric("requests_count", 1)
        # custom metric: request duration
        tc.track_metric("request_duration_ms", duration)

        tc.flush()
        return response

    @app.teardown_request
    def log_exception(exc):
        if exc is not None:
            # Track exceptions
            tc.track_exception()
            tc.track_metric("errors_count", 1)
            tc.flush()

# ---- Background CPU telemetry ----
def start_cpu_metric_loop(interval_seconds=10):
    def loop():
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                tc.track_metric("CPU_percent", cpu)
                tc.flush()
            except Exception as e:
                # don't crash thread
                print("CPU metric error:", e)
            time.sleep(interval_seconds)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
