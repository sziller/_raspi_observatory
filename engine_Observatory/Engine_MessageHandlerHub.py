"""=== Message handler =========================================================
Process to manage communication between Server API and Engine.
============================================================== by Sziller ==="""

import time
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
    API sends requests over a socket
    ============================================================================================== by Sziller ==="""
    ccn = inspect.currentframe().f_code.co_name  # current class name

    def __init__(self,
                 zmq_port: int,
                 queue_hub_to_eng: Queue,
                 queue_eng_to_hub: Queue = None,
                 hcdd: dict or None      = None,
                 **kwargs):
        lg.info("INIT : {:>85} <<<".format(self.ccn))
        # setting Hard Coded Default Data and updating IF incoming argument can be used.
        # Use this section to define Hard Coded information to enable you to later modify these.
        # NOTE: this data CANNOT be modified at runtime.
        self.zmq_port: int          = zmq_port
        self.hcdd_default           = {"timeout": 5,
                                       "cpu_delay": 0.01,
                                       "err_msg_path": "./"}
        if hcdd:  # if <hcdd> update is entered...
            self.hcdd_default.update(hcdd)  # updated the INSTANCE stored default!!!
        self.hcdd = self.hcdd_default
    
        # Establish ZMQ socket                                                              -   START   -
        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:{}".format(self.zmq_port))
        # Establish ZMQ socket                                                              -   ENDED   -

        # Queue management                                                                  -   START   -
        self.queue_hub_to_eng = queue_hub_to_eng
        self.queue_eng_to_hub = queue_eng_to_hub
        # Queue management                                                                  -   START   -
        
        self.listen()

    def listen(self):
        """=== Method name: listen =====================================================================================
        Continuously listens for incoming messages on the socket and processes them.
        Method runs an infinite loop that waits for messages from the router via the socket.
        Upon receiving a message, it forwards the message to the engine queue for processing.
        If msg requires sync., it waits for a response from the engine and forwards the response back through socket.
        This is done by method < handle_synced_message() >.
        If msg is not synced: fire-and-forget behaviour is e
        ========================================================================================== by Sziller ==="""
        while True:
            lg.debug("new loop  : listen() - to socket still active after recent message")
            # Awaiting new message from Router: (ATTENTION: line interrupts program flow!)
            try:
                msg_hub_to_eng: msg.InternalMsg           = self.socket.recv_pyobj()
                # Validate the type of the received message
                if not isinstance(msg_hub_to_eng, msg.InternalMsg):
                    lg.error("Received message of invalid type: {}".format(type(msg_hub_to_eng)))
                    continue  # Continue to the next iteration of the loop: start over at --> "while True"
            except Exception as e:
                lg.error("Error receiving message from socket:\n {}".format(e))
                continue  # Continue to the next iteration of the loop: start over at --> "while True"
                
            # New message arrived:
            lg.info("received  : message from API over socket: {}".format(msg_hub_to_eng.payload))
            
            # Process the message:
            # - forward message into Queue
            self.queue_hub_to_eng.put(msg_hub_to_eng)
            lg.debug("put       : message into Queue for Engine: {}".format(msg_hub_to_eng.payload))
            # - read msg-sync mode:
            if msg_hub_to_eng.synced:  # request-response mode
                msg_eng_to_hub = self.handle_synced_message(msg_hub_to_eng=msg_hub_to_eng)
            else:  # fire and forget mode
                msg_eng_to_hub = msg.ExternalResponseMsg(payload=msg_hub_to_eng.payload,
                                                         message="request being processed",
                                                         timestamp=msg_hub_to_eng.timestamp)
            try:
                # Attempt to send the response back through the socket
                self.socket.send_pyobj(msg_eng_to_hub)
                lg.debug("sent      : response to API over socket: {}".format(msg_eng_to_hub.payload))
            except Exception as e:
                # If an error occurs while sending, log it
                lg.error("Error sending response to socket:\n {}".format(e))

    def handle_synced_message(self, msg_hub_to_eng):
        """=== Method name: handle_synced_message ======================================================================
        Handles synchronized messages by waiting for a response from the engine.
        Method processes a synchronized message by putting it into the engine queue and waiting for a response.
        It waits for a specified timeout period, continuously checking the engine queue for a response with a matching
        timestamp. If a matching response is found within the timeout period, it returns the response. If no matching
        response is received before the timeout, it returns a timeout message.
        :param msg_hub_to_eng: msg.InternalMsg - Message received from the router that requires synchronization.
        :returns: msg.ExternalResponseMsg - The response message from the engine or a timeout message.
        ========================================================================================= by Sziller ==="""
        # default message on timeout:
        msg_eng_to_hub = msg.ExternalResponseMsg(payload=msg_hub_to_eng.payload,
                                                 message="timed out",
                                                 timestamp=msg_hub_to_eng.timestamp)
        timeout_at = time.time() + self.hcdd["timeout"]
        resp_received = False
        while (not resp_received) and (time.time() < timeout_at):  # checking until valid response of timed-out
            if not self.queue_eng_to_hub.empty():  # if queue in not empty...
                msg_read = self.queue_eng_to_hub.get()
                if msg_read.timestamp == msg_hub_to_eng.timestamp:
                    msg_eng_to_hub = msg_read
                    resp_received = True
            else:  # if queue empty
                time.sleep(self.hcdd["cpu_delay"])  # Sleep to reduce CPU usage
        return msg_eng_to_hub
