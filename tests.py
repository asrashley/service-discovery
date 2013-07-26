import unittest, datetime

from google.appengine.api import memcache
from google.appengine.ext import ndb
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
        le = models.LogEntry(ev='start', ts=from_isodatetime(date_str))
        self.assertEqual(le.ts.year, 2013)
        self.assertEqual(le.ts.month, 7)
        self.assertEqual(le.ts.day, 25)
        d = le.as_dict()
        self.assertEqual(d['ts'],date_str)
        self.assertEqual(d['ev'],le.ev)
        extra={"dhcp": {
            "dns2": "172.20.0.106",
            "dns1": "172.20.0.102",
            "gatewayIP": "172.20.0.1",
            "gatewayMAC": "00:90:0b:25:6c:f6",
            "netmask": "255.255.248.0",
            "address": "172.20.4.42"
        },
        "client": {
            "uid": "af290300-bef5-4bfd-838c-e05c3c99f73e"
        },
        "wifi": {
            "ip": "172.20.4.42",
            "mac": "60:a4:4c:91:a5:c3",
            "bssid": "02:e6:fe:91:a5:c3"
        }}
        ev = models.EventLog(uid='8c9cdea2-5528-4579-a9e1-9abe1bcf5e72',
                      date=from_isodatetime("2013-07-25T09:57:31Z"),
                      client=False,
                      name="Test device",
                      loc=ndb.GeoPt(51.52,0.11),
                      city= "London",
                      addr='172.20.4.42',
                      entries=[le],
                      extra=extra)
        d=ev.as_dict()
        for field in ['uid','date','client','name','city']:
            value = getattr(ev,field)
            if isinstance(value,datetime.datetime):
                value = value.isoformat()
            self.assertEqual(value,d[field])
        self.assertEqual(d['publicAddress'],ev.addr)
        self.assertEqual(d['location']['lat'],ev.loc.lat)
        self.assertEqual(d['location']['lon'],ev.loc.lon)
        
    def test_sort(self):
        entries = [ models.LogEntry(ev='start', ts=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(ev='end', ts=from_isodatetime("2013-07-25T09:57:44Z")),
                   models.LogEntry(ev='upnp', ts=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(ev='cloud', ts=from_isodatetime("2013-07-25T09:57:31Z")),
                   models.LogEntry(ev='zeroconf', ts=from_isodatetime("2013-07-25T09:57:43Z")),
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
                self.assertGreaterEqual(e.ts, tc)
            tc = e.ts
        
if __name__ == '__main__':
    unittest.main()        