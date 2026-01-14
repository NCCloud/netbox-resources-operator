import base64
import unittest
from unittest.mock import Mock, patch
import pykube
from app.kubernetes import get_secret_value, get_config_map_value, k8s_api, settings


class TestKubernetes(unittest.TestCase):
    def setUp(self):
        secret_patcher = patch("app.kubernetes.pykube.Secret")
        configmap_patcher = patch("app.kubernetes.pykube.ConfigMap")
        self.addCleanup(secret_patcher.stop)
        self.addCleanup(configmap_patcher.stop)

        self.mock_secret_cls = secret_patcher.start()
        self.mock_secret_manager = Mock()
        self.mock_secret_cls.objects.return_value = self.mock_secret_manager

        self.mock_cm_cls = configmap_patcher.start()
        self.mock_configmap_manager = Mock()
        self.mock_cm_cls.objects.return_value = self.mock_configmap_manager

    def test_get_secret_value_success(self):
        secret_value = "admin"
        secret_b64 = base64.b64encode(secret_value.encode("utf-8")).decode("utf-8")

        secret_obj = Mock()
        secret_obj.obj = {"data": {"username": secret_b64}}
        self.mock_secret_manager.get_or_none.return_value = secret_obj

        result = get_secret_value("mysecret", "username")
        self.assertEqual(result, secret_value)

        self.mock_secret_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_secret_value_secret_not_found(self):
        self.mock_secret_manager.get_or_none.return_value = None

        with self.assertRaises(pykube.exceptions.ObjectDoesNotExist):
            get_secret_value("mysecret", "username")

        self.mock_secret_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_secret_value_key_missing(self):
        secret_obj = Mock()
        secret_obj.obj = {"data": {}}
        self.mock_secret_manager.get_or_none.return_value = secret_obj

        with self.assertRaises(KeyError):
            get_secret_value("mysecret", "missing_key")

        self.mock_secret_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_secret_value_invalid_base64(self):
        secret_obj = Mock()
        secret_obj.obj = {"data": {"password": "not_base64"}}
        self.mock_secret_manager.get_or_none.return_value = secret_obj

        with self.assertRaises(Exception):
            get_secret_value("mysecret", "username")

        self.mock_secret_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_config_map_value_success(self):
        config_obj = Mock()
        config_obj.obj = {"data": {"username": "admin"}}
        self.mock_configmap_manager.get_or_none.return_value = config_obj

        result = get_config_map_value("myconfig", "username")
        self.assertEqual(result, "admin")

        self.mock_cm_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_config_map_value_not_found(self):
        self.mock_configmap_manager.get_or_none.return_value = None

        with self.assertRaises(pykube.exceptions.ObjectDoesNotExist):
            get_config_map_value("myconfig", "username")

        self.mock_cm_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )

    def test_get_config_map_value_key_missing(self):
        config_obj = Mock()
        config_obj.obj = {"data": {}}
        self.mock_configmap_manager.get_or_none.return_value = config_obj

        with self.assertRaises(KeyError):
            get_config_map_value("myconfig", "missing_key")

        self.mock_cm_cls.objects.assert_called_with(
            k8s_api, namespace=settings.namespace
        )
