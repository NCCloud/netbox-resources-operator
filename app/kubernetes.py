import os
import base64
import pykube
from .config import Settings

settings = Settings()

if os.environ.get("NETBOX_APP_ENV") == "test":
    os.environ["KUBECONFIG"] = f"{os.getcwd()}/tests/dummy_kubeconfig.yaml"

k8s_api = pykube.HTTPClient(pykube.KubeConfig.from_env())


def get_secret_value(name: str, key: str):
    """
    Get the value of the key from a secret
    :name: the name of the secret
    :key: the key in the secret data
    """
    secret = pykube.Secret.objects(k8s_api, namespace=settings.namespace).get_or_none(
        name=name
    )
    if not secret:
        raise pykube.exceptions.ObjectDoesNotExist(f'Secret "{name}" does not exist')

    secret_data_b64 = secret.obj["data"].get(key)
    if secret_data_b64 is None:
        raise KeyError(f'Secret "{name}" does not have key "{key}"')

    secret_data = base64.b64decode(secret_data_b64).decode("utf-8")
    return secret_data


def get_config_map_value(name: str, key: str):
    """
    Get the value of the key from a config map
    :name: the name of the config map
    :key: the key in the config map data
    """
    config_map = pykube.ConfigMap.objects(
        k8s_api, namespace=settings.namespace
    ).get_or_none(name=name)
    if not config_map:
        raise pykube.exceptions.ObjectDoesNotExist(f'ConfigMap "{name}" does not exist')

    config_map_data = config_map.obj["data"].get(key)
    if config_map_data is None:
        raise KeyError(f'ConfigMap "{name}" does not have key "{key}"')

    return config_map_data
