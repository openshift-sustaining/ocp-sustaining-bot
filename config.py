import logging
import os
import re
from dotenv import load_dotenv
from dynaconf import Dynaconf
import tempfile
import json
import httpx
import hvac

required_keys = [
    "GOOGLE_CLOUD_CREDS",
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "OS_AUTH_URL",
    "OS_PROJECT_ID",
    "OS_INTERFACE",
    "OS_ID_API_VERSION",
    "OS_REGION_NAME",
    "OS_APP_CRED_ID",
    "OS_APP_CRED_SECRET",
    "OS_AUTH_TYPE",
    "ALLOW_ALL_WORKSPACE_USERS",
    "ALLOWED_SLACK_USERS",
    "ROTA_SERVICE_ACCOUNT",
    "ROTA_ADMINS",
    "ROTA_USERS",
]

load_dotenv()

# Default GCP machine types for help / command choices if ``GCP_POPULAR_INSTANCE_TYPES`` is unset
# or invalid in ``.env`` (JSON array of strings).
gcp_popular_instance_types = [
    "e2-micro",
    "e2-small",
    "e2-medium",
    "e2-standard-2",
    "e2-standard-4",
    "e2-standard-8",
    "n1-standard-1",
    "n1-standard-2",
    "n1-standard-4",
    "n2-standard-2",
    "n2-standard-4",
    "n2-standard-8",
    "n2-standard-16",
    "n2-highmem-4",
    "n2-highmem-8",
    "n2d-standard-2",
    "n2d-standard-4",
    "n2d-standard-8",
    "c2d-standard-4",
    "c2d-standard-8",
]

_GCP_MACHINE_TYPE_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# GCP boot disk size (GB) must be one of these; env ``GCP_BOOT_DISK_SIZE_GB`` picks which to use.
_GCP_DEFAULT_DISK_SIZES = (10, 20, 50)


def _resolve_gcp_boot_disk_size_gb():
    """
    Read ``GCP_BOOT_DISK_SIZE_GB`` from config (``.env`` / Vault). If missing or invalid,
    use ``_GCP_DEFAULT_DISK_SIZES[0]``. If set but not in ``_GCP_DEFAULT_DISK_SIZES``,
    log a warning and use ``_GCP_DEFAULT_DISK_SIZES[0]``.
    """
    raw = getattr(config, "GCP_BOOT_DISK_SIZE_GB", None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return _GCP_DEFAULT_DISK_SIZES[0]
    try:
        n = int(raw)
    except (TypeError, ValueError):
        logging.warning(
            "GCP_BOOT_DISK_SIZE_GB=%r is not an integer; using %s",
            raw,
            _GCP_DEFAULT_DISK_SIZES[0],
        )
        return _GCP_DEFAULT_DISK_SIZES[0]
    if n not in _GCP_DEFAULT_DISK_SIZES:
        logging.warning(
            "GCP_BOOT_DISK_SIZE_GB=%s is not in %s; using %s",
            n,
            _GCP_DEFAULT_DISK_SIZES,
            _GCP_DEFAULT_DISK_SIZES[0],
        )
        return _GCP_DEFAULT_DISK_SIZES[0]
    return n


def _normalize_gcp_instance_types_list(value):
    """Return sorted unique machine type strings, or None if value is missing/invalid."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, (list, tuple)):
        return None
    out = []
    for x in value:
        s = str(x).strip().lower()
        if s and len(s) <= 63 and _GCP_MACHINE_TYPE_NAME_RE.match(s):
            out.append(s)
    return sorted(set(out)) if out else None


req_env_vars = {
    "RH_CA_BUNDLE_TEXT",
    "VAULT_ENABLED_FOR_DYNACONF",
    "VAULT_URL_FOR_DYNACONF",
    "VAULT_SECRET_ID_FOR_DYNACONF",
    "VAULT_ROLE_ID_FOR_DYNACONF",
    "VAULT_MOUNT_POINT_FOR_DYNACONF",
    "VAULT_PATH_FOR_DYNACONF",
    "VAULT_KV_VERSION_FOR_DYNACONF",
}

# DON'T MOVE: `basicConfig` gets called only once. Dynaconf sets it to `WARNING` so our setting should be above that
log_level = os.getenv("LOG_LEVEL", "INFO")
log_level = log_level.upper()
log_level_int = getattr(logging, log_level, 20)
log_format = "[%(asctime)s %(levelname)s %(name)s] %(message)s"
logging.basicConfig(level=log_level_int, format=log_format)

vault_enabled = req_env_vars <= set(os.environ.keys())  # subset of os.environ

# Load CA Cert to avoid SSL errors
ca_bundle_file = tempfile.NamedTemporaryFile()
cert_txt = os.getenv("RH_CA_BUNDLE_TEXT", "")
cert_text_final = cert_txt.replace("\\n", "\n")
with open(ca_bundle_file.name, "w") as f:
    f.write(cert_text_final)

# print("CA bundle file:", ca_bundle_file.name)
# os.system(f"cat  {ca_bundle_file.name}")


try:
    config = Dynaconf(
        load_dotenv=True,  # This will load config from `.env`
        environment=False,  # This will disable layered env
        vault_enabled=vault_enabled,
        vault={
            "url": os.getenv("VAULT_URL_FOR_DYNACONF", ""),
            "verify": ca_bundle_file.name,
        },
        envvar_prefix=False,  # This will make it so that ALL the variables from `.env` are loaded
    )
except (httpx.ConnectError, ConnectionError):
    logging.warn("Vault connection failed")
except hvac.exceptions.InvalidRequest:
    logging.warn("Authentication error with Vault")

for key in dir(config):
    try:
        value = getattr(config, key)
        if isinstance(value, str):
            val = json.loads(value)
            # NOTE: This will create a `Dynabox` object which is basically a wrapper around dicts which allows . access to keys
            # So you can access `config.key.val` instead of `config.key['val']` but it can be used like a dictionary as well.
            config.set(key, val)
    except json.decoder.JSONDecodeError:
        logging.warn(f"{key} is not a valid JSON string .")
        pass
    except AttributeError:
        logging.warn(f"Attribute {key} not found.")  # Should usually be harmless

# ``GCP_POPULAR_INSTANCE_TYPES`` in ``.env``: JSON array of machine types, e.g.
# GCP_POPULAR_INSTANCE_TYPES=["e2-medium","n2-standard-4"]
# If missing or invalid, ``config.GCP_POPULAR_INSTANCE_TYPES`` is set to ``gcp_popular_instance_types``.
_raw_gcp_instance_types = getattr(config, "GCP_POPULAR_INSTANCE_TYPES", None)
_gcp_types = _normalize_gcp_instance_types_list(_raw_gcp_instance_types)
if _gcp_types is None:
    if _raw_gcp_instance_types not in (None, ""):
        logging.warning(
            "GCP_POPULAR_INSTANCE_TYPES is missing or invalid; using gcp_popular_instance_types"
        )
    _gcp_types = list(gcp_popular_instance_types)
else:
    logging.info(
        "GCP_POPULAR_INSTANCE_TYPES loaded from environment (%d types)",
        len(_gcp_types),
    )
config.set("GCP_POPULAR_INSTANCE_TYPES", _gcp_types)


def _resolve_gcp_default_instance_type():
    """
    Default machine type when ``gcp vm create`` omits ``--instance-type`` / ``--instance_type``.

    Read ``GCP_DEFAULT_INSTANCE_TYPE`` from config. It must appear in
    ``GCP_POPULAR_INSTANCE_TYPES``. If missing or invalid, use ``e2-medium`` when allowed,
    otherwise the first entry in ``GCP_POPULAR_INSTANCE_TYPES``.
    """
    allowed = list(config.GCP_POPULAR_INSTANCE_TYPES)
    allowed_set = set(allowed)
    raw = getattr(config, "GCP_DEFAULT_INSTANCE_TYPE", None)
    fallback = "e2-medium" if "e2-medium" in allowed_set else allowed[0]

    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return fallback

    s = str(raw).strip().lower()
    if not _GCP_MACHINE_TYPE_NAME_RE.match(s):
        logging.warning(
            "GCP_DEFAULT_INSTANCE_TYPE=%r is not a valid machine type name; using %s",
            raw,
            fallback,
        )
        return fallback
    if s not in allowed_set:
        logging.warning(
            "GCP_DEFAULT_INSTANCE_TYPE=%s is not in GCP_POPULAR_INSTANCE_TYPES; using %s",
            s,
            fallback,
        )
        return fallback
    return s


config.set(
    "GCP_DEFAULT_INSTANCE_TYPE",
    _resolve_gcp_default_instance_type(),
)

# ``GCP_DEFAULT_INSTANCE_TYPE`` in ``.env``: machine type used when ``gcp vm create`` omits
# ``--instance-type`` / ``--instance_type``. Must be in ``GCP_POPULAR_INSTANCE_TYPES``.

# Boot disk size (GB) for `gcp vm create`: ``GCP_BOOT_DISK_SIZE_GB`` in ``.env`` (must be one of
# ``_GCP_DEFAULT_DISK_SIZES``). Resolved and stored as ``config.GCP_BOOT_DISK_SIZE_GB``.
config.set("GCP_BOOT_DISK_SIZE_GB", _resolve_gcp_boot_disk_size_gb())

# Verify that all keys were loaded correctly
for k in required_keys:
    if not hasattr(config, k):
        logging.error(f"Could not read key: {k} from Vault.")
        raise AttributeError(f"Could not read key: {k} from Vault.")
