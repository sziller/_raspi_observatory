

import logging
import inspect
import zmq
from multiprocessing import Queue
from shmc_messages import msg


# LOGGING                                                                                   logging - START -
lg = logging.getLogger()
# LOGGING                                                                                   logging - ENDED -


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

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:52902")
        
        self.queue = queue_in
        self.go()

    def go(self):
        """=== Method name: go =========================================================================================
        ========================================================================================== by Sziller ==="""
        while True:
            lg.debug("loopstart: go()")
            msg_router_to_engine: msg.InternalMsg           = self.socket.recv_pyobj()
            print("Received message from API: {}".format(msg_router_to_engine.payload))
            # Process the message
            msg_engine_to_router = msg.ExternalResponseMsg(payload=None,
                                                           message="request being processed",
                                                           timestamp=msg_router_to_engine.timestamp)
            self.socket.send_pyobj(msg_engine_to_router)

            self.queue.put(msg_router_to_engine)
