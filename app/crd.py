"""
Generate Kubernetes CRDs for the operator
The use of apischema is greatly inspired by https://github.com/maxking/kubecrd
"""

import os
import json
import yaml
from apischema.json_schema import deserialization_schema
from app.models import NetBoxObjectSchema

CRD_GROUP = "spaceship.com"
NETBOX_OBJECT_CRD_NAME = "NetBoxObject"
NETBOX_OBJECT_CRD_NAME_LOWER = NETBOX_OBJECT_CRD_NAME.lower()
NETBOX_OBJECT_CRD_NAME_PLURAL = f"{NETBOX_OBJECT_CRD_NAME_LOWER}s"
NETBOX_OBJECT_CRD_NAME_FULL = f"{NETBOX_OBJECT_CRD_NAME_PLURAL}.{CRD_GROUP}"


def generate_crd():
    crd_schema = json.loads(
        json.dumps(
            deserialization_schema(
                NetBoxObjectSchema,
                all_refs=False,
                additional_properties=True,
                with_schema=False,
            )
        )
    )

    crd = {
        "apiVersion": "apiextensions.k8s.io/v1",
        "kind": "CustomResourceDefinition",
        "metadata": {"name": NETBOX_OBJECT_CRD_NAME_FULL},
        "spec": {
            "scope": "Cluster",
            "group": CRD_GROUP,
            "names": {
                "kind": NETBOX_OBJECT_CRD_NAME,
                "plural": NETBOX_OBJECT_CRD_NAME_PLURAL,
                "singular": NETBOX_OBJECT_CRD_NAME_LOWER,
                "shortNames": ["nbo"],
            },
            "versions": [
                {
                    "name": "v1alpha1",
                    "served": True,
                    "storage": True,
                    "schema": {"openAPIV3Schema": crd_schema},
                    "subresources": {"status": {}},
                    "additionalPrinterColumns": [
                        {
                            "name": "Data Model",
                            "type": "string",
                            "jsonPath": ".status.netboxobject.dataModel",
                        },
                        {
                            "name": "Endpoint",
                            "type": "string",
                            "jsonPath": ".status.netboxobject.endpoint",
                        },
                        {
                            "name": "Resource ID",
                            "type": "integer",
                            "description": "The NetBox resource ID",
                            "jsonPath": ".status.netboxobject.id",
                        },
                        {
                            "name": "Resource URL",
                            "type": "string",
                            "description": "The URL to the created NetBox resource",
                            "jsonPath": ".status.netboxobject.url",
                        },
                        {
                            "name": "Phase",
                            "type": "string",
                            "description": "The phase of the resource deployment",
                            "jsonPath": ".status.phase",
                        },
                    ],
                }
            ],
        },
    }

    return crd


def crd_to_yaml():
    crd = generate_crd()
    crd_name = crd["metadata"]["name"]

    os.makedirs("crds", exist_ok=True)

    with open(f"crds/{crd_name}.yaml", "w", encoding="utf-8") as destination:
        yaml.dump(crd, destination, sort_keys=False)
