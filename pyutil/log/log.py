import logging
import os
from .multi_process_logger import MultiProcessRotatingFileHandler

def init(conf, logger=None, console_log_level=None):
    # make path
    log_dir = os.path.dirname(conf.filename) if conf else './log'
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    
    format = '%(asctime)s, %(levelname)s %(message)s'
    filename = os.path.join(log_dir, 'log')
    level = logging.INFO

    if conf:
        format = conf.format or format
        filename = conf.filename or filename
        level = int(conf.level) if conf.level else level
        if conf.console_log_level:
            console_log_level = int(conf.console_log_level)
        
    if logger is None:
        logger = logging.getLogger()

    logger.setLevel(level)
    formatter = logging.Formatter(format)

    if filename:
        handler = MultiProcessRotatingFileHandler(filename=filename, when='midnight')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if console_log_level is not None:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(format)
        ch.setFormatter(logging.Formatter(format))
        ch.setLevel(console_log_level)
        logger.addHandler(ch)
