import os
from picamera2 import Picamera2, Preview
import inspect
import time

from dotenv import load_dotenv
import logging

from shmc_sqlAccess import SQL_interface as SQLi
from shmc_sqlBases.sql_baseMeasurement import Measurement as sqlMeasurement

# LOGGING                                                                                   logging - START -
lg = logging.getLogger()
# LOGGING                                                                                   logging - ENDED -

load_dotenv()


class EngineObservatory:
    """=== Class name: EngineObservatory ===============================================================================
    An object to be instantiated to controll the Observatory 
    By Room we refer to any built or naturarly originated closed area, space.
    ============================================================================================== by Sziller ==="""
    ccn = inspect.currentframe().f_code.co_name  # current class name
    
    def __init__(self,
                 schedule: list,
                 finite_looping: int        = 20,
                 session_name: str          = "",
                 session_style: str         = "SQLite",
                 room_id: str               = "room_01",
                 time_shift: (dict, bool)   = False,
                 low_light: bool            = True,
                 rotation: int              = 180,
                 hcdd: (dict, None)         = None,
                 **kwargs):
        lg.info("INIT : {:>85} <<<".format(self.ccn))
        # setting Hard Coded Default Data and updating IF incoming argument can be used.
        # Use this section to define Hard Coded information to enable you to later modify these.
        # NOTE: this data CANNOT be modified at runtime.
        self.hcdd_default = {
            "heartbeat": 20,
            "delta_t_h": 0,
            "delta_t_m": 0,  # TB-R: _dict is appropriate name
            "err_msg_path": "./"}
        if hcdd:  # if <hcdd> update is entered...
            self.hcdd_default.update(hcdd)  # updated the INSTANCE stored default!!!
        self.hcdd = self.hcdd_default

        # Create a PiCamera object
        self.camera = Picamera2()
        self.cam_conf = self.camera.create_preview_configuration()
        # self.camera.configure(self.cam_conf)
        
        self.room_id: str                   = room_id
        self.finite_looping: int            = finite_looping  # 1- any int: actual int;
        self.low_light: bool                = low_light
        self.rotation: int                  = rotation
        if not session_name:
            self.session_name = '.' + self.room_id + '.db'
        else: self.session_name = session_name
        self.session_style = session_style
        self.session = SQLi.createSession(db_fullname=self.session_name,
                                          tables=[sqlMeasurement.__table__],
                                          style=self.session_style)
        if not time_shift:
            self.time_shift = {'delta_t_h': -1, 'delta_t_m': 0}
        else:
            self.time_shift = time_shift
        self.schedule = schedule
        
        self.go()

    def go(self):
        """=== Method name: go =========================================================================================
        ========================================================================================== by Sziller ==="""
        if not self.finite_looping:
            current_loop_count = 0
        else:
            current_loop_count = 1
        while current_loop_count <= self.finite_looping:
            lg.info("{:>4}/{:>4}".format(current_loop_count, self.finite_looping))
            # Start the preview (optional)
            # self.camera.start_preview(Preview.QTGL)
            self.camera.start()
            # Add a delay to let the camera adjust to light levels
            time.sleep(2)

            # Capture an image
            self.camera.capture_file('image_{}.jpg'.format(current_loop_count))

            # Stop the preview
            self.camera.stop_preview()

            # Release the camera resources
            self.camera.close()
            time.sleep(10)
            if self.finite_looping: current_loop_count += 1

