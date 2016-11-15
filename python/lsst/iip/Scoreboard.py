import toolsmod
import time
import redis
from SimplePublisher import SimplePublisher
import sys
import yaml
import logging
import os

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

class Scoreboard:
    """This is the parent class of the three scoreboard classes. 
       It, and they, form an interface for the Redis in-memory DB
       that continually stores state information about components and jobs.
    """

    AUDIT_QUEUE = 'audit_consume'
    SCBDS = None
    SCOREBOARD_TYPE = None

    def __init__(self, scoreboard_type, file=None):
        print "The scoreboard arg is "
        print scoreboard_type
        print "Done printing scoreboard arg is "
        if file == None:
            file = 'ForemanCfgTest.yaml'
        try:
            f = open(file)
        except IOError:
            print "Can't open %s" % file
            raise L1Error

        self.cdm = yaml.safe_load(f)
        scbds = self.cdm['ROOT']['SCOREBOARDS']
        keez = scbds.keys()
        for k in keez:
            if scbds[k] == scoreboard_type:
                self.SCOREBOARD_TYPE = k
                break

#        self.SCOREBOARD_TYPE = (key for key, value in self.SCBDS.iteritems() if value == scoreboard_type)
        print "Printing value of self.SCOREBOARD_TYPE"
        print self.SCOREBOARD_TYPE
        print "Done printing value of self.SCOREBOARD_TYPE"
        broker_address = self.cdm['ROOT']['BASE_BROKER_ADDR']
        name = self.cdm['ROOT']['BASE_BROKER_NAME']
        passwd = self.cdm['ROOT']['BASE_BROKER_PASSWD']
        self.broker_url = "amqp://" + name + ":" + passwd + "@" + str(broker_address)

        self.audit_format = "YAML"
        if 'AUDIT_MSG_FORMAT' in self.cdm['ROOT']:
            self.audit_format = self.cdm['ROOT']['AUDIT_MSG_FORMAT']

        try:
            self.audit_publisher = SimplePublisher(self.broker_url, self.audit_format)
        except L1RabbitConnectionError as e:
            LOGGER.error("Scoreboard Parent Class cannot create SimplePublisher:  ", e.arg)
            print "No Publisher for YOU"
            raise L1Error('Cant create SimplePublisher'. e.arg)


    def persist(self, data):
        params = {}
        params['DATA_TYPE'] = self.SCOREBOARD_TYPE
        keez = data.keys()
        for k in keez:
            params[k] = data[k]
        self.audit_publisher.publish_message(self.AUDIT_QUEUE, params)


    def persist_snapshot(self, connection, filename):
        pass
        """
        LOGGER.info('Saving Scoreboard Snapshot')
        rdb = filename + ".rdb" 
        self._redis.config_set("dbfilename", rdb)
        while True: 
            try: 
                self._redis.bgsave()
                break
            except: 
                print("Waiting for preceding persistence to complete.")
                time.sleep(10) 


        while True: 
            if rdb in os.listdir(os.getcwd()): 
                os.rename(rdb, filename + "_" +  str(self._redis.lastsave()) + ".rdb")
                break
            else:
                print("Waiting for current persistence to complete.")
                time.sleep(10)
        """ 










