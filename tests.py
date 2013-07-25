import unittest, datetime

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

import models
from views import from_isodatetime

class GAETestCase(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_blobstore_stub
        self.testbed.init_taskqueue_stub()
        self.testbed.init_channel_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        
    def tearDown(self):
        self.testbed.deactivate()    

class DateTimeTests(unittest.TestCase):
    def test_isoformat(self):
        date_str = "2013-07-25T09:57:31Z"
        date_val = from_isodatetime(date_str)
        self.assertEqual(date_val.year,2013)
        self.assertEqual(date_val.month, 7)
        self.assertEqual(date_val.day, 25)
        self.assertEqual(date_val.hour, 9)
        self.assertEqual(date_val.minute, 57)
        self.assertEqual(date_val.second, 31)
        # Don't check for the 'Z' because Python doesn't put the timezone in the isoformat string
        self.assertEqual(date_val.isoformat(),date_str[:-1])
        date_str = "2013-07-25T09:57:31.123Z"
        date_val = from_isodatetime(date_str)
        self.assertEqual(date_val.microsecond, 123000)
        # Don't check for the 'Z' because Python doesn't put the timezone in the isoformat string
        self.assertTrue(date_val.isoformat().startswith(date_str[:-1]))
        
class TestEventLog(GAETestCase):
    def test_as_dict(self):
        date_str = "2013-07-25T09:57:31Z"
        le = models.LogEntry(event='start', timestamp=from_isodatetime(date_str))
        self.assertEqual(le.timestamp.year, 2013)
        self.assertEqual(le.timestamp.month, 7)
        self.assertEqual(le.timestamp.day, 25)
        d = le.as_dict()
        self.assertEqual(d['ts'],date_str)
        self.assertEqual(d['ev'],le.event)
                             
    def test_sort(self):
        entries = [ models.LogEntry(event='start', timestamp=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(event='end', timestamp=from_isodatetime("2013-07-25T09:57:44Z")),
                   models.LogEntry(event='upnp', timestamp=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(event='cloud', timestamp=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(event='zeroconf', timestamp=from_isodatetime("2013-07-25T09:57:43Z")),
                   ]
        
        self.assertLess(entries[0], entries[1])
        log = models.EventLog(
                              uid='8c9cdea2-5528-4579-a9e1-9abe1bcf5e72',
                              date=datetime.datetime(2013,7,25),
                              addr='172.20.4.42',
                              entries=entries
                              )
        log.sort_entries()
        tc = None
        #print log.entries
        for e in log.entries:
            if tc is not None:
                self.assertGreaterEqual(e.timestamp, tc)
            tc = e.timestamp
        
if __name__ == '__main__':
    unittest.main()        