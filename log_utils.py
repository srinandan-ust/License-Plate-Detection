# log_utils.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures a rotating file logger."""
    logger = logging.getLogger('LPR_System')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('logs/detection.log', maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger