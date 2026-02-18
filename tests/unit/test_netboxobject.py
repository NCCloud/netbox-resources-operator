# pylint: disable=protected-access
import unittest
from kopf import PermanentError
from unittest.mock import Mock, patch
from tests.unit.util import DummyNetBoxRecord
from app.netboxobject import NetBoxObjectReconciler, MANAGED_OBJECT_DESCRIPTION
from app.errors import NetBoxConflict, NetBoxObjectNotFound


class TestNetBoxObjectReconciler(unittest.TestCase):
    def setUp(self):
        self.netbox_resolve = {
            "dataModel": "ipam",
            "endpoint": "vlan-groups",
            "filter": "name__ic=test",
            "path": "id",
        }
        self.secret_key_ref = {"key": "token", "name": "test-secret"}
        self.configmap_key_ref = {"key": "data", "name": "test-configmap"}
        self.k8s_object_name = "test"
        self.spec = {
            "dataModel": "ipam",
            "endpoint": "vlans",
            "body": [
                {
                    "path": "group.id",
                    "valueFrom": {"netboxObjRef": self.netbox_resolve},
                },
                {"path": "vid", "valueFrom": {"secretKeyRef": self.secret_key_ref}},
                {
                    "path": "description",
                    "valueFrom": {"configMapKeyRef": self.configmap_key_ref},
                },
                {"path": "name", "value": self.k8s_object_name, "lookupKey": True},
                {
                    "path": "tags",
                    "value": [1, 2],
                    "lookupKey": True,
                    "lookupAlias": "tag",
                },
            ],
        }
        old_spec = self.spec.copy()
        old_spec_body: list = self.spec["body"].copy()
        old_spec_body.extend(
            [
                {"path": "tenant.id", "value": 1},
                {
                    "path": "status",
                    "valueFrom": {
                        "configMapKeyRef": {"key": "status", "name": "test-configmap"}
                    },
                },
            ]
        )
        old_spec["body"] = old_spec_body

        self.k8s_object_status = {
            "netboxobject": {
                "id": 1,
                "url": "dummy-url",
                "endpoint": "vlans",
                "dataModel": "ipam",
            }
        }

        self.netbox_obj_reconciler = NetBoxObjectReconciler(
            k8s_object_name=self.k8s_object_name,
            spec=self.spec,
            old_spec=old_spec,
            k8s_object_status=self.k8s_object_status,
        )

    @patch(
        "pynetbox.core.endpoint.Endpoint.get", return_value=DummyNetBoxRecord({"id": 1})
    )
    def test__resolve_netbox_value__success(self, mock_get: Mock):
        expected = 1

        obj_ref = self.netbox_obj_reconciler.netbox_object.body[
            0
        ].value_from.netbox_obj_ref
        actual = self.netbox_obj_reconciler._resolve_netbox_value(
            netbox_resolve=obj_ref
        )

        self.assertEqual(expected, actual)

        mock_get.assert_called_once()

    @patch("pynetbox.core.endpoint.Endpoint.get", return_value=DummyNetBoxRecord())
    def test__resolve_netbox_value__obj_not_found(self, mock_get: Mock):
        obj_ref = self.netbox_obj_reconciler.netbox_object.body[
            0
        ].value_from.netbox_obj_ref

        with self.assertRaises(NetBoxObjectNotFound):
            self.netbox_obj_reconciler._resolve_netbox_value(netbox_resolve=obj_ref)

        mock_get.assert_called_once()

    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord({"name": "test"}),
    )
    def test__resolve_netbox_value__value_not_found(self, mock_get: Mock):
        obj_ref = self.netbox_obj_reconciler.netbox_object.body[
            0
        ].value_from.netbox_obj_ref

        with self.assertRaises(ValueError):
            self.netbox_obj_reconciler._resolve_netbox_value(netbox_resolve=obj_ref)

        mock_get.assert_called_once()

    @patch("pynetbox.core.endpoint.Endpoint.get")
    def test__convert_tag_names_to_ids(self, mock_create_netbox_tags: Mock):
        mock_create_netbox_tags.side_effect = [
            DummyNetBoxRecord({"id": 1}),
            DummyNetBoxRecord({"id": 10}),
        ]
        expected = [1, 10]
        actual = self.netbox_obj_reconciler._convert_tag_names_to_ids(
            ["tag-a", "tag-b"]
        )

        self.assertEqual(expected, actual)
        self.assertEqual(mock_create_netbox_tags.call_count, 2)

    def test__get_netbox_compatible_value__tags_all_integers(self):
        expected = [1, 10]
        actual = self.netbox_obj_reconciler._get_netbox_compatible_value(
            path="tags", value=expected
        )

        self.assertEqual(expected, actual)

    @patch("pynetbox.core.endpoint.Endpoint.get")
    def test__get_netbox_compatible_value__tags_all_strings(
        self, mock_create_netbox_tags: Mock
    ):
        mock_create_netbox_tags.side_effect = [
            DummyNetBoxRecord({"id": 1}),
            DummyNetBoxRecord({"id": 5}),
        ]
        expected = [1, 5]
        actual = self.netbox_obj_reconciler._get_netbox_compatible_value(
            path="tags", value=["tag-a", "tag-b"]
        )

        self.assertEqual(expected, actual)
        self.assertEqual(mock_create_netbox_tags.call_count, 2)

    @patch("app.netboxobject.get_config_map_value", return_value="test description")
    @patch("app.netboxobject.get_secret_value", return_value=10)
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._resolve_netbox_value", return_value=1
    )
    def test__get_body_data(
        self, mock_netbox_ref: Mock, mock_secret_ref: Mock, mock_cm_ref: Mock
    ):
        expected = {
            "group": {"id": 1},
            "vid": 10,
            "description": f"test description | {MANAGED_OBJECT_DESCRIPTION}",
            "name": self.k8s_object_name,
            "tags": [1, 2],
        }

        actual = self.netbox_obj_reconciler._get_body_data()

        self.assertDictEqual(expected, actual)

        mock_netbox_ref.assert_called_once()
        mock_cm_ref.assert_called_once()
        mock_secret_ref.assert_called_once()

    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_value_from_ref", return_value=1
    )
    def test__get_lookup_filter(self, mock_ref_values: Mock):
        mock_ref_values.side_effect = [1, 10]

        expected = {"name": self.k8s_object_name, "tag": [1, 2]}

        actual = self.netbox_obj_reconciler._get_lookup_filter()

        self.assertDictEqual(expected, actual)

        mock_ref_values.assert_not_called()

    @patch("pynetbox.core.endpoint.Endpoint.get")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_lookup_filter", return_value=None
    )
    def test__find_existing_object__no_lookup_filter(
        self, mock_lookup_filter: Mock, mock_get: Mock
    ):
        expected = None
        actual = self.netbox_obj_reconciler._find_existing_object()

        self.assertEqual(expected, actual)

        mock_lookup_filter.assert_called_once()
        mock_get.assert_not_called()

    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord({"name": "test"}),
    )
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_lookup_filter",
        return_value={"name": "test"},
    )
    def test__find_existing_object__object_exists(
        self, mock_lookup_filter: Mock, mock_get: Mock
    ):
        actual = self.netbox_obj_reconciler._find_existing_object()

        self.assertEqual(mock_get.return_value, actual)

        mock_lookup_filter.assert_called_once()
        mock_get.assert_called_once()

    def test__get_removed_fields__no_old_spec(self):
        netbox_obj_reconciler = NetBoxObjectReconciler(
            k8s_object_name=self.k8s_object_name,
            spec=self.spec,
        )
        expected = {}
        actual = netbox_obj_reconciler._get_removed_fields()

        self.assertEqual(expected, actual)

    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_value_from_ref",
        return_value="active",
    )
    def test__get_removed_fields(self, mock_value_ref: Mock):
        expected = {"tenant": None, "status": ""}
        actual = self.netbox_obj_reconciler._get_removed_fields()

        self.assertDictEqual(expected, actual)

        mock_value_ref.assert_called_once()

    @patch(
        "app.netboxobject.NetBoxObjectReconciler.create",
        return_value=DummyNetBoxRecord(
            {
                "url": "dummy-url",
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "test"}),
            }
        ),
    )
    @patch("app.netboxobject.NetBoxObjectReconciler.update")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._find_existing_object",
        return_value=None,
    )
    @patch("pynetbox.core.endpoint.Endpoint.get")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_body_data",
        return_value={"name": "test"},
    )
    def test_create_or_update__no_object_status_no_existing(
        self,
        mock_body_data: Mock,
        mock_get: Mock,
        mock_find_existing: Mock,
        mock_update: Mock,
        mock_create: Mock,
    ):
        self.netbox_obj_reconciler.k8s_object_status = None
        actual = self.netbox_obj_reconciler.create_or_update()

        self.assertIsInstance(actual, dict)

        mock_body_data.assert_called_once()
        mock_get.assert_not_called()
        mock_find_existing.assert_called_once()
        mock_update.assert_not_called()
        mock_create.assert_called_once()

    @patch("app.netboxobject.NetBoxObjectReconciler.create")
    @patch("app.netboxobject.NetBoxObjectReconciler.update")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._find_existing_object",
        return_value=None,
    )
    @patch("pynetbox.core.endpoint.Endpoint.get")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_body_data",
        return_value={"name": "test"},
    )
    def test_create_or_update__no_object_status_existing_found_allow_existing(
        self,
        mock_body_data: Mock,
        mock_get: Mock,
        mock_find_existing: Mock,
        mock_update: Mock,
        mock_create: Mock,
    ):
        mock_find_existing.return_value = DummyNetBoxRecord(
            {
                "url": "dummy-url",
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "test"}),
            }
        )
        mock_update.return_value = mock_find_existing.return_value

        self.netbox_obj_reconciler.k8s_object_status = None
        self.netbox_obj_reconciler.netbox_object.allow_existing = True
        actual = self.netbox_obj_reconciler.create_or_update()

        self.assertIsInstance(actual, dict)

        mock_body_data.assert_called_once()
        mock_get.assert_not_called()
        mock_find_existing.assert_called_once()
        mock_update.assert_called_once()
        mock_create.assert_not_called()

    @patch("app.netboxobject.NetBoxObjectReconciler.create")
    @patch("app.netboxobject.NetBoxObjectReconciler.update")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._find_existing_object",
        return_value=None,
    )
    @patch("pynetbox.core.endpoint.Endpoint.get")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_body_data",
        return_value={"name": "test"},
    )
    def test_create_or_update__no_object_status_existing_found_not_allow_existing(
        self,
        mock_body_data: Mock,
        mock_get: Mock,
        mock_find_existing: Mock,
        mock_update: Mock,
        mock_create: Mock,
    ):
        mock_find_existing.return_value = DummyNetBoxRecord(
            {
                "url": "dummy-url",
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "test"}),
            }
        )

        self.netbox_obj_reconciler.k8s_object_status = None
        self.netbox_obj_reconciler.netbox_object.allow_existing = False

        with self.assertRaises(PermanentError):
            self.netbox_obj_reconciler.create_or_update()

        mock_body_data.assert_called_once()
        mock_get.assert_not_called()
        mock_find_existing.assert_called_once()
        mock_update.assert_not_called()
        mock_create.assert_not_called()

    @patch("app.netboxobject.NetBoxObjectReconciler.create")
    @patch("app.netboxobject.NetBoxObjectReconciler.update")
    @patch("app.netboxobject.NetBoxObjectReconciler._find_existing_object")
    @patch("pynetbox.core.endpoint.Endpoint.get")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_body_data",
        return_value={"name": "test"},
    )
    def test_create_or_update__object_status_present(
        self,
        mock_body_data: Mock,
        mock_get: Mock,
        mock_find_existing: Mock,
        mock_update: Mock,
        mock_create: Mock,
    ):
        mock_get.return_value = DummyNetBoxRecord(
            {
                "url": "dummy-url",
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "test"}),
            }
        )
        mock_update.return_value = mock_get.return_value

        actual = self.netbox_obj_reconciler.create_or_update()
        self.assertIsInstance(actual, dict)

        mock_body_data.assert_called_once()
        mock_get.assert_called_once()
        mock_find_existing.assert_not_called()
        mock_update.assert_called_once()
        mock_create.assert_not_called()

    @patch("app.netboxobject.NetBoxObjectReconciler.create")
    @patch("app.netboxobject.NetBoxObjectReconciler.update")
    @patch("app.netboxobject.NetBoxObjectReconciler._find_existing_object")
    @patch("pynetbox.core.endpoint.Endpoint.get", return_value=None)
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_body_data",
        return_value={"name": "test"},
    )
    def test_create_or_update__object_status_present_obj_not_found(
        self,
        mock_body_data: Mock,
        mock_get: Mock,
        mock_find_existing: Mock,
        mock_update: Mock,
        mock_create: Mock,
    ):
        self.netbox_obj_reconciler.netbox_object.allow_existing = True
        mock_find_existing.return_value = DummyNetBoxRecord(
            {
                "url": "dummy-url",
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "test"}),
            }
        )
        mock_update.return_value = mock_find_existing.return_value

        actual = self.netbox_obj_reconciler.create_or_update()
        self.assertIsInstance(actual, dict)

        mock_body_data.assert_called_once()
        mock_get.assert_called_once()
        mock_find_existing.assert_called_once()
        mock_update.assert_called_once()
        mock_create.assert_not_called()

    @patch("pynetbox.core.endpoint.Endpoint.get")
    def test__allocate_available_object__no_parent_obj_id(self, mock_get: Mock):
        self.netbox_obj_reconciler.endpoint.name = "ip-addresses"

        with self.assertRaises(ValueError):
            self.netbox_obj_reconciler._allocate_available_object({})

        mock_get.assert_not_called()

    @patch("pynetbox.core.endpoint.Endpoint.get", return_value=None)
    def test__allocate_available_object__parent_not_found(self, mock_get: Mock):
        with self.assertRaises(ValueError):
            self.netbox_obj_reconciler._allocate_available_object({"id": 1})

        mock_get.assert_called_once()

    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord(
            {"endpoint": DummyNetBoxRecord({"name": "dcim"})}
        ),
    )
    def test__allocate_available_object__unsupported_endpoint(self, mock_get: Mock):
        with self.assertRaises(PermanentError) as ctx:
            self.netbox_obj_reconciler._allocate_available_object({"id": 1})
            self.assertIn("Unsupported endpoint", str(ctx.exception))

        mock_get.assert_called_once()

    @patch("app.netboxobject.AvailableGlobalVlan.create")
    @patch(
        "pynetbox.core.endpoint.DetailEndpoint.create", return_value=DummyNetBoxRecord()
    )
    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord(
            {
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "prefixes", "url": "dummy-url"}),
                "api": DummyNetBoxRecord({"token": "token", "http_session": ""}),
            }
        ),
    )
    def test__allocate_available_object__available_prefix(
        self, mock_get: Mock, mock_detail_endpoint: Mock, mock_global_vlan: Mock
    ):
        actual = self.netbox_obj_reconciler._allocate_available_object(
            {"id": 1, "prefix_length": 24}
        )

        self.assertIsInstance(actual, DummyNetBoxRecord)

        mock_get.assert_called_once()
        mock_detail_endpoint.assert_called_once()
        mock_global_vlan.assert_not_called()

    @patch(
        "app.netboxobject.AvailableGlobalVlan.create", return_value=DummyNetBoxRecord()
    )
    @patch("pynetbox.core.endpoint.DetailEndpoint.create")
    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord(
            {
                "id": 1,
                "endpoint": DummyNetBoxRecord({"name": "vlans", "url": "dummy-url"}),
                "api": DummyNetBoxRecord({"token": "token", "http_session": ""}),
            }
        ),
    )
    def test__allocate_available_object__available_global_vlan(
        self, mock_get: Mock, mock_detail_endpoint: Mock, mock_global_vlan: Mock
    ):
        actual = self.netbox_obj_reconciler._allocate_available_object({"id": 1})

        self.assertIsInstance(actual, DummyNetBoxRecord)

        mock_get.assert_called_once()
        mock_detail_endpoint.assert_not_called()
        mock_global_vlan.assert_called_once()

    @patch("pynetbox.core.endpoint.Endpoint.create")
    @patch(
        "app.netboxobject.NetBoxObjectReconciler._allocate_available_object",
        return_value=DummyNetBoxRecord(),
    )
    def test_create__allocate_available(
        self, mock_allocate_available: Mock, mock_create: Mock
    ):
        self.netbox_obj_reconciler.netbox_object.allocate_available = True

        payload = {"name": "test"}
        self.netbox_obj_reconciler.create(payload)

        mock_allocate_available.assert_called_once_with(payload)
        mock_create.assert_not_called()

    @patch("pynetbox.core.endpoint.Endpoint.create", return_value=DummyNetBoxRecord())
    @patch("app.netboxobject.NetBoxObjectReconciler._allocate_available_object")
    def test_create(self, mock_allocate_available: Mock, mock_create: Mock):
        self.netbox_obj_reconciler.netbox_object.allocate_available = False

        payload = {"name": "test"}
        actual = self.netbox_obj_reconciler.create(payload)

        self.assertIsInstance(actual, DummyNetBoxRecord)

        mock_allocate_available.assert_not_called()
        mock_create.assert_called_once_with(**payload)

    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_removed_fields",
    )
    def test_update__removed_fields(self, mock_removed_fields: Mock):
        removed_fields = {"tenant": {}}
        mock_removed_fields.return_value = removed_fields

        dummy_record = DummyNetBoxRecord(
            {
                "id": 1,
                "name": "test",
                "endpoint": DummyNetBoxRecord({"url": "dummy-url"}),
            }
        )
        data = {"tags": [1, 2]}

        expected = dummy_record.copy()
        expected.update(data)
        expected.update(removed_fields)

        self.netbox_obj_reconciler.netbox_object.allocate_available = False
        actual = self.netbox_obj_reconciler.update(dummy_record, data)

        self.assertEqual(expected, actual)

        mock_removed_fields.assert_called_once()

    @patch(
        "app.netboxobject.NetBoxObjectReconciler._get_removed_fields",
    )
    def test_update__allocate_available(self, mock_removed_fields: Mock):
        mock_removed_fields.return_value = {}
        dummy_record = DummyNetBoxRecord(
            {
                "id": 1,
                "name": "test",
                "endpoint": DummyNetBoxRecord({"url": "dummy-url"}),
            }
        )
        data = {"tags": [1, 2], "id": 2}

        expected = dummy_record.copy()
        expected_data = data.copy()
        expected_data.pop("id")
        expected.update(expected_data)

        self.netbox_obj_reconciler.netbox_object.allocate_available = True
        actual = self.netbox_obj_reconciler.update(dummy_record, data)

        self.assertEqual(expected, actual)

        mock_removed_fields.assert_called_once()

    def test_delete__no_object_status(self):
        self.netbox_obj_reconciler.k8s_object_status = None

        with self.assertRaises(PermanentError):
            self.netbox_obj_reconciler.delete()

    @patch("pynetbox.core.endpoint.Endpoint.get", return_value=None)
    def test_delete__obj_not_found(self, mock_get: Mock):
        actual = self.netbox_obj_reconciler.delete()
        self.assertFalse(actual)

        mock_get.assert_called_once()

    @patch("pynetbox.core.endpoint.Endpoint.get")
    def test_delete__conflict(self, mock_get: Mock):
        DummyNetBoxRecord.raise_conflict_on_delete = True
        record = DummyNetBoxRecord(
            {
                "id": 1,
                "name": "test",
                "endpoint": DummyNetBoxRecord({"url": "dummy-url"}),
                "url": "dummy-url",
            }
        )

        mock_get.return_value = record

        with self.assertRaises(NetBoxConflict):
            self.netbox_obj_reconciler.delete()

        mock_get.assert_called_once()

        DummyNetBoxRecord.raise_conflict_on_delete = False

    @patch("pynetbox.core.endpoint.Endpoint.get")
    def test_delete__success(self, mock_get: Mock):
        record = DummyNetBoxRecord(
            {
                "id": 1,
                "name": "test",
                "endpoint": DummyNetBoxRecord({"url": "dummy-url"}),
                "url": "dummy-url",
            }
        )

        mock_get.return_value = record

        actual = self.netbox_obj_reconciler.delete()
        self.assertTrue(actual)

        mock_get.assert_called_once()
