import unittest
from apischema import ValidationError, deserialize
from app.models import NetBoxObjectValueFrom, NetBoxObjectBodyItem, NetBoxObject


class TestNetBoxObjectValueFrom(unittest.TestCase):
    def test_multiple_values_set(self):
        with self.assertRaises(ValidationError) as ctx:
            data = {
                "secretKeyRef": {"key": "user", "name": "test"},
                "configMapKeyRef": {"key": "user", "name": "test"},
            }
            deserialize(NetBoxObjectValueFrom, data)

        self.assertIn("Only one value reference should be provided", str(ctx.exception))

    def test_no_values_set(self):
        with self.assertRaises(ValidationError) as ctx:
            deserialize(NetBoxObjectValueFrom, {})

        self.assertIn(
            "Either secretKeyRef or configMapKeyRef or netboxObjRef must be set",
            str(ctx.exception),
        )

    def test_one_value(self):
        data = {
            "secretKeyRef": {"key": "user", "name": "test"},
        }
        try:
            deserialize(NetBoxObjectValueFrom, data)
        except ValidationError as e:
            self.fail(f"an unexpected ValidationError was raised: {e}")


class TestNetBoxObjectBodyItem(unittest.TestCase):
    def test_multiple_values_set(self):
        with self.assertRaises(ValidationError) as ctx:
            data = {
                "path": "field",
                "value": 1,
                "valueFrom": {"secretKeyRef": {"key": "user", "name": "test"}},
            }
            deserialize(NetBoxObjectBodyItem, data)

        self.assertIn(
            "Only one of value or valueFrom must be provided", str(ctx.exception)
        )

    def test_no_values_set(self):
        with self.assertRaises(ValidationError) as ctx:
            data = {"path": "field"}
            deserialize(NetBoxObjectBodyItem, data)

        self.assertIn("Either value or valueFrom must be set", str(ctx.exception))

    def test_one_value_set(self):
        data = {"path": "field", "value": 1}
        try:
            deserialize(NetBoxObjectBodyItem, data)
        except ValidationError as e:
            self.fail(f"an unexpected ValidationError was raised: {e}")


class TestNetBoxObject(unittest.TestCase):
    def test_unsupported_endpoint_for_resource_allocation(self):
        data = {
            "dataModel": "dcim",
            "endpoint": "devices",
            "body": [{"path": "field", "value": 1}],
            "allocateAvailable": True,
        }

        with self.assertRaises(ValidationError) as ctx:
            deserialize(NetBoxObject, data)

        self.assertIn("Endpoint must be one of these", str(ctx.exception))

    def test_no_id_path_for_resource_allocation(self):
        data = {
            "dataModel": "ipam",
            "endpoint": "prefixes",
            "body": [{"path": "field", "value": 1}],
            "allocateAvailable": True,
        }

        with self.assertRaises(ValidationError) as ctx:
            deserialize(NetBoxObject, data)

        self.assertIn(
            "body must contain the 'id' path to find the existing parent resource",
            str(ctx.exception),
        )

    def test_valid_for_resource_allocation(self):
        data = {
            "dataModel": "ipam",
            "endpoint": "prefixes",
            "body": [
                {"path": "id", "value": 1},
            ],
            "allocateAvailable": True,
        }

        try:
            deserialize(NetBoxObject, data)
        except ValidationError as e:
            self.fail(f"an unexpected ValidationError was raised: {e}")
