import pika
import redis
import yaml
import sys
import os
from time import sleep
import _thread
import pytest
import random
import logging

sys.path.insert(0, '../iip')
#sys.path.append('/home/fedora/src/git/ctrl_iip/python/lsst/iip')
from const import *
import toolsmod
from toolsmod import L1Exception
from toolsmod import L1MessageError
from toolsmod import get_timestamp
from BaseForeman import *
from Scoreboard import Scoreboard
from ForwarderScoreboard import ForwarderScoreboard
from JobScoreboard import JobScoreboard
from AckScoreboard import AckScoreboard
from Consumer import Consumer
from SimplePublisher import SimplePublisher

"""
 Creates BaseForeman object used to test the methods below
 Can either last for the entire testing session or per test one can be created

This test file requires the use of two external fixtures:
1) An AMQP message broker
2) The Redis in-memory database

The BaseForeman class s built to receive parameters froma configuration file.
If an init arg is not given when creating a BaseForeman, the default
ForemanCFG.yaml is used...but it is also possible to create a BaseForeman
instance with a specific config file given as the arg - in this case, we will
use a file called ForemanCFGTest.yaml. This file contains the user/passwd
information for access to the message broker, and also gives explicit info
about the Forwarders that this file will use as well.

"""

@pytest.fixture(scope='session')
def bf(request):
    return BaseForeman('ForemanCfgTest.yaml')


logging.basicConfig(filename='logs/BaseForeman.log', level=logging.INFO, format=LOG_FORMAT)

class TestInsufficientBaseResources:
    DMCS_PUBLISH = "dmcs_publish"
    DMCS_CONSUME = "dmcs_consume"
    NCSA_PUBLISH = "ncsa_publish"
    NCSA_CONSUME = "ncsa_consume"
    FORWARDER_PUBLISH = "forwarder_publish"
    F_CONSUME = "f_consume"
    ACK_PUBLISH = "ack_publish"
    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'direct'
    PUB = None
    ACK_REPLACEMENT = "11_BB"
    CDM = None
    FORMAT = None
    test_broker_url = None
    next_integer = 0

    def setup_publisher(self):
        self.PUB = SimplePublisher(self.test_broker_url)

    def get_next_integer(self):
        self.next_integer = self.next_integer + 2
        return self.next_integer

    def on_insufficient_base_message(self, ch, method, properties, body):
        msg_dict = body
        fail_dict = msg_dict['FAIL_DETAILS']
        timed_ack = msg_dict["ACK_ID"]
        job_num = msg_dict['JOB_NUM']
        msg_params = {}
        msg_params['MSG_TYPE'] = 'NEW_JOB_ACK'
        msg_params['JOB_NUM'] = job_num
        msg_params['ACK_BOOL'] = False 
        msg_params['ACK_ID'] = self.ACK_REPLACEMENT
        msg_params['COMPONENT_NAME'] = 'BASE' 
        msg_params['FAIL_DETAILS'] = fail_dict
        self.PUB.publish_message("ack_publish", msg_params)

    def run_consumer(self, threadname, delay, adict):
        callback = adict['cb']
        adict['csume'].run(callback)


    def setup_consumer(self, test_broker_url, Q, format, callback):
        consumer = Consumer(test_broker_url, Q, format)
        try:
            _thread.start_new_thread( self.run_consumer, ("thread-test-consume", 2, {'csume': consumer, 'cb': callback}))
        except:
            print("Bad trouble creating consumer thread for testing...exiting...")
            sys.exit(101)

    def purge_queues(self, queues):
        for q in queues:
            cmd = "rabbitmqctl -p /tester purge_queue " + q
            os.system(cmd)

    def test_forwarder_check_health(self, bf):
        time.sleep(4)
        #os.system('rabbitmqctl -p /tester purge_queue f_consume')
        #os.system('rabbitmqctl -p /tester purge_queue forwarder_publish')
        #os.system('rabbitmqctl -p /tester purge_queue ack_publish')
        #os.system('rabbitmqctl -p /tester purge_queue dmcs_consume')
        try:
           f = open('ForemanCfgTest.yaml')
        except IOError:
            print("Can't open ForemanCfgTest.yaml")
            print("Bailing out on test_forwarder_check_health...")
            sys.exit(99)

        self.CDM = yaml.safe_load(f)
        #self.purge_queues(self.CDM['ROOT']['QUEUE_PURGES'])
        number_of_pairs = self.CDM['ROOT']['NUMBER_OF_PAIRS']
        test_broker_address = self.CDM['ROOT']['TEST_BROKER_ADDR']
        name = self.CDM['ROOT']['TEST_BROKER_NAME']
        passwd = self.CDM['ROOT']['TEST_BROKER_PASSWD']
        self.base_format = None
        self.ncsa_format = None
        if 'BASE_MSG_FORMAT' in self.CDM[ROOT]:
            self.base_format = self.CDM[ROOT][BASE_MSG_FORMAT]
        if 'NCSA_MSG_FORMAT' in self.CDM[ROOT]:
            self.ncsa_format = self.CDM[ROOT][NCSA_MSG_FORMAT]

        self.test_broker_url = "amqp://" + name + ":" + passwd + "@" + str(test_broker_address)
        self.setup_publisher()
        self.setup_consumer(self.test_broker_url, 'dmcs_consume', self.base_format, self.on_insufficient_base_message )
        forwarders = list(self.CDM['ROOT']['XFER_COMPONENTS']['FORWARDERS'].keys())
        needed_forwarders = 4
        available_forwarders = 3
        L = []
        fwders = []
        for i in range (0, needed_forwarders):
           L.append(self.CDM['ROOT']['RAFT_LIST'][i]) 
        for i in range (0, available_forwarders):
           fwders.append(forwarders[i]) 

        this_job_num = '1562'

        params = {}
        params['MSG_TYPE'] = 'NEW_JOB'
        params['JOB_NUM'] = this_job_num
        params['ACK_ID'] = self.ACK_REPLACEMENT
        params['RAFTS'] = L

        bf.insufficient_base_resources(params, fwders)
        sleep(3)

        ack_responses = bf.ACK_SCBD.get_components_for_timed_ack(self.ACK_REPLACEMENT)

        assert len(ack_responses) == 1
        assert ack_responses['BASE']['JOB_NUM'] == this_job_num
        assert 'FAIL_DETAILS' in ack_responses['BASE'] 
        print("Done with insufficient_base_resources test")



