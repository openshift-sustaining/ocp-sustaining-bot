import logging
import re
import traceback

from config import config
from google.api_core import exceptions as google_exceptions
from google.cloud import compute_v1
from google.oauth2 import service_account
from sdk.tools.helpers import get_list_of_values_for_key_in_dict_of_parameters

logger = logging.getLogger(__name__)


class GCPHelper:
    def __init__(self):
        self.region = getattr(config, "GCP_DEFAULT_REGION", "asia-south1")
        _info = dict(config["GOOGLE_CLOUD"])
        self._credentials = service_account.Credentials.from_service_account_info(
            _info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        self.project_id = _info.get("project_id", "")
        network = getattr(config, "GCP_NETWORK", None) or "default"
        # network = "slackbot-vpc"
        if not network.startswith(("projects/", "global/")):
            network = f"global/networks/{network}"
        self.network = network
        # Subnetwork required for custom VPC; use same region as helper
        subnetwork = getattr(config, "GCP_SUBNETWORK", None)
        # subnetwork = "slackbot-vpc-net1"
        if subnetwork and not subnetwork.startswith(("projects/", "regions/")):
            subnetwork = f"regions/{self.region}/subnetworks/{subnetwork}"
        self.subnetwork = subnetwork
        logger.info(f"Region set for session: {self.region}")

    def _instance_to_info(self, instance, zone_key):
        """Map a GCP Instance to the EC2-style instance info dict."""
        # Zone key is like "zones/us-central1-a"; strip to get zone name
        zone_name = zone_key.split("/")[-1] if zone_key else ""

        state = (instance.status or "").lower() if instance.status else ""

        # machine_type is a URL; use last segment (e.g. n1-standard-4)
        machine_type = "N/A"
        if instance.machine_type:
            machine_type = instance.machine_type.split("/")[-1]

        # Boot disk: first boot disk's source (image URL contains /images/)
        image_id = "N/A"
        if instance.disks:
            for d in instance.disks:
                if getattr(d, "boot", False):
                    src = getattr(d, "source", "") or ""
                    if "/images/" in src:
                        image_id = src.split("/")[-1]
                    break

        # Labels (GCP) -> name, architecture (like EC2 tags)
        name = instance.name or ""
        architecture = ""
        if instance.labels:
            architecture = instance.labels.get("architecture", "")

        # Network: first interface (proto uses network_i_p, access_configs)
        private_ip = "N/A"
        public_ip = "N/A"
        vpc_id = "N/A"
        if instance.network_interfaces:
            ni = instance.network_interfaces[0]
            private_ip = getattr(ni, "network_i_p", None) or "N/A"
            network_url = getattr(ni, "network", None) or ""
            vpc_id = network_url.split("/")[-1] if network_url else "N/A"
            for ac in getattr(ni, "access_configs", []) or []:
                if getattr(ac, "type", None) == "ONE_TO_ONE_NAT":
                    public_ip = getattr(ac, "nat_i_p", None) or "N/A"
                    break

        return {
            "name": name,
            "architecture": architecture,
            "instance_id": str(instance.id) if instance.id else instance.name or "",
            "image_id": image_id,
            "instance_type": machine_type,
            "key_name": "",  # GCP uses metadata/OS Login or project-level keys
            "vpc_id": vpc_id,
            "public_ip": public_ip,
            "private_ip": private_ip,
            "state": state,
            "zone": zone_name,
        }

    def _get_zone_by_instance_name(self, instance_name):
        """
        Resolve the zone of an instance by name (search in self.region).
        Returns (zone_name, None) if found, or (None, error_message) if not.
        """
        if not instance_name or not instance_name.strip():
            return None, "Instance name is required"
        instance_name = instance_name.strip()
        try:
            client = compute_v1.InstancesClient(credentials=self._credentials)
            request = compute_v1.AggregatedListInstancesRequest()
            request.project = self.project_id
            request.max_results = 500
            zone_prefix = f"zones/{self.region}"
            for zone_key, response in client.aggregated_list(request=request):
                if not response.instances or not zone_key.startswith(zone_prefix):
                    continue
                for instance in response.instances:
                    if instance.name == instance_name:
                        zone_name = zone_key.split("/")[-1]
                        return zone_name, None
            return None, f"Instance '{instance_name}' not found in region {self.region}"
        except Exception as e:
            logger.error(f"Error resolving instance zone: {e}")
            return None, str(e)

    def stop_instance(self, instance_name):
        """
        Stop a GCP VM instance by name.

        :param instance_name: The name of the instance to stop.
        :return: Dict with "success" (bool) and optionally "error" (str).
        """
        zone, err = self._get_zone_by_instance_name(instance_name)
        if err:
            return {"success": False, "error": err}
        try:
            client = compute_v1.InstancesClient(credentials=self._credentials)
            operation = client.stop(
                project=self.project_id,
                zone=zone,
                instance=instance_name,
            )
            operation.result(timeout=120)
            logger.info(f"Successfully stopped instance {instance_name} in zone {zone}")
            return {"success": True, "instance_name": instance_name, "zone": zone}
        except google_exceptions.NotFound:
            return {"success": False, "error": f"Instance '{instance_name}' not found"}
        except Exception as e:
            logger.error(f"Error stopping instance {instance_name}: {e}")
            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def delete_instance(self, instance_name):
        """
        Delete a GCP VM instance by name.

        :param instance_name: The name of the instance to delete.
        :return: Dict with "success" (bool) and optionally "error" (str).
        """
        zone, err = self._get_zone_by_instance_name(instance_name)
        if err:
            return {"success": False, "error": err}
        try:
            client = compute_v1.InstancesClient(credentials=self._credentials)
            operation = client.delete(
                project=self.project_id,
                zone=zone,
                instance=instance_name,
            )
            operation.result(timeout=120)
            logger.info(f"Successfully deleted instance {instance_name} in zone {zone}")
            return {"success": True, "instance_name": instance_name, "zone": zone}
        except google_exceptions.NotFound:
            return {"success": False, "error": f"Instance '{instance_name}' not found"}
        except Exception as e:
            logger.error(f"Error deleting instance {instance_name}: {e}")
            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def list_instances(self, params_dict=None):
        """
        get all GCP instances in the specified region.
        returns a dictionary with information on server instances (EC2-style shape).
        """
        if params_dict is None:
            params_dict = {}
        instance_ids = get_list_of_values_for_key_in_dict_of_parameters(
            "instance-ids", params_dict
        )
        state_filters = get_list_of_values_for_key_in_dict_of_parameters(
            "state", params_dict
        )
        instance_type_filters = get_list_of_values_for_key_in_dict_of_parameters(
            "type", params_dict
        )
        if state_filters:
            state_filters = {s.lower() for s in state_filters}
        if instance_type_filters:
            instance_type_filters = {t.lower() for t in instance_type_filters}

        try:
            client = compute_v1.InstancesClient(credentials=self._credentials)
            request = compute_v1.AggregatedListInstancesRequest()
            request.project = self.project_id
            request.max_results = 500
            agg_list = client.aggregated_list(request=request)

            instances_info = []
            # Restrict to zones in self.region (e.g. us-central1-a, us-central1-b)
            zone_prefix = f"zones/{self.region}"
            for zone_key, response in agg_list:
                if not response.instances:
                    continue
                if not zone_key.startswith(zone_prefix):
                    continue
                for instance in response.instances:
                    state = (instance.status or "").lower()
                    if state_filters and state not in state_filters:
                        continue
                    machine_type = ""
                    if instance.machine_type:
                        machine_type = instance.machine_type.split("/")[-1].lower()
                    if (
                        instance_type_filters
                        and machine_type not in instance_type_filters
                    ):
                        continue
                    if instance_ids:
                        name_ok = instance.name in instance_ids
                        id_ok = str(instance.id) in instance_ids
                        if not (name_ok or id_ok):
                            continue
                    info = self._instance_to_info(instance, zone_key)
                    instances_info.append(info)

            return {"count": len(instances_info), "instances": instances_info}
        except google_exceptions.Forbidden as e:
            logger.error(f"GCP Compute API Forbidden (403): {e}")
            raise PermissionError(
                "Access to Compute Engine API was denied. For project "
                f"'{self.project_id}': (1) Enable the 'Compute Engine API' in Google "
                "Cloud Console (APIs & Services → Library → Compute Engine API). "
                "(2) Grant the service account (e.g. Compute Viewer, "
                "roles/compute.viewer) on the project. If you just enabled the API, "
                "wait a few minutes and retry."
            ) from e
        except Exception as e:
            logger.error(f"Unable to get instances from GCP: {e}")
            raise

    def create_instance(
        self,
        image_id,
        instance_type,
        instance_name,
        zone=None,
        network=None,
    ):
        """
        Create a GCP VM instance with the given parameters

        Args:
            image_id: Source image for the boot disk. Use a full path
                (e.g. projects/debian-cloud/global/images/family/debian-12)
                or an image family name (e.g. debian-12) which will be resolved
                as projects/debian-cloud/global/images/family/<image_id>.
            instance_type: Machine type (e.g. n1-standard-1, e2-medium).
            instance_name: Name for the VM (1–63 chars, lowercase, digits, hyphens;
                must match [a-z]([-a-z0-9]*[a-z0-9])?).
            zone: Optional zone (e.g. asia-south1-a). Defaults to <region>-a.
            network: Optional network name or URL (e.g. default, or
                projects/PROJECT/global/networks/VPC). Uses config.GCP_NETWORK
                if not set, then global/networks/default.

        Returns:
            {"count": 1, "instances": [{"name", "instance_id", "instance_type", "public_ip"}]}
            or on error {"count": 0, "instances": [], "error": "..."}.
        """
        zone = zone or f"{self.region}-a"
        instance_name = (instance_name or "").strip().lower()
        if not instance_name:
            return {
                "count": 0,
                "instances": [],
                "error": "instance_name is required",
            }
        if len(instance_name) > 63:
            return {
                "count": 0,
                "instances": [],
                "error": "instance_name must be at most 63 characters",
            }
        if not re.match(r"^[a-z]([-a-z0-9]*[a-z0-9])?$", instance_name):
            return {
                "count": 0,
                "instances": [],
                "error": "instance_name must start with a letter, use only lowercase letters, digits, and hyphens",
            }

        try:
            client = compute_v1.InstancesClient(credentials=self._credentials)

            # Resolve image: if not a full path, treat as image family
            if image_id.startswith("projects/"):
                source_image = image_id
            else:
                source_image = f"projects/debian-cloud/global/images/family/{image_id}"

            disk_size_gb = 10
            boot_disk = compute_v1.AttachedDisk()
            init_params = compute_v1.AttachedDiskInitializeParams()
            init_params.source_image = source_image
            init_params.disk_size_gb = disk_size_gb
            boot_disk.initialize_params = init_params
            boot_disk.auto_delete = True
            boot_disk.boot = True

            # Network: param overrides instance default (self.network from config)
            network_ref = network if network is not None else self.network
            if not network_ref.startswith(("projects/", "global/")):
                network_ref = f"global/networks/{network_ref}"

            network_interface = compute_v1.NetworkInterface()
            network_interface.network = network_ref
            if self.subnetwork:
                network_interface.subnetwork = self.subnetwork
            access = compute_v1.AccessConfig()
            access.type_ = "ONE_TO_ONE_NAT"
            access.name = "External NAT"
            access.network_tier = "PREMIUM"
            network_interface.access_configs = [access]

            instance_resource = compute_v1.Instance()
            instance_resource.name = instance_name
            instance_resource.machine_type = (
                f"zones/{zone}/machineTypes/{instance_type}"
            )
            instance_resource.disks = [boot_disk]
            instance_resource.network_interfaces = [network_interface]

            request = compute_v1.InsertInstanceRequest()
            request.project = self.project_id
            request.zone = zone
            request.instance_resource = instance_resource

            operation = client.insert(request=request)
            operation.result(timeout=300)

            created = client.get(
                project=self.project_id,
                zone=zone,
                instance=instance_name,
            )
            public_ip = "N/A"
            if created.network_interfaces:
                ni = created.network_interfaces[0]
                for ac in getattr(ni, "access_configs", []) or []:
                    if getattr(ac, "nat_i_p", None):
                        public_ip = ac.nat_i_p
                        break

            instance_info = {
                "name": instance_name,
                "instance_id": str(created.id) if created.id else instance_name,
                "instance_type": instance_type,
                "public_ip": public_ip,
            }
            logger.info(f"Instance {instance_name} created successfully in {zone}")
            return {"count": 1, "instances": [instance_info]}
        except google_exceptions.Forbidden as e:
            logger.error(f"GCP Compute API Forbidden (403): {e}")
            return {
                "count": 0,
                "instances": [],
                "error": (
                    "Access denied to Compute Engine API. Enable the API and "
                    "grant the service account roles/compute.instanceAdmin.v1 "
                    "(or similar) on the project."
                ),
            }
        except Exception as e:
            logger.error(f"An error occurred creating the GCP instance: {e}")
            logger.debug(traceback.format_exc())
            return {"count": 0, "instances": [], "error": str(e)}
