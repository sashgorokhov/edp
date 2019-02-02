import logging
import logging.config

import sentry_sdk

from edp import config


def configure(enable_sentry: bool = True):
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)

    if config.SENTRY_DSN and config.FROZEN and enable_sentry:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            release=config.VERSION,
            server_name='unknown'
        )


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'short': {
            'format': '%(levelname)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': config.LOGS_DIR / 'edp.log',
            'maxBytes': 1024 * 1024,  # 1 mb
            'backupCount': 10
        },
        'capi': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': config.LOGS_DIR / 'edp_capi.log',
            'maxBytes': 1024 * 1024,  # 1 mb
            'backupCount': 5
        }
    },
    'loggers': {
        'edp': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'edp.plugins': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'edp.utils.discord_rpc': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False
        },
        'edp.contrib.capi': {
            'handlers': ['capi', 'console'],
            'level': 'DEBUG',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR'
    },
}
