import logging
import os
import sys

import config
import utils

if __name__ == '__main__':
    for path in ['logs', 'maintain', 'ignore']:
        if not os.path.isdir(path):
            os.makedirs(path)

    root_logger = utils.get_a_logger(None)
    info_logger = utils.get_a_logger(None, logging.INFO, 1)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(config.FORMATTER)

    root_logger.addHandler(sh)
    root_logger.setLevel(1)
    logging.info('\n\n\n')
    logging.info("Starting pydis-pixels canvas drawing")
    import strategy

    strategy.main_loop()
