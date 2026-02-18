import base64
import unittest
import kr8s
from unittest.mock import Mock, patch
from app.kubernetes import get_secret_value, get_config_map_value, settings


class TestKubernetes(unittest.TestCase):

    def setUp(self):
        secret_patcher = patch("app.kubernetes.kr8s.objects.Secret")
        configmap_patcher = patch("app.kubernetes.kr8s.objects.ConfigMap")
        self.addCleanup(secret_patcher.stop)
        self.addCleanup(configmap_patcher.stop)

        self.mock_secret_cls = secret_patcher.start()
        self.mock_cm_cls = configmap_patcher.start()

    def _make_secret(self, data: dict) -> Mock:
        secret = Mock()
        secret.data = data
        return secret

    def _make_configmap(self, data: dict) -> Mock:
        configmap = Mock()
        configmap.data = data
        return configmap

    # -------------------------
    # get_secret_value
    # -------------------------

    def test_get_secret_value_success(self):
        secret_value = "admin"
        secret_b64 = base64.b64encode(secret_value.encode()).decode()

        self.mock_secret_cls.get.return_value = self._make_secret(
            {"username": secret_b64}
        )

        result = get_secret_value("mysecret", "username")

        self.assertEqual(result, secret_value)
        self.mock_secret_cls.get.assert_called_once_with(
            name="mysecret",
            namespace=settings.namespace
        )

    def test_get_secret_value_not_found(self):
        self.mock_secret_cls.get.side_effect = kr8s.NotFoundError("mysecret")

        with self.assertRaises(kr8s.NotFoundError):
            get_secret_value("mysecret", "username")

    def test_get_secret_value_key_missing(self):
        self.mock_secret_cls.get.return_value = self._make_secret({})

        with self.assertRaises(KeyError):
            get_secret_value("mysecret", "missing_key")

    def test_get_secret_value_invalid_base64(self):
        self.mock_secret_cls.get.return_value = self._make_secret(
            {"password": "not_valid_base64!!!"}
        )

        with self.assertRaises(Exception):
            get_secret_value("mysecret", "password")

    # -------------------------
    # get_config_map_value
    # -------------------------

    def test_get_config_map_value_success(self):
        self.mock_cm_cls.get.return_value = self._make_configmap(
            {"username": "admin"}
        )

        result = get_config_map_value("myconfig", "username")

        self.assertEqual(result, "admin")
        self.mock_cm_cls.get.assert_called_once_with(
            name="myconfig",
            namespace=settings.namespace
        )

    def test_get_config_map_value_not_found(self):
        self.mock_cm_cls.get.side_effect = kr8s.NotFoundError("myconfig")

        with self.assertRaises(kr8s.NotFoundError):
            get_config_map_value("myconfig", "username")

    def test_get_config_map_value_key_missing(self):
        self.mock_cm_cls.get.return_value = self._make_configmap({})

        with self.assertRaises(KeyError):
            get_config_map_value("myconfig", "missing_key")
