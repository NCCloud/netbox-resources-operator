"""
Test real scenarios from the "examples" folder
"""
import kr8s
import pynetbox
from tests.e2e.conftest import assert_resources_phase


def test_device_setup(apply_yaml, netbox_client: pynetbox.api):
    resources: list[kr8s.objects.APIObject] = apply_yaml(
        "examples/device_setup.yaml")

    # test creation
    assert_resources_phase(resources, phase="Provisioned")

    device = resources[-1]

    netbox_device = netbox_client.dcim.devices.get(
        name="test-device")

    assert netbox_device is not None
    assert netbox_device.id == device.status.netboxobject.id
    assert netbox_device.site.name == "test-site"
    assert netbox_device.tenant.name == "test-tenant"
    assert netbox_device.location.name == "testing"
    assert netbox_device.platform.name == "test-platform"
    assert netbox_device.role.name == "Test"
    assert netbox_device.device_type.model == "test-model"

    # test deletion
    device.delete()
    device.wait(conditions=["delete"], timeout=30)

    netbox_device = netbox_client.dcim.devices.get(
        name="test-device")

    assert netbox_device is None


def test_device_primary_ip(apply_yaml, netbox_client: pynetbox.api):
    setup_resources = apply_yaml("examples/device_setup.yaml")

    # test creation of dependent resources
    assert_resources_phase(setup_resources, phase="Provisioned")

    resources: list[kr8s.objects.APIObject] = apply_yaml(
        "examples/device_primary_ip.yaml")

    interface, ip_address, device = resources

    # test creation of this test subjects
    assert_resources_phase(resources, phase="Provisioned")

    netbox_device = netbox_client.dcim.devices.get(
        name="test-device")

    assert netbox_device is not None
    assert netbox_device.id == device.status.netboxobject.id
    assert netbox_device.primary_ip4.address == "10.0.0.1/32"

    # test deletion
    device.delete()
    device.wait(conditions=["delete"], timeout=30)

    ip_address.delete()
    ip_address.wait(conditions=["delete"], timeout=30)

    interface.delete()
    interface.wait(conditions=["delete"], timeout=30)

    netbox_device = netbox_client.dcim.devices.get(
        name="test-device")
    assert netbox_device is not None

    netbox_ip = netbox_client.ipam.ip_addresses.get(
        address="10.0.0.1/32")
    assert netbox_ip is None

    netbox_interface = netbox_client.dcim.interfaces.get(
        name=interface.name,
        device=netbox_device.name if netbox_device else None)
    assert netbox_interface is None


def test_allocate_available_vlan(apply_yaml, netbox_client: pynetbox.api):
    resources: list[kr8s.objects.APIObject] = apply_yaml(
        "examples/allocate_available_vlan.yaml")

    # test creation
    assert_resources_phase(resources, phase="Provisioned")

    vlan_group, group_available_vlan, global_available_vlan = resources

    netbox_vlan_group = netbox_client.ipam.vlan_groups.get(
        name="test-vlan-group")

    assert netbox_vlan_group is not None
    assert netbox_vlan_group.id == vlan_group.status.netboxobject.id

    netbox_group_available_vlan = netbox_client.ipam.vlans.get(
        tag=["group-available-vlan"])

    assert netbox_group_available_vlan is not None
    assert netbox_group_available_vlan.id == group_available_vlan.status.netboxobject.id
    assert netbox_group_available_vlan.group.id == netbox_vlan_group.id

    netbox_global_available_vlan = netbox_client.ipam.vlans.get(
        tag=["global-available-vlan"])

    assert netbox_global_available_vlan is not None
    assert netbox_global_available_vlan.id == global_available_vlan.status.netboxobject.id
    assert netbox_global_available_vlan.group.id == netbox_vlan_group.id

    # test deletion
    group_available_vlan.delete()
    group_available_vlan.wait(conditions=["delete"], timeout=30)

    global_available_vlan.delete()
    global_available_vlan.wait(conditions=["delete"], timeout=30)

    vlan_group.delete()
    vlan_group.wait(conditions=["delete"], timeout=30)

    # Verify deletion in NetBox
    netbox_vlan_group = netbox_client.ipam.vlan_groups.get(
        name="test-vlan-group")
    assert netbox_vlan_group is None

    netbox_group_available_vlan = netbox_client.ipam.vlans.get(
        tag=["group-available-vlan"])
    assert netbox_group_available_vlan is None

    netbox_global_available_vlan = netbox_client.ipam.vlans.get(
        tag=["global-available-vlan"])
    assert netbox_global_available_vlan is None


def test_allocate_available_ip(apply_yaml, netbox_client: pynetbox.api):
    resources: list[kr8s.objects.APIObject] = apply_yaml(
        "examples/allocate_available_ip.yaml")

    # test creation
    assert_resources_phase(resources, phase="Provisioned")

    ip, ip_range, available_ip = resources

    netbox_ip = netbox_client.ipam.ip_addresses.get(address="10.0.0.5/24")

    assert netbox_ip is not None
    assert netbox_ip.id == ip.status.netboxobject.id

    netbox_ip_range = netbox_client.ipam.ip_ranges.get(
        contains="10.0.0.10/24")

    assert netbox_ip_range is not None
    assert netbox_ip_range.id == ip_range.status.netboxobject.id

    netbox_available_ip_address = netbox_client.ipam.ip_addresses.get(
        address="10.0.0.1/24")

    assert netbox_available_ip_address is not None
    assert netbox_available_ip_address.id == available_ip.status.netboxobject.id

    available_ip.delete()
    available_ip.wait(conditions=["delete"], timeout=30)

    # test deletion
    ip.delete()
    ip.wait(conditions=["delete"], timeout=30)

    ip_range.delete()
    ip_range.wait(conditions=["delete"], timeout=30)

    netbox_ip = netbox_client.ipam.ip_addresses.get(address="10.0.0.5/24")
    assert netbox_ip is None

    netbox_ip_range = netbox_client.ipam.ip_ranges.get(
        contains="10.0.0.10/24")
    assert netbox_ip_range is None

    netbox_available_ip_address = netbox_client.ipam.ip_addresses.get(
        address="10.0.0.1/24")
    assert netbox_available_ip_address is None


def test_reference_existing_objects(apply_yaml, netbox_client: pynetbox.api):
    resources: list[kr8s.objects.APIObject] = apply_yaml(
        "examples/reference_existing_objects.yaml")
    _, _, tenant, vlan_group, vlan_a, vlan_b = resources

    # test creation
    assert_resources_phase(
        [tenant, vlan_group, vlan_a, vlan_b], phase="Provisioned")

    netbox_vlan_group = netbox_client.ipam.vlan_groups.get(
        name="temporary-test")

    assert netbox_vlan_group is not None
    assert netbox_vlan_group.id == vlan_group.status.netboxobject.id

    netbox_vlan_a = netbox_client.ipam.vlans.get(
        name="vlan-1234")

    assert netbox_vlan_a is not None
    assert netbox_vlan_a.id == vlan_a.status.netboxobject.id
    assert netbox_vlan_a.group.id == netbox_vlan_group.id
    assert netbox_vlan_a.tenant.name == "test-tenant"

    netbox_vlan_b = netbox_client.ipam.vlans.get(
        name="vlan-1324")

    assert netbox_vlan_b is not None
    assert netbox_vlan_b.id == vlan_b.status.netboxobject.id
    assert netbox_vlan_b.group.id == netbox_vlan_group.id
    assert netbox_vlan_a.tenant.name == "test-tenant"

    # test deletion
    vlan_a.delete()
    vlan_a.wait(conditions=["delete"], timeout=30)

    vlan_b.delete()
    vlan_b.wait(conditions=["delete"], timeout=30)

    vlan_group.delete()
    vlan_group.wait(conditions=["delete"], timeout=30)

    netbox_vlan_group = netbox_client.ipam.vlan_groups.get(
        name="temporary-test")

    assert netbox_vlan_group is None

    netbox_vlan_a = netbox_client.ipam.vlans.get(
        name="vlan-1234")

    assert netbox_vlan_a is None

    netbox_vlan_b = netbox_client.ipam.vlans.get(
        name="vlan-1324")

    assert netbox_vlan_b is None
