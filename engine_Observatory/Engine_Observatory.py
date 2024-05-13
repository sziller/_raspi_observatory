"""=== Observatory engine ======================================================
Working horse of the main usecase. Daemon-like engine running in the
background, responsible for business logic and complex tasks
============================================================== by Sziller ==="""

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


class EngineObservatory:
    """=== Class name: EngineObservatory ===============================================================================
    An object to be instantiated to controll the Observatory.
    This is an Engine responsible for tasks such as:
    - taking pictures
    ============================================================================================== by Sziller ==="""
    ccn = inspect.currentframe().f_code.co_name  # current class name
    
    def __init__(self,
                 schedule: list,
                 queue_server_to_engine: (Queue, None)    = None,
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
            "heartbeat": 0.1,
            "delta_t_h": 0,
            "delta_t_m": 0,  # TB-R: _dict is appropriate name
            "err_msg_path": "./"}
        if hcdd:  # if <hcdd> update is entered...
            self.hcdd_default.update(hcdd)  # updated the INSTANCE stored default!!!
        self.hcdd = self.hcdd_default
        self.queue_request = queue_server_to_engine
        
        # Create a PiCamera object
        self.camera = Picamera2()
        self.cam_conf = self.camera.create_preview_configuration()
        self.camera.configure(self.cam_conf)
        self.camera.start()

        self.actual_request                 = None
        
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

        self.took_n_queued_last_loop: int        = 0
        
        self.go()

    def go(self):
        """=== Method name: go =========================================================================================
        ========================================================================================== by Sziller ==="""
        lg.info("loop start: go() - says {} at {}".format(self.ccn, os.path.basename(__file__)))
        self.took_n_queued_last_loop = 0
        while True:
            # check and empty directcall containing queue                               - START -
            self.pop_last_entry_from_queue_in()  # Engine pops last object put into Queue.
            if self.took_n_queued_last_loop:
                self.process_actual_request()
            # check and empty directcall containing queue                               - ENDED -
            time.sleep(self.hcdd["heartbeat"])
            
    def pop_last_entry_from_queue_in(self):
        """=== Method name: pop_last_entry_from_queue_in =========================================
        Suggesting self.queue_request to include data, method takes last member.
        Last member is:
        - stored under self.actual_request
        - deleted from queue_in
        If self.queue_request is empty on call, nothig happens, method passes.
        ___________ (by Instance we refer to the Instance of THIS very Class: DareEngine) ________________________________
        :var self.actual_request - dict      : the dict storing the actual <directcall> - updatable loop by loop.
                                                  This variable might be MODIFIED
        :var self.queue_request - queue  : queue to pass data TO Instance. (from whatever source e.g.: UI
                                                  This variable is READ (checked)
        :return nothing
        """
        cmn = inspect.currentframe().f_code.co_name  # current method name
        self.took_n_queued_last_loop = 0
        if not self.queue_request.empty():  # only if Queue is not empty... having at least 1 element.
            lg.info("QUEUE--in - <self.queue_request>: {} sees   {:>3} object.".format(cmn, self.queue_request.qsize()))
            lg.info("QUEUE--in - <self.queue_request>: {} POPPING...".format(cmn))
            self.actual_request = self.queue_request.get()  # <self.actual_request> takes first incoming obj
            lg.info("QUEUE--in - <self.queue_request>: {} popped {:>3} object.".format(cmn, 1))
            lg.info("QUEUE--in - <self.queue_request>: {} sees   {:>3} object.".format(cmn, self.queue_request.qsize()))
            self.took_n_queued_last_loop = 1
        pass

    def process_actual_request(self):
        """=== Method name: process_actual_request =====================================================================
        Method is responsible for all non-scheduled processes to be run.
        ========================================================================================== by Sziller ==="""
        cmn = inspect.currentframe().f_code.co_name  # current method name
        if self.actual_request is not None:
            command = self.actual_request.command
            id_timestamp = self.actual_request.timestamp
            lg.info("Framework : {} - executing process:".format(cmn))
            lg.info("COMMAND   : {:>76} <<<".format(command))
            for k, v in self.actual_request.as_dict().items():
                lg.debug("{:>10}: {}".format(k, v))
            lg.info("Timestamp of   REQUEST: {:>60}".format(id_timestamp))
            actual_command = getattr(self, command)
            actual_command(**self.actual_request.as_dict)
            # self.actual_response = None
            # self.actual_response = msg.EngineToHub(timestamp=id_timestamp, payload={}, message="")  # message must be ""
            # actual_process_data = self.command_assignment.get(command)
            # if actual_process_data is not None:
            #     actual_processcall = actual_process_data["method"]
            #     actual_kwargs = self.command_assignment[command]["kw"]
                # ------------------------------------------------------------------------------------------
                # - to be revised ...                                                       ERROR HANDLING -
                # ------------------------------------------------------------------------------------------
                # try:
                #     successfull_run: bool = actual_processcall(**actual_kwargs)
                # except:
                #     error_code = 102
                #     fill_in = {"err": error_code, "cmd": command, "adm": cmn, "fn": FN}
                #     lg.critical("FAILED actual processcall! - {err:>3}".format(**fill_in))
                #     self.actual_response.payload = "ERR {err:>3}".format(**fill_in)
                #     self.actual_response.message = ERROR[error_code][LNG].format(**fill_in)
                # ------------------------------------------------------------------------------------------
                # - to be revised ...                                                       ERROR HANDLING -
                # ------------------------------------------------------------------------------------------
            # else:
            #     error_code = 101
            #     fill_in = {"err": error_code, "cmd": command, "adm": cmn, "fn": FN,
            #                "data01": self.actual_response.timestamp}
            #     lg.warning("{data01} received unknown command: '{cmd}'! - {err:>3}".format(**fill_in))
            #     self.actual_response.payload = "ERR {err:>3}".format(**fill_in)
            #     self.actual_response.message = ERROR[error_code][LNG].format(**fill_in)
            # lg.info("QUEUE-out - <self.queue_response>: {} sees {:>3} object.".format(cmn, self.queue_response.qsize()))
            # lg.info("QUEUE-out - <self.queue_response>: {} PUTTING...".format(cmn))
            # self.queue_response.put(self.actual_response)
            # lg.info("QUEUE-out - <self.queue_response>: {} put  {:>3} object.".format(cmn, 1))
            # lg.info("QUEUE-out - <self.queue_response>: {} sees {:>3} object.".format(cmn, self.queue_response.qsize()))
            # 
            # lg.info("Timestamp as RESPONDED: {:>60}".format(self.actual_response.timestamp))
        else:
            lg.critical("bad logic : no request detected, still in processing mode! - says {} at {}"
                        .format(self.ccn, os.path.basename(__file__)))
        # And tha most important line in the entire UNIVERSE:
        # FCKNG crucial - you don't do that, Engine will repeat task in current second as amy times it can!!!!
        # self.actual_response = None
        self.actual_request = None

    def GET_photo(self, **kwargs):
        """=== Method name: GET_photo ==================================================================================
        ========================================================================================== by Sziller ==="""
        if kwargs:
            timestamp = "{}-".format(kwargs["timestamp"])
        else:
            timestamp = ""
        if not self.finite_looping:
            current_loop_count = 0
        else:
            current_loop_count = 1
        time.sleep(2) # Add a delay to let the camera adjust to light levels
        while current_loop_count <= self.finite_looping:
            lg.info("{:>4}/{:>4}".format(current_loop_count, self.finite_looping))
            # Start the preview (optional)
            # self.camera.start_preview(Preview.QTGL)
            current_filename = './{}photo_{}.jpg'.format(timestamp, current_loop_count)
            # Capture an image
            self.camera.capture_file(current_filename)
            lg.debug("photo     : TAKEN and saved as {}".format(current_filename))

            # # Stop the preview
            # self.camera.stop_preview()

            time.sleep(self.hcdd["heartbeat"])
            if self.finite_looping: current_loop_count += 1
        lg.info("photoloop : ")
        # Release the camera resources
        self.camera.close()
        
