# coding: utf-8

import logging

from ecard import SummaryTask as Task

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    task = Task()
    task.run()
