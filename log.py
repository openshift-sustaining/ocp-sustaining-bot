import inspect

from config import config
import logging


def create_logger(name=None):
    """
    Create a logger to log the events in the code, the logger is based in the logging Python dependency.

    :param name: Name of the log used to refer where the log is coming from.
    If no name is provided, the logger will use the module name that is calling this function.
    :return: The logger object
    """

    if name is None:
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        name = mod.__name__

    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)

    formatter = logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(config.LOG_LEVEL)

    logger.addHandler(ch)

    return logger
