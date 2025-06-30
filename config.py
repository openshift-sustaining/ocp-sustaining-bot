import logging
import os
from dotenv import load_dotenv
import json

#
load_dotenv()


class Config:
    """
    Config class to load and validate environment variables.

    If any environment variable is missing or empty, a ValueError will be raised.
    """

    def __init__(self):
        # Load environment variables from a .env file
        load_dotenv()
        required_keys = [
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
            "OS_IMAGE_MAP",
            "OS_NETWORK_MAP",
            "OS_DEFAULT_NETWORK",
            "OS_DEFAULT_SSH_USER",
            "OS_DEFAULT_KEY_NAME",
        ]
        for key in required_keys:
            value = os.getenv(key)
            try:
                if not value:
                    # Raise an error if the environment variable is missing or empty
                    raise ValueError(
                        f"Missing or empty value for environment variable: {key}"
                    )

                setattr(self, key, value)

            except ValueError as e:
                logging.error(f"Error: {e}")
                raise

            except Exception as e:
                logging.error(f"Unexpected error with environment variable {key}: {e}")
                raise

        # Parse all environment variables
        for key, value in os.environ.items():
            value = value.strip()
            parsed = value

            if value.startswith("{") or value.startswith("["):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON format for {key}: {e}")
                    raise ValueError(f"Invalid JSON format for {key}")

            setattr(self, key, parsed)

        # Logging level
        log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_level = log_level.upper()

        self.setup_logging()

    def setup_logging(self):
        log_format = "[%(asctime)s %(levelname)s %(name)s] %(message)s"

        logging.basicConfig(level=self.log_level, format=log_format)


config = Config()
