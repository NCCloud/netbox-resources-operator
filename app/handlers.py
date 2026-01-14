from typing import Any
import kopf
import logging
from apischema import ValidationError
from app.netboxobject import NetBoxObjectReconciler
from app.config import Settings

app_settings = Settings()
logger = logging.getLogger("kopf.objects")


def handle_netboxobject(name: str, spec: dict, status: dict, old: Any, **_):
    """
    Handle NetBox object creation and updates
    """
    old_spec = old.get("spec", {}) if isinstance(old, dict) else {}

    netbox_object_reconciler = NetBoxObjectReconciler(
        k8s_object_name=name,
        spec=dict(spec),
        old_spec=old_spec,
        k8s_object_status=dict(status),
    )

    result = netbox_object_reconciler.create_or_update()

    return result


def handle_netboxobject_deletion(name: str, spec: dict, status: dict, **_):
    """
    Handle NetBox object deletion
    """
    try:
        netbox_object_reconciler = NetBoxObjectReconciler(
            k8s_object_name=name, spec=dict(spec), k8s_object_status=dict(status)
        )
    except ValidationError as e:
        raise kopf.PermanentError(
            f"[{name}] Spec is invalid, cannot reliably handle the deletion, error: {e.errors}"
        ) from e

    if netbox_object_reconciler.netbox_object.preserve_on_delete:
        logger.info(
            "[%s] Skipping NetBox object deletion because `preserveOnDelete` is True",
            name,
        )
        return

    netbox_object_reconciler.delete()
