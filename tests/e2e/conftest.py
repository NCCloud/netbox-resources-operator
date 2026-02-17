import time
import pytest
import kr8s
import base64
import pynetbox

NetBoxObject = kr8s.objects.new_class(
    kind="NetBoxObject",
    version="spaceship.com/v1alpha1",
    namespaced=False
)


@pytest.fixture
def apply_yaml():
    created = []

    def _apply(path: str):
        resources = kr8s.objects.objects_from_files(path)
        kr8s.create(resources)
        created.extend(resources)
        return resources

    yield _apply

    # teardown
    # this will do soft delete
    for r in reversed(created):
        try:
            r.delete()
        except kr8s.NotFoundError:
            pass

    # therefore, wait for objects to disappear
    for r in reversed(created):
        try:
            r.wait(conditions=["delete"], timeout=60)
        except kr8s.NotFoundError:
            pass


@pytest.fixture
def netbox_client():
    nb_svc = kr8s.objects.Service.get("netbox", namespace="default")

    # start port-forward
    pf = nb_svc.portforward(remote_port=8080, local_port=None)

    # Start the background thread
    pf.start()

    netbox_token_secret = kr8s.objects.Secret.get(name="netbox-token")
    secret_data_b64 = netbox_token_secret.data.get("token")
    netbox_token = base64.b64decode(secret_data_b64).decode("utf-8")

    nb = pynetbox.api(
        url=f"http://localhost:{pf.local_port}",
        token=netbox_token
    )
    yield nb

    # Stop port-forward after the test completion
    pf.stop()


def assert_resources_phase(
    resources: list[kr8s.objects.APIObject],
    phase: str,
    timeout: int = 60,
    max_initial_delay_seconds=15,
) -> None:
    """
    Assert all resources reach the desired phase
    """
    # initial delay for the operator to register resources
    # and populate with status
    elapsed = 0
    for resource in resources:
        while elapsed < max_initial_delay_seconds:
            resource.refresh()
            if "status" in dict(resource) and resource.status.get("phase"):
                break
            time.sleep(1)
            elapsed += 1

    for resource in resources:
        try:
            resource.wait(
                conditions=[f"jsonpath='{{.status.phase}}'={phase}"],
                timeout=timeout
            )
        except TimeoutError:
            resource.refresh()
            raise AssertionError(
                f"{resource.kind}/{resource.name} failed to reach phase {phase} in {timeout} seconds "
                f"(current: {resource.status.get('phase', 'unknown')})"
            )
