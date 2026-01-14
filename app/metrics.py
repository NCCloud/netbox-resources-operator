import time
import functools
import kopf
from requests import Session
from prometheus_client import Counter, Gauge, Histogram

METRIC_PREFIX = "netbox_resources_operator"

OPERATOR_RECONCILE_DURATION_SECONDS = Histogram(
    name=f"{METRIC_PREFIX}_operator_reconcile_duration_seconds",
    documentation="Time spent reconciling",
)

OPERATOR_RECONCILE_ERRORS_TOTAL = Counter(
    name=f"{METRIC_PREFIX}_operator_reconcile_errors_total",
    documentation=("The total number of errors encountered while reconciling"),
    labelnames=["error_type"],
)

OPERATOR_RECONCILE_TOTAL = Counter(
    name=f"{METRIC_PREFIX}_operator_reconcile_total",
    documentation="The total number of operator reconciliations",
)

OPERATOR_ACTIVE_WORKERS = Gauge(
    name=f"{METRIC_PREFIX}_operator_active_workers",
    documentation="The number of currently active operator workers",
)

OPERATOR_MAX_WORKERS = Gauge(
    name=f"{METRIC_PREFIX}_operator_max_workers",
    documentation="The total number of workers, same as max_concurrent_reconciles",
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    name=f"{METRIC_PREFIX}_http_request_duration_seconds",
    documentation="Time spent processing NetBox HTTP request",
    labelnames=["status_code", "method"],
)

HTTP_REQUEST_TOTAL = Counter(
    name=f"{METRIC_PREFIX}_http_request_total",
    documentation="The total number of HTTP requests by status code and method",
    labelnames=["status_code", "method"],
)


def collect_operator_reconcile_metrics(func):
    """
    Collect metrics for an operator request
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        error_class = None

        OPERATOR_RECONCILE_TOTAL.inc()

        try:
            OPERATOR_ACTIVE_WORKERS.inc()
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error_class = e.__class__.__name__.lower()
            raise
        finally:
            elapsed = time.perf_counter() - start_time
            OPERATOR_RECONCILE_DURATION_SECONDS.observe(elapsed)
            if error_class:
                OPERATOR_RECONCILE_ERRORS_TOTAL.labels(error_type=error_class).inc()

            OPERATOR_ACTIVE_WORKERS.dec()

    return wrapper


def collect_operator_configuration_metrics(settings: kopf.OperatorSettings):
    if settings.execution.max_workers:
        OPERATOR_MAX_WORKERS.set(settings.execution.max_workers)


class InstrumentedSession(Session):
    """
    requests.Session with support for Prometheus metrics
    """

    def request(self, method, url, *args, **kwargs):
        start_time = time.perf_counter()

        response = super().request(method, url, *args, **kwargs)

        elapsed = time.perf_counter() - start_time
        status_code = str(response.status_code)

        HTTP_REQUEST_TOTAL.labels(status_code=status_code, method=method).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            status_code=status_code, method=method
        ).observe(elapsed)

        return response
