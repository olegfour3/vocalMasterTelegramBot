import os
import logging
import locale
from logging.handlers import RotatingFileHandler

locale.setlocale(
    category=locale.LC_ALL,
    locale="Russian"
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


NOTIFICATION_HOUR = 9
NOTIFICATION_MINUTE = 0


log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'logfile.log'
console_out = logging.StreamHandler()
log_handler = RotatingFileHandler(logFile,
                                  mode='a',
                                  maxBytes=5*1024*1024,
                                  backupCount=2,
                                  encoding=None,
                                  delay=0)

log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.addHandler(log_handler)
logger.addHandler(console_out)



