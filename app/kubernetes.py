import os
import base64
import kr8s
from .config import Settings

settings = Settings()

if os.environ.get("NETBOX_APP_ENV") == "test":
    os.environ["KUBECONFIG"] = f"{os.getcwd()}/tests/unit/dummy_kubeconfig.yaml"


def get_secret_value(name: str, key: str) -> str:
    """
    Get the value of the key from a secret
    :name: the name of the secret
    :key: the key in the secret data
    """
    secret = kr8s.objects.Secret.get(name=name, namespace=settings.namespace)

    secret_data_b64 = secret.data.get(key)
    if secret_data_b64 is None:
        raise KeyError(f'Secret "{name}" does not have key "{key}"')

    return base64.b64decode(secret_data_b64).decode("utf-8")


def get_config_map_value(name: str, key: str) -> str:
    """
    Get the value of the key from a config map
    :name: the name of the config map
    :key: the key in the config map data
    """
    config_map = kr8s.objects.ConfigMap.get(
        name=name, namespace=settings.namespace)

    config_map_data = config_map.data.get(key)
    if config_map_data is None:
        raise KeyError(f'ConfigMap "{name}" does not have key "{key}"')

    return config_map_data
