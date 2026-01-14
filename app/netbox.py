import pynetbox
import urllib3
from pynetbox.core.response import Record
from app.config import Settings
from app.metrics import InstrumentedSession

settings = Settings()

nb = pynetbox.api(url=str(settings.netbox_url), token=settings.netbox_token)
nb.http_session = InstrumentedSession()

if not settings.netbox_verify_ssl:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

nb.http_session.verify = settings.netbox_verify_ssl


def get_or_create_netbox_tag(name: str) -> Record:
    """
    Create a tag in NetBox if it doesn't exist
    :param name: The name of the NetBox tag
    """
    existing_tag = nb.extras.tags.get(name=name)
    if existing_tag:
        return existing_tag

    return nb.extras.tags.create(
        name=name, slug=name.lower(), description="Created by netbox-resources-operator"
    )


class ExhaustedVlan(Exception):
    pass


class AvailableGlobalVlan:
    def __init__(self):
        # URL is added for compatibility reasons with DetailEndpoint
        self.url = nb.ipam.vlans.url

    def list(self):
        """
        Find available VLANs globally
        NetBox supports finding available VLANs inside groups
        This function searches them across all groups
        """
        max_vlans = 4096
        all_vlans = nb.ipam.vlans.all()
        all_vlan_vids = [v.vid for v in all_vlans]

        available_vlan_vids = [
            i for i in range(1, max_vlans + 1) if i not in all_vlan_vids
        ]

        return available_vlan_vids

    def create(self, data: dict):
        """
        Create the next available VLAN that doesn't exist globally
        (either in a group or without it)
        """
        available_vlan_vids = self.list()

        if not available_vlan_vids:
            raise ExhaustedVlan(
                "Cannot find available VIDs to allocate a new global VLAN"
            )

        data["vid"] = available_vlan_vids[0]

        return nb.ipam.vlans.create(**data)
