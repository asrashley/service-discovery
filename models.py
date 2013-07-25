import logging, datetime, math, functools

from google.appengine.ext import ndb
from google.appengine.api import search

def delete_all_in_index(index_name):
    """Delete all the docs in the given index."""
    doc_index = search.Index(name=index_name)

    while True:
        document_ids = [document.doc_id for document in doc_index.get_range(ids_only=True)]
        if not document_ids:
            break
        doc_index.delete(document_ids)
        
class NetworkService(ndb.Model):
    """representation of one IANA registered service"""
    INDEX_NAME='services'
    PROTOCOLS = ['tcp','udp','sctp','dccp']
    NAME_MAPPING = {
                    'nm':'name', 'pt':'port', 'dc':'description', 'pr':'protocol',
                    'as':'assignee', 'ct':'contact','md':'modification'
                    }
    name = ndb.StringProperty('nm',required=True, indexed=True, verbose_name='Name')
    port = ndb.IntegerProperty('pt',indexed=True, required=False, verbose_name='Port')
    description = ndb.StringProperty('dc',indexed=False, required=True, verbose_name='Description')
    protocol = ndb.StringProperty('pr', indexed=False, choices=PROTOCOLS, required=False, default='tcp', verbose_name='Protocol')
    assignee = ndb.StringProperty('as',indexed=False, required=True, verbose_name='Assignee')
    contact = ndb.StringProperty('ct',indexed=False, required=True, verbose_name='Contact')
    #registration = ndb.DateProperty('rd', indexed=False, required=False, verbose_name='Registration Date')
    modification = ndb.DateProperty('md', indexed=False, required=False, verbose_name='Modification Date')
    #reference = ndb.StringProperty('rf', indexed=False, required=False, verbose_name='Reference')
    
    @classmethod
    def empty_database(clz):
        delete_all_in_index(clz.INDEX_NAME)
        list_of_keys = NetworkService.query().fetch(keys_only=True)
        ndb.delete_multi(list_of_keys)
        
    def create_search_document(self):
        """create a search Document from an instance of this model"""
        fields=[search.AtomField(name='name', value=self.name),
                search.TextField(name='description', value=self.description),
                search.AtomField(name='protocol', value=self.protocol),
                ]
        if self.port:
            fields.append(search.NumberField(name='port', value=self.port))
        return search.Document(doc_id=self.key.string_id(), fields=fields)
                
    def put(self,*args,**kwargs):
        rv = super(NetworkService,self).put(*args,**kwargs)
        try:
            search.Index(name=self.INDEX_NAME).put(self.create_search_document())
        except search.Error:
            logging.exception('Index put failed')
        return rv
    
class ServiceLocation(ndb.Model):
    """representation of the location of a device"""
    uid = ndb.StringProperty(required=True, indexed=True, verbose_name="UID")
    #name = ndb.StringProperty('nm',required=True, indexed=False)
    #country = ndb.StringProperty('co',required=True, indexed=True, verbose_name="Country")
    #location = ndb.GeoPtProperty('ln',indexed=False,required=False, verbose_name="Location")
    public_address = ndb.StringProperty('pa',indexed=True, required=True, verbose_name="Public IP address")
    internal_addresses = ndb.StringProperty('ia',indexed=False,required=True, verbose_name="Internal IP addresses")
    port = ndb.IntegerProperty('pt',indexed=False,required=True, verbose_name="Port")
    path = ndb.StringProperty('ph',indexed=False,required=False, verbose_name="Path")
    last_update = ndb.DateTimeProperty('ts',indexed=True,auto_now=True, verbose_name="Last update")
    
class ApiAuthorisation(ndb.Model):
    """database of all authorisation data"""
    apikey = ndb.StringProperty('a',indexed=True, required=True, verbose_name='API key')
    secret = ndb.StringProperty('s',indexed=False, required=True, verbose_name='API secret')
    user = ndb.UserProperty('u',indexed=True, verbose_name='User')
    service = ndb.StringProperty('v', verbose_name='Service',indexed=False, required=False)
    country = ndb.StringProperty('c',required=True, indexed=True, verbose_name='Country')
    description = ndb.StringProperty('d',indexed=False, verbose_name='Description')
    created = ndb.DateTimeProperty('n',auto_now_add=True,indexed=False)
    last_update = ndb.DateTimeProperty('l',auto_now=True,indexed=False)
    
@functools.total_ordering
class LogEntry(ndb.Model):
    EVENT_TYPES = ['start','zeroconf','upnp','cloud','end']
    event = ndb.StringProperty('ev',required=True, choices=EVENT_TYPES, verbose_name="Event type")
    timestamp = ndb.DateTimeProperty('ts', required=True, verbose_name="Timestamp")
    
    def as_dict(self):
        ts = self.timestamp.isoformat()
        if not self.timestamp.utcoffset():
            ts += 'Z'
        return {"ev":self.event, "ts":ts}
    
    def __hash__(self):
        return self.timestamp.__hash__() ^ self.EVENT_TYPES.index(self.event)
    
    def __eq__(self, other):
        if isinstance(other,LogEntry):
            return self.timestamp==other.timestamp and self.event==other.event
        return NotImplemented
    
    def __lt__(self,other):
        if not isinstance(other,LogEntry):
            return NotImplemented
        delta = self.timestamp - other.timestamp
        #print self.timestamp,other.timestamp,delta
        if delta.days<0 or delta.seconds<0 or delta.microseconds<0:
            return True
        if delta.days==0 and delta.seconds==0 and delta.microseconds==0:
            return self.EVENT_TYPES.index(self.event) < self.EVENT_TYPES.index(other.event)
        return False

    def __le__(self,other):
        if not isinstance(other,LogEntry):
            return NotImplemented
        delta = self.timestamp - other.timestamp
        if delta.days<0 or delta.seconds<0 or delta.microseconds<0:
            return True
        if delta.days==0 and delta.seconds==0 and delta.microseconds==0:
            return EVENT_TYPES.index(self.event) <= EVENT_TYPES.index(other.event)
        return False
        
        
    #def __cmp__(self,other):
    #    if other is None:
    #        return 1
    #    delta = self.timestamp - other.timestamp
    #    if delta.days==0 and delta.seconds==0:
    #        if delta.microseconds==0:
    #            return EVENT_TYPES.index(self.event) - EVENT_TYPES.index(other.event)
    #        return delta.microseconds
    #    return int(delta.total_seconds())

class EventLog(ndb.Model):
    uid = ndb.StringProperty(required=True, indexed=True)
    date = ndb.DateProperty(required=True, indexed=True)
    client = ndb.BooleanProperty(default=False, indexed=False)
    name = ndb.StringProperty(required=False, indexed=False)
    loc = ndb.GeoPtProperty(indexed=False,required=False, verbose_name="Location")
    city = ndb.StringProperty(indexed=False, required=False, verbose_name="City")
    addr = ndb.StringProperty(indexed=False, required=True, verbose_name="Public IP address")
    entries = ndb.LocalStructuredProperty(LogEntry, repeated=True)
    extra = ndb.JsonProperty(required=False, indexed=False)
    
    def as_dict(self):
        rv = {"uid":self.uid, 
              "date":self.date.isoformat(), 
              "location": dict(lat=self.loc.lat, lon=self.loc.lon),
              "city":self.city,
              "publicAddress":self.addr,
              "extra":self.extra
              }
        rv['events'] = [ e.as_dict() for e in self.entries]
        return rv
    
    def sort_entries(self):
        """Sort all the log entries in timestamp order and remove duplicates"""
        #self.entries = list(set(self.entries))
        self.entries.sort()
        seen = set()
        seen_add = seen.add
        self.entries = [e for e in self.entries if e not in seen and not seen_add(e)]
        
    def count(self, event=None):
        if event is None:
            event = 'start'
        rv=0
        for entry in self.entries:
            if entry.event==event:
                rv += 1
        return rv
        
    def duration(self,event):
        """calculates the average time taken for each of the given discovery method
        """
        start = None
        times=[]
        for entry in self.entries:
            if entry.event=='start':
                start = entry
            elif entry.event==event and start is not None:
                times.append((entry.timestamp - start.timestamp).total_seconds())
                start = None
        if len(times):
            avg = math.fsum(times) / len(times)
            return avg
            #secs = int(avg)
            #usecs = int((avg-secs)*1000000)
            #mins = secs // 60
            #secs = secs % 60
            #hours = mins // 60
            #mins = mins % 60
            #return datetime.time(hour=hours,minute=mins,second=secs,microsecond=usecs)            
        return None
                
    