import logging
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Config class to load and validate environment variables.
    """

    def __init__(self):
        log_level = os.getenv("LOG_LEVEL_API", "INFO")
        self.log_level = log_level.upper()

        self.setup_logging()

    def setup_logging(self):
        log_format = "[%(asctime)s %(levelname)s %(name)s] %(message)s"

        logging.basicConfig(level=self.log_level, format=log_format)


config = Config()
