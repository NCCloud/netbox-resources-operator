from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
from apischema import schema, alias, validator, ValidationError


class NetBoxDataModelsEnum(str, Enum):
    circuits = "circuits"
    core = "core"
    dcim = "dcim"
    extras = "extras"
    ipam = "ipam"
    tenancy = "tenancy"
    users = "users"
    virtualization = "virtualization"
    vpn = "vpn"
    wireless = "wireless"


class NetBoxObjectStatusPhaseEnum(str, Enum):
    FAILED = "Failed"
    PROVISIONED = "Provisioned"
    PROGRESSING = "Progressing"


class StatusConditionTypeEnum(str, Enum):
    FAILED = "Failed"
    RECONCILING = "Reconciling"
    READY = "Ready"


class StatusConditionReasonEnum(str, Enum):
    COMPLETED = "Completed"
    ERROR = "Error"
    RECONCILED = "Reconciled"
    RECONCILING = "Reconciling"
    SPEC_CHANGED = "SpecChanged"


@dataclass
class StatusCondition:
    type: StatusConditionTypeEnum
    status: str
    reason: StatusConditionReasonEnum
    message: str
    last_transition_time: datetime = field(
        default_factory=datetime.now,
        metadata=alias("lastTransitionTime")
        | schema(
            description="The last time the condition transitioned from one status to another"
        ),
    )


@dataclass
class ValueKeyRef:
    key: str = field(metadata=schema(description="The key in the object data"))
    name: str = field(metadata=schema(description="The name of the object"))


# separate classes for Secret and ConfigMap reference
# to avoid apischema using $defs and $refs in the CRD spec due to re-used types
# https://wyfo.github.io/apischema/0.19/json_schema/#use-reference-only-for-reused-types
@dataclass
class SecretValueKeyRef(ValueKeyRef):
    pass


@dataclass
class ConfigMapValueKeyRef(ValueKeyRef):
    pass


@dataclass
class NetBoxObjectValueFrom:
    secret_key_ref: SecretValueKeyRef = field(
        default=None,
        metadata=alias("secretKeyRef")
        | schema(description="Selects a key of a Secret in the pod's namespace"),
    )
    config_map_key_ref: ConfigMapValueKeyRef = field(
        default=None,
        metadata=alias("configMapKeyRef")
        | schema(description="Selects a key of a ConfigMap in the pod's namespace"),
    )
    netbox_obj_ref: "NetBoxObjectValueResolution" = field(
        default=None,
        metadata=alias("netboxObjRef")
        | schema(
            description="Resolves a value for the path from NetBox",
            extra={"x-kubernetes-preserve-unknown-fields": True},
        ),
    )

    # since apischema doesn't run validators when all fields have a default value
    # use post init to implement this logic
    # https://wyfo.github.io/apischema/0.17/validation/#validators-are-not-run-on-default-values
    def __post_init__(self):
        value_options = [
            self.secret_key_ref,
            self.config_map_key_ref,
            self.netbox_obj_ref,
        ]
        if all(v is None for v in value_options):
            raise ValidationError(
                "Either secretKeyRef or configMapKeyRef or netboxObjRef must be set"
            )

    @validator("netbox_obj_ref")
    def value_is_set(self):
        """
        Validate that one value is set
        """
        value_options = [
            self.secret_key_ref,
            self.config_map_key_ref,
            self.netbox_obj_ref,
        ]

        provided_values_num = len([v for v in value_options if v is not None])
        expected_values_num = 1

        if provided_values_num > expected_values_num:
            raise ValidationError("Only one value reference should be provided")

        return self


@dataclass(frozen=True)
class NetBoxObjectValueResolution:
    data_model: NetBoxDataModelsEnum = field(
        metadata=alias("dataModel")
        | schema(
            description=(
                "NetBox data model type. Available choices: "
                f"{[d_model.value for d_model in NetBoxDataModelsEnum]}"
            )
        )
    )
    endpoint: str = field(
        metadata=schema(
            description=(
                "NetBox endpoint for the data model according to API, "
                "e.g., in URL /api/ipam/vlans, vlans is the endpoint"
            )
        )
    )
    filter: str = field(
        metadata=schema(
            description="NetBox comma-separated resource filter: https://netboxlabs.com/docs/netbox/reference/filtering/"
        )
    )
    path: str = field(
        metadata=schema(
            description="The dot-separated path to the field in the retrieved object, e.g., group.id"
        )
    )


@dataclass
class NetBoxObjectBodyItem:
    path: str = field(
        metadata=schema(
            description="The dot-separated path to the field in the NetBox object to manage, e.g., group.id"
        )
    )
    value: Any = field(
        default=None,
        metadata=schema(
            description="The raw value to put into path",
            extra={"x-kubernetes-preserve-unknown-fields": True},
        ),
    )
    value_from: NetBoxObjectValueFrom = field(
        default=None,
        metadata=alias("valueFrom")
        | schema(description="Get a value from a Secret or ConfigMap"),
    )
    lookup_key: bool = field(
        default=False,
        metadata=alias("lookupKey")
        | schema(
            description="Whether to use this field to find existing objects in NetBox"
        ),
    )
    lookup_alias: str = field(
        default="",
        metadata=alias("lookupAlias")
        | schema(
            description=(
                "The alias specifies the name to use for lookup "
                "because NetBox may have different keys for creating and getting objects, "
                "e.g. tags for creation and tag for filtering"
            )
        ),
    )

    # since apischema doesn't run validators when all fields have a default value
    # use post init to implement this logic
    # https://wyfo.github.io/apischema/0.17/validation/#validators-are-not-run-on-default-values
    def __post_init__(self):
        value_options = [self.value, self.value_from]
        if all(v is None for v in value_options):
            raise ValidationError("Either value or valueFrom must be set")

    @validator()
    def value_is_set(self):
        """
        Validate that at least one value is set
        """
        value_options = [self.value, self.value_from]

        provided_values_num = len([v for v in value_options if v is not None])
        expected_values_num = 1

        if provided_values_num > expected_values_num:
            raise ValidationError("Only one of value or valueFrom must be provided")
        return self


@dataclass
class NetBoxObject:
    data_model: NetBoxDataModelsEnum = field(
        metadata=alias("dataModel")
        | schema(
            description=(
                "NetBox data model type. Available choices: "
                f"{[d_model.value for d_model in NetBoxDataModelsEnum]}"
            )
        )
    )
    endpoint: str = field(
        metadata=schema(
            description=(
                "NetBox endpoint for the data model according to API, "
                "e.g., in URL /api/ipam/vlans, vlans is the endpoint"
            )
        )
    )
    body: list[NetBoxObjectBodyItem]
    allow_existing: bool = field(
        default=False,
        metadata=alias("allowExisting")
        | schema(
            description="Whether to allow the management of existing NetBox resources during creation"
        ),
    )
    preserve_on_delete: bool = field(
        default=False,
        metadata=alias("preserveOnDelete")
        | schema(
            description="Whether not to delete the resource from NetBox upon manifest deletion"
        ),
    )
    allocate_available: bool = field(
        default=False,
        metadata=alias("allocateAvailable")
        | schema(
            description=(
                "Whether to allocate the next available item for the given endpoint.\n"
                "This setting only works with the following endpoints: "
                "vlans, vlan-groups, prefixes, ip-ranges.\n"
                "If 'prefixes' is used as endpoint, prefix_length must be provided to create a new prefix. "
                "Otherwise, the next available IP will be created.\n"
                "For every endpoint other than 'vlans', you must provide the 'id' path to the parent object\n"
                "While NetBox doesn't natively support allocating new VLANs for the 'vlans' endpoint, "
                "the operator will provision the next available VLAN globally, "
                "i.e. an available VLAN within the range of 1-4096 that doesn't exist either in a group or outside of it"
            )
        ),
    )

    @validator
    def can_allocate_available_resource(self):
        """
        If allocate_available is True, check that all the required data is present
        """
        if not self.allocate_available:
            return

        supported_endpoints = ["vlans", "vlan_groups", "prefixes", "ip_ranges"]
        endpoint = self.endpoint.replace("-", "_")
        if endpoint not in supported_endpoints:
            raise ValidationError(
                f"Endpoint must be one of these: {supported_endpoints}"
            )

        has_id_path = False
        for item in self.body:
            if item.path == "id":
                has_id_path = True
                break

        if not has_id_path and endpoint != "vlans":
            raise ValidationError(
                "body must contain the 'id' path to find the existing parent resource"
            )


@dataclass
class NetBoxObjectStatusFields:
    id: int = field(metadata=schema(description="The ID of the NetBox object"))
    url: str = field(metadata=schema(description="The URL of the NetBox object"))
    endpoint: str = field(
        metadata=schema(description="The endpoint of the NetBox object")
    )
    data_model: str = field(
        metadata=alias("dataModel")
        | schema(description="The data model of the NetBox object")
    )


@dataclass
class NetBoxObjectStatus:
    netboxobject: NetBoxObjectStatusFields = field(
        default_factory=dict, metadata=schema(description="The NetBox object data")
    )
    phase: NetBoxObjectStatusPhaseEnum = field(
        default=None,
        metadata=schema(
            description="The current phase of the NetBox object provisioning"
        ),
    )
    conditions: list[StatusCondition] = field(
        default_factory=list,
        metadata=schema(description="The conditions of the object"),
    )
    observed_generation: int = field(
        default=None,
        metadata=schema(
            description="represents the .metadata.generation that the condition was set based upon"
        ),
    )


@dataclass
class NetBoxObjectSchema:
    spec: NetBoxObject
    status: Optional[None] = field(
        default=None,
        metadata=schema(
            extra={"x-kubernetes-preserve-unknown-fields": True, "type": "object"}
        ),
    )
