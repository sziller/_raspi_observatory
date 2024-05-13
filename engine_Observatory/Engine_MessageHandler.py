import os
from picamera2 import Picamera2
import inspect
import time
from multiprocessing import Queue

from dotenv import load_dotenv
import logging

from shmc_sqlAccess import SQL_interface as SQLi
from shmc_sqlBases.sql_baseMeasurement import Measurement as sqlMeasurement

# LOGGING                                                                                   logging - START -
lg = logging.getLogger()
# LOGGING                                                                                   logging - ENDED -

load_dotenv()


class EngineMessageHandler:
    """=== Class name: EngineMessageHandler ============================================================================
    Class controlling communication between API and Engine.
    ============================================================================================== by Sziller ==="""
    ccn = inspect.currentframe().f_code.co_name  # current class name

    def __init__(self,
                 queue_in: (Queue, None) = None,
                 hcdd: (dict, None) = None,
                 **kwargs):
        lg.info("INIT : {:>85} <<<".format(self.ccn))
        # setting Hard Coded Default Data and updating IF incoming argument can be used.
        # Use this section to define Hard Coded information to enable you to later modify these.
        # NOTE: this data CANNOT be modified at runtime.
        self.hcdd_default = {"err_msg_path": "./"}
        if hcdd:  # if <hcdd> update is entered...
            self.hcdd_default.update(hcdd)  # updated the INSTANCE stored default!!!
        self.hcdd = self.hcdd_default
        self.queue = queue_in
        self.go()

    def go(self):
        """=== Method name: go =========================================================================================
        ========================================================================================== by Sziller ==="""
        lg.debug("loopstart: go()")
        while True:
            time.sleep(5)
            lg.info("process   : message handler")
