import logging
from functools import lru_cache
from typing import Any

from apischema import ValidationError, deserialize
from glom import PathAccessError, assign, glom
from kopf import PermanentError
from pynetbox.core.app import App
from pynetbox.core.endpoint import DetailEndpoint, Endpoint
from pynetbox.core.query import RequestError
from pynetbox.core.response import Record
from pynetbox.models.ipam import IpAddresses, Prefixes, Vlans

from .errors import NetBoxConflict, NetBoxObjectNotFound
from .kubernetes import get_config_map_value, get_secret_value
from .models import (
    NetBoxObject,
    NetBoxObjectBodyItem,
    NetBoxObjectStatusFields,
    NetBoxObjectValueFrom,
    NetBoxObjectValueResolution,
)
from .netbox import AvailableGlobalVlan, get_or_create_netbox_tag, nb
from .util import netbox_value_to_default, parse_filter_string

logger = logging.getLogger("kopf.objects")

MANAGED_OBJECT_DESCRIPTION = "Managed by netbox-resources-operator"


class NetBoxObjectStatusHandler:
    def __init__(self, status: dict):
        self.netboxobject: NetBoxObjectStatusFields = deserialize(
            NetBoxObjectStatusFields, status, additional_properties=True
        )

    @property
    def netboxobject_endpoint(self):
        """
        Get object endpoint from Kubernetes resource status
        This is useful for managing existing objects
        as they may have a different endpoint from what is specified in the CR,
        for example, when we allocated the next available IP/vlan/etc.
        """
        app = App(nb, self.netboxobject.data_model)
        endpoint = Endpoint(nb, app, self.netboxobject.endpoint)
        return endpoint

    @property
    def netboxobject_id(self):
        """
        The ID of the managed NetBox object
        """
        return self.netboxobject.id


class NetBoxObjectReconciler:
    def __init__(
        self,
        k8s_object_name: str,
        spec: dict,
        old_spec: dict = None,
        k8s_object_status: dict = None,
    ):
        self.k8s_object_name = k8s_object_name
        self.spec = spec
        self.old_spec = old_spec
        self.k8s_object_status = self._get_object_status_model(k8s_object_status)

        self.netbox_object = self._netbox_object_from_spec(self.spec)
        self.endpoint = self._get_object_endpoint(
            data_model=self.netbox_object.data_model.value,
            endpoint=self.netbox_object.endpoint,
        )

    def _get_object_status_model(self, status: dict):
        """
        Deserialize the netboxobject part of the k8s object status
        """
        if not status or "netboxobject" not in status:
            return None

        status_model = None
        try:
            status_model = NetBoxObjectStatusHandler(status["netboxobject"])
        except ValidationError as e:
            logger.debug(
                "[%s] Cannot parse status data: %s, error=%s",
                self.k8s_object_name,
                status,
                e.errors,
            )

        return status_model

    def _netbox_object_from_spec(self, spec: dict):
        return deserialize(NetBoxObject, spec)

    def _get_object_endpoint(self, data_model: str, endpoint: str) -> Endpoint:
        app = App(nb, data_model)
        endpoint = Endpoint(nb, app, endpoint)
        return endpoint

    def _get_object_filter(self, filter_str: str) -> dict:
        """
        Convert a string like `name__ic=target,tag=hello` to a dictionary
        """
        netbox_obj_filter = parse_filter_string(filter_str)

        logger.debug(
            "[%s] Constructed NetBox object filter: %s",
            self.k8s_object_name,
            netbox_obj_filter,
        )

        return netbox_obj_filter

    @lru_cache(maxsize=128)
    def _resolve_netbox_value(self, netbox_resolve: NetBoxObjectValueResolution):
        """
        Given NetBoxObjectValueResolution, find the object in NetBox and
        return the value according to the path
        """
        endpoint = self._get_object_endpoint(
            data_model=netbox_resolve.data_model.value, endpoint=netbox_resolve.endpoint
        )
        filter_set = self._get_object_filter(netbox_resolve.filter)

        netbox_object = endpoint.get(**filter_set)
        # maybe the object is dependent on the existence of another object
        # that we manage but haven't created yet, let's try again in a couple of seconds
        if not netbox_object:
            raise NetBoxObjectNotFound(
                (
                    f"Could not find NetBox object with filter {netbox_resolve.filter} "
                    f"at endpoint {netbox_resolve.data_model.value}/{netbox_resolve.endpoint}, "
                    f"k8s_object_name={self.k8s_object_name}"
                ),
            )

        try:
            value = glom(dict(netbox_object), netbox_resolve.path)
        except PathAccessError as e:
            raise ValueError(
                f"Failed to get data at path {netbox_resolve.path} "
                f"from NetBox object: {dict(netbox_object)} ",
                f"k8s_object_name={self.k8s_object_name}",
            ) from e

        return value

    def _convert_tag_names_to_ids(self, tags: list[str]) -> list[int]:
        """
        Convert a list of NetBox tag strings to a list of their IDs
        Missing tags will be created
        """
        tag_ids = []
        for tag in tags:
            netbox_tag = get_or_create_netbox_tag(tag)
            tag_ids.append(netbox_tag.id)

        return tag_ids

    def _get_netbox_compatible_value(self, path: str, value: Any):
        """
        Based on the given path and value, make the final value compatible with NetBox
        For example, auto-convert tag names to IDs
        :return list[int]: a list of NetBox tag IDs
        """
        compatible_value = value

        # the path is "tags" and the value is a list of strings
        # if the value is a list of numbers, this may indicate
        # that the user manually provided tag IDs and we shouldn't resolve them
        if (
            path == "tags"
            and isinstance(value, list)
            and all(isinstance(t, str) for t in value)
        ):
            compatible_value = self._convert_tag_names_to_ids(value)

        return compatible_value

    def _get_value_from_ref(self, value_from: NetBoxObjectValueFrom):
        """
        Given the valueFrom section of the CRD, find the final value
        """
        if value_from.config_map_key_ref:
            return get_config_map_value(
                name=value_from.config_map_key_ref.name,
                key=value_from.config_map_key_ref.key,
            )

        if value_from.secret_key_ref:
            return get_secret_value(
                name=value_from.secret_key_ref.name, key=value_from.secret_key_ref.key
            )

        if value_from.netbox_obj_ref:
            return self._resolve_netbox_value(value_from.netbox_obj_ref)

        raise PermanentError(
            "Cannot resolve valueFrom because no supported reference is provided"
        )

    def _resolve_nested_values(self, value: Any) -> Any:
        """
        Recursively resolve any embedded valueFrom references inside a
        list/dict value. This allows building NetBox fields that are arrays of
        objects (e.g. cable a_terminations/b_terminations) from NetBox lookups,
        which a single dot-separated path cannot express:

            - object_type: dcim.interface
              object_id:
                valueFrom:
                  netboxObjRef: {...}

        A dict containing the "valueFrom" key is treated as a reference marker
        and replaced with its resolved value; everything else is walked
        recursively and returned unchanged.
        """
        if isinstance(value, dict):
            if "valueFrom" in value:
                value_from = deserialize(NetBoxObjectValueFrom, value["valueFrom"])
                return self._get_value_from_ref(value_from)

            return {k: self._resolve_nested_values(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self._resolve_nested_values(item) for item in value]

        return value

    def _get_body_item_value(self, body_item: NetBoxObjectBodyItem) -> Any:
        """
        Given NetBoxObjectBodyItem, get the resulting value
        """
        value = None

        if body_item.value is not None:
            resolved_value = self._resolve_nested_values(body_item.value)
            value = self._get_netbox_compatible_value(
                path=body_item.path, value=resolved_value
            )

        if body_item.value_from is not None:
            value = self._get_value_from_ref(body_item.value_from)

        return value

    def _get_body_data(self):
        """
        Get the body of a NetBox object. It can be used for creation and update operations
        """
        data = {}
        for body_item in self.netbox_object.body:
            value = self._get_body_item_value(body_item)
            assign(data, path=body_item.path, val=value, missing=dict)

        if "description" in data:
            data["description"] += f" | {MANAGED_OBJECT_DESCRIPTION}"
        else:
            data["description"] = MANAGED_OBJECT_DESCRIPTION

        logger.debug(
            "[%s] Constructed NetBox object body: %s", self.k8s_object_name, data
        )

        return data

    def _get_lookup_filter(self) -> dict:
        """
        Get the lookup filter of a NetBox object
        """
        netbox_obj_filter = {}
        for body_item in self.netbox_object.body:
            if not body_item.lookup_key:
                continue

            lookup_key = (
                body_item.lookup_alias if body_item.lookup_alias else body_item.path
            )

            lookup_value = None

            if body_item.value is not None:
                lookup_value = body_item.value

            if body_item.value_from is not None:
                lookup_value = self._get_value_from_ref(body_item.value_from)

            netbox_obj_filter[lookup_key] = lookup_value

        logger.debug(
            "[%s] Constructed NetBox object lookup filter: filter=%s",
            self.k8s_object_name,
            netbox_obj_filter,
        )

        return netbox_obj_filter

    def _find_existing_object(self) -> Record | None:
        """
        Find existing NetBox
        """
        netbox_obj_filter = self._get_lookup_filter()
        if not netbox_obj_filter:
            return None

        existing_obj = self.endpoint.get(**netbox_obj_filter)

        return existing_obj

    def _get_removed_fields(self):
        """
        Compare the old and current spec of the object to find if any fields were removed
        :return: a dict of field keys and new values
        """
        if not self.old_spec:
            logger.debug(
                "[%s] Can't get removed fields as their is no old spec",
                self.k8s_object_name,
            )
            return {}

        old_netbox_object_spec = self._netbox_object_from_spec(self.old_spec)
        old_keys = [body_item.path for body_item in old_netbox_object_spec.body]
        new_keys = [body_item.path for body_item in self.netbox_object.body]

        removed_keys = list(set(old_keys) - set(new_keys))

        unset_data = {}
        for key in removed_keys:
            body_item = [
                body_item
                for body_item in old_netbox_object_spec.body
                if body_item.path == key
            ][0]

            path_parts = key.split(".")
            path_root = path_parts[0]

            # the given path is a nested dict
            # therefore, we don't need to resolve the value, we know it's a dict
            if len(path_parts) > 1:
                unset_data[path_root] = None
                continue

            value = None

            if body_item.value is not None:
                value = body_item.value

            if body_item.value_from is not None:
                value = self._get_value_from_ref(body_item.value_from)

            new_value = netbox_value_to_default(value)

            unset_data[path_root] = new_value

        return unset_data

    def create_or_update(self):
        """
        Create an object in NetBox if it doesn't exist. Otherwise, update it
        We will try to find an existing object using Kubernetes resource status
        or user-provided spec
        """
        netbox_obj: Record = None
        data = self._get_body_data()

        if self.k8s_object_status:
            endpoint = self.k8s_object_status.netboxobject_endpoint
            obj_id = self.k8s_object_status.netboxobject_id

            netbox_obj: Record = endpoint.get(obj_id)

        # the object may or may not be managed by the operator
        # because we have no information about it in the status
        # let's try to find an existing object using lookup keys
        if not netbox_obj:
            netbox_obj = self._find_existing_object()

            if netbox_obj and self.netbox_object.allow_existing:
                logger.info(
                    (
                        "[%s] Found an existing NetBox object "
                        "that is not managed by the operator, "
                        "will update it: url=%s, id=%s"
                    ),
                    self.k8s_object_name,
                    netbox_obj.url,
                    netbox_obj.id,
                )

            # the object is not managed by the operator
            # and managing existing objects is not allowed
            if netbox_obj and not self.netbox_object.allow_existing:
                raise PermanentError(
                    f"Found existing NetBox object url={netbox_obj.url}, "
                    "but managing existing objects is not allowed",
                )

        if netbox_obj:
            netbox_obj = self.update(netbox_obj, data)
        else:
            netbox_obj = self.create(data)

        return {
            "url": netbox_obj.url,
            "id": netbox_obj.id,
            "dataModel": self.netbox_object.data_model,
            "endpoint": netbox_obj.endpoint.name,
        }

    def _allocate_available_object(self, data: dict):
        """
        Allocate an available NetBox object with the given data
        """
        parent_netbox_obj_id = data.get("id")
        data.pop("id", None)

        # we expect the id path to be present for every endpoint besides VLANs
        if not parent_netbox_obj_id and self.endpoint.name != "vlans":
            raise ValueError(
                "The id path must be present to allocate a new resource: ",
                f"endpoint={self.endpoint.url}",
            )

        parent_netbox_obj = None

        if parent_netbox_obj_id:
            parent_netbox_obj: Record = self.endpoint.get(parent_netbox_obj_id)
            if not parent_netbox_obj:
                raise ValueError(
                    "Could not allocate a new object: "
                    f"failed to find parent NetBox object {parent_netbox_obj_id}, "
                    f"endpoint={self.endpoint.url}"
                )

        netbox_obj = None
        detail_endpoint = None

        # the presence of the prefix length indicates that we need to provision
        # a new prefix from prefix instead of an IP from prefix
        # https://pynetbox.readthedocs.io/en/latest/IPAM.html#pynetbox.models.ipam.Prefixes.available_prefixes
        has_prefix_length = "prefix_length" in data

        endpoint_name = (
            parent_netbox_obj.endpoint.name if parent_netbox_obj else self.endpoint.name
        )
        # match endpoint_name:
        if endpoint_name == "ip-ranges":
            detail_endpoint = DetailEndpoint(
                parent_obj=parent_netbox_obj,
                name="available-ips",
                custom_return=IpAddresses,
            )
        elif endpoint_name == "prefixes" and has_prefix_length:
            detail_endpoint = DetailEndpoint(
                parent_obj=parent_netbox_obj,
                name="available-prefixes",
                custom_return=Prefixes,
            )
        elif endpoint_name == "prefixes":
            detail_endpoint = DetailEndpoint(
                parent_obj=parent_netbox_obj,
                name="available-ips",
                custom_return=IpAddresses,
            )
        elif endpoint_name == "vlan-groups":
            detail_endpoint = DetailEndpoint(
                parent_obj=parent_netbox_obj,
                name="available-vlans",
                custom_return=Vlans,
            )
        elif endpoint_name == "vlans":
            detail_endpoint = AvailableGlobalVlan()
        else:
            raise PermanentError(
                f'Unsupported endpoint "{endpoint_name}" '
                "for allocating available objects"
            )

        logger.info(
            "[%s] Allocating next available object: url=%s, data=%s",
            self.k8s_object_name,
            detail_endpoint.url,
            data,
        )
        netbox_obj = detail_endpoint.create(data)

        return netbox_obj

    def create(self, data: dict) -> Record:
        """
        Create an object in NetBox
        :param data: a dictionary with data to pass as the object body
        """
        netbox_obj = None

        if self.netbox_object.allocate_available:
            return self._allocate_available_object(data)

        logger.info(
            "[%s] Creating NetBox object, endpoint=%s, data=%s",
            self.k8s_object_name,
            self.endpoint.url,
            data,
        )

        netbox_obj = self.endpoint.create(**data)
        return netbox_obj

    def update(self, netbox_obj: Record, data: dict) -> Record:
        """
        Update a NetBox object with the given data
        """
        logger.info(
            "[%s] Updating NetBox object, id=%s, endpoint=%s, data=%s",
            self.k8s_object_name,
            netbox_obj.id,
            self.endpoint.url,
            data,
        )

        removed_fields = self._get_removed_fields()
        if removed_fields:
            logger.info(
                ("[%s] Unsetting removed fields: removed_fields=%s, endpoint=%s"),
                self.k8s_object_name,
                removed_fields,
                netbox_obj.endpoint.url,
            )
            netbox_obj.update(removed_fields)

        if self.netbox_object.allocate_available:
            data.pop("id", None)

        # TODO: improve diffing logic to avoid unnecessary NetBox calls
        # e.g., passing tenant.name=string is correct but pynetbox sees only tenant=string
        # and this causes diff all the time
        netbox_obj.update(data)

        return netbox_obj

    def delete(self) -> bool:
        """
        Delete a NetBox object
        :return bool: whether the object was deleted
        """
        if not self.k8s_object_status:
            raise PermanentError(
                f"[{self.k8s_object_name}]"
                "The ID of the existing NetBox object is not available"
            )

        obj_id = self.k8s_object_status.netboxobject_id
        endpoint = self.k8s_object_status.netboxobject_endpoint

        netbox_obj: Record = endpoint.get(obj_id)
        if not netbox_obj:
            logger.warning(
                (
                    "[%s] Didn't find NetBox object "
                    "with id %s at endpoint %s, skipping deletion"
                ),
                self.k8s_object_name,
                self.k8s_object_status.netboxobject_id,
                self.endpoint.url,
            )
            return False

        logger.info(
            "[%s] Deleting NetBox object: id=%s, endpoint=%s",
            self.k8s_object_name,
            obj_id,
            self.endpoint.url,
        )

        try:
            deleted = netbox_obj.delete()
        except RequestError as e:
            if e.req.status_code == 409:
                raise NetBoxConflict(
                    (
                        "Failed to delete object due to conflict, will retry in 5 seconds: ",
                        f"url={netbox_obj.url}, error={e.error}",
                    ),
                ) from e
            raise e

        return deleted
