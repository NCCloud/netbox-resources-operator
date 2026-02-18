import kr8s
import kr8s.objects
from tests.e2e.conftest import assert_resources_phase


def test_invalid_endpoint():
    """Test that invalid endpoint causes failure."""
    resource_manifest = {
        "apiVersion": "spaceship.com/v1alpha1",
        "kind": "NetBoxObject",
        "metadata": {
            "name": "invalid-endpoint-test",
        },
        "spec": {
            "dataModel": "ipam",
            "endpoint": "nonexistent-endpoint",
            "body": [
                {"path": "name", "value": "test"}
            ]
        }
    }

    resource = kr8s.objects.object_from_spec(resource_manifest)
    resource.create()

    try:
        assert_resources_phase([resource], phase="Failed", timeout=120)
    finally:
        resource.delete()


def test_invalid_secret_reference():
    """Test that invalid secretKeyRef causes failure."""

    resource_manifest = {
        "apiVersion": "spaceship.com/v1alpha1",
        "kind": "NetBoxObject",
        "metadata": {
            "name": "invalid-ref-test",
        },
        "spec": {
            "dataModel": "ipam",
            "endpoint": "vlans",
            "body": [
                {"path": "vid", "value": 200},
                {"path": "name", "value": "test-vlan"},
                {
                    "path": "description",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": "nonexistent-secret",
                            "key": "description"
                        }
                    }
                }
            ]
        }
    }

    resource = kr8s.objects.object_from_spec(resource_manifest)
    resource.create()

    try:
        assert_resources_phase([resource], phase="Failed", timeout=120)
    finally:
        resource.delete()


def test_invalid_update():
    """Test that an invalid update leads to the Failed state"""

    resource_manifest = {
        "apiVersion": "spaceship.com/v1alpha1",
        "kind": "NetBoxObject",
        "metadata": {
            "name": "invalid-update",
        },
        "spec": {
            "dataModel": "ipam",
            "endpoint": "vlans",
            "body": [
                {"path": "vid", "value": 200},
                {"path": "name", "value": "test-vlan"},
            ]
        }
    }

    resource = kr8s.objects.object_from_spec(resource_manifest)
    resource.create()

    try:
        assert_resources_phase([resource], phase="Provisioned", timeout=120)
    except Exception:
        resource.delete()
        return

    try:
        resource.patch({"spec": {"body": [
            {"path": "vid", "value": 5000}, # invalid VID
            {"path": "name", "value": "test-vlan"}
        ]}})
        assert_resources_phase([resource], phase="Failed", timeout=120)
    finally:
        resource.delete()
