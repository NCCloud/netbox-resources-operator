import logging
from typing import Any

import kopf
from prometheus_client import start_http_server

from app.conditions import (
    set_failed_condition,
    set_reconciled_condition,
    set_reconciliation_conditions,
)
from app.config import Settings
from app.crd import NETBOX_OBJECT_CRD_NAME_FULL, NETBOX_OBJECT_CRD_NAME_LOWER
from app.handlers import handle_netboxobject, handle_netboxobject_deletion
from app.metrics import (
    collect_operator_configuration_metrics,
    collect_operator_reconcile_metrics,
)
from app.models import NetBoxObjectStatusPhaseEnum

app_settings = Settings()
logger = logging.getLogger("kopf.objects")


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    # by default, the number of workers is unlimited
    settings.batching.worker_limit = app_settings.operator_worker_limit
    # don't post to Kubernetes events
    settings.posting.enabled = False
    # by default, the number of execution workers is unlimited
    settings.execution.max_workers = app_settings.operator_worker_limit

    collect_operator_configuration_metrics(settings)

    logger.info(
        "Starting Prometheus server on port %s", app_settings.prometheus_metrics_port
    )
    start_http_server(app_settings.prometheus_metrics_port)


@kopf.timer(
    NETBOX_OBJECT_CRD_NAME_FULL,
    id=NETBOX_OBJECT_CRD_NAME_LOWER,
    retries=app_settings.operator_retry_limit,
    backoff=app_settings.operator_backoff_seconds,
    idle=app_settings.operator_timer_idle_seconds,
    interval=app_settings.operator_timer_interval_seconds,
)
@kopf.on.create(
    NETBOX_OBJECT_CRD_NAME_FULL,
    id=NETBOX_OBJECT_CRD_NAME_LOWER,
    retries=app_settings.operator_retry_limit,
    backoff=app_settings.operator_backoff_seconds,
)
@kopf.on.update(
    NETBOX_OBJECT_CRD_NAME_FULL,
    id=NETBOX_OBJECT_CRD_NAME_LOWER,
    retries=app_settings.operator_retry_limit,
    backoff=app_settings.operator_backoff_seconds,
)
@kopf.on.delete(
    NETBOX_OBJECT_CRD_NAME_FULL,
    retries=app_settings.operator_retry_limit,
    backoff=app_settings.operator_backoff_seconds,
)
@collect_operator_reconcile_metrics
def reconcile(
    name: str,
    spec: kopf.Spec,
    status: kopf.Status,
    meta: kopf.Meta,
    patch: kopf.Patch,
    retry: int,
    old: Any = {},
    **_,
):
    """
    Handle NetBoxObject lifecycle
    """
    deleting = meta.get("deletionTimestamp") is not None
    generation_mismatch = status.get("observedGeneration") != meta.get("generation")

    if not deleting and not generation_mismatch:
        logger.debug(
            "[%s] The object shouldn't be reconciled as it's neither deleted nor the spec is updated",
            name,
        )
        return

    logger.info("[%s] Starting reconciliation", name)
    set_reconciliation_conditions(patch)
    patch.status["phase"] = NetBoxObjectStatusPhaseEnum.PROGRESSING.value

    result = {}
    try:
        if deleting:
            logger.info("[%s] Deleting the object", name)
            handle_netboxobject_deletion(name=name, spec=spec, status=status)
            return

        result = handle_netboxobject(
            name=name, spec=spec, status=status, old=old, patch=patch
        )

    except kopf.PermanentError as e:
        logger.error("[%s] A permanent error has been raised", name)
        set_failed_condition(patch=patch, error=str(e))
        patch.status["phase"] = NetBoxObjectStatusPhaseEnum.FAILED.value
        raise e
    except Exception as e:
        if retry == app_settings.operator_retry_limit - 1:
            logger.error(
                "[%s] Retry attempts exhausted, the handler failed permanently", name
            )
            set_failed_condition(patch=patch, error=str(e))
            patch.status["phase"] = NetBoxObjectStatusPhaseEnum.FAILED.value
        raise e

    set_reconciled_condition(patch)
    patch.status["phase"] = NetBoxObjectStatusPhaseEnum.PROVISIONED.value

    patch.status["observedGeneration"] = meta["generation"]

    patch.status.setdefault("netboxobject", {})
    patch.status["netboxobject"].update(result)
