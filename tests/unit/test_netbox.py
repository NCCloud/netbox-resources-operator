import unittest
from unittest.mock import patch, Mock
from tests.unit.util import DummyNetBoxRecord
from app.netbox import get_or_create_netbox_tag, AvailableGlobalVlan, ExhaustedVlan


class TestNetBox(unittest.TestCase):
    @patch("pynetbox.core.endpoint.Endpoint.create", return_value=None)
    @patch(
        "pynetbox.core.endpoint.Endpoint.get",
        return_value=DummyNetBoxRecord({"id": 0, "name": "tag"}),
    )
    def test_get_or_create_netbox_tag_existing(self, mock_get: Mock, mock_create: Mock):
        actual = get_or_create_netbox_tag(name="tag")

        self.assertEqual(mock_get.return_value, actual)
        mock_get.assert_called_once_with(name="tag")
        mock_create.assert_not_called()

    @patch(
        "pynetbox.core.endpoint.Endpoint.create",
        return_value=DummyNetBoxRecord({"id": 0, "name": "tag"}),
    )
    @patch("pynetbox.core.endpoint.Endpoint.get", return_value=None)
    def test_get_or_create_netbox_tag_new(self, mock_get: Mock, mock_create: Mock):
        actual = get_or_create_netbox_tag(name="tag")

        self.assertEqual(mock_create.return_value, actual)
        mock_get.assert_called_once_with(name="tag")
        mock_create.assert_called_once()


class TestNetBoxAvailableGlobalVlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.available_global_vlan = AvailableGlobalVlan()

    @classmethod
    def tearDownClass(cls):
        del cls.available_global_vlan

    @patch(
        "pynetbox.core.endpoint.Endpoint.all",
        return_value=[
            DummyNetBoxRecord({"vid": 1}),
            DummyNetBoxRecord({"vid": 2}),
            DummyNetBoxRecord({"vid": 5}),
        ],
    )
    def test_list(self, mock_list_vlans: Mock):
        used_vlans = [1, 2, 5]
        expected = [i for i in range(1, 4097) if i not in used_vlans]

        actual = self.available_global_vlan.list()

        self.assertEqual(expected, actual)
        mock_list_vlans.assert_called_once()

    @patch(
        "pynetbox.core.endpoint.Endpoint.create",
        return_value=DummyNetBoxRecord({"id": 2}),
    )
    @patch(
        "pynetbox.core.endpoint.Endpoint.all",
        return_value=[DummyNetBoxRecord({"vid": 1})],
    )
    def test_create_success(self, mock_list_vlans: Mock, mock_create_vlan: Mock):
        actual = self.available_global_vlan.create({})

        self.assertEqual(mock_create_vlan.return_value, actual)
        mock_list_vlans.assert_called_once()
        mock_create_vlan.assert_called_once_with(vid=2)

    @patch(
        "pynetbox.core.endpoint.Endpoint.all",
    )
    def test_create_exhausted_vlans(self, mock_list_vlans: Mock):
        mock_list_vlans.return_value = [
            DummyNetBoxRecord({"vid": i}) for i in range(1, 4097)
        ]

        with self.assertRaises(ExhaustedVlan):
            self.available_global_vlan.create({})

        mock_list_vlans.assert_called_once()
