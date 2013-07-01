import datetime, re, time, math
from email.utils import formataddr

try:
    from models import NetworkService
except ImportError:
    class NetworkService(object):
        PROTOCOLS = ['tcp','udp','sctp','dccp']
        def __init__(self,**kwargs):
            for k,v in kwargs.iteritems():
                setattr(self, k, v)
        def put(self):
            print ','.join(str(s) for s in [self.name,self.port,self.protocol,
                                            self.description,self.assignee,
                                            self.contact,self.registration,
                                            self.modification,self.reference])

def parse_contact_list(source, progress=None):
    id_re = re.compile(r'^\[[A-Za-z0-9\-_]+\]$')
    contacts = {}
    line_count = 0
    contact_count = 0
    last_update = math.floor(time.time())
    for line in source:
        id= line[:58].strip()
        name = line[58:84].strip()
        organization = line[84:106].strip()
        contact = line[106:168].strip()
        if id_re.match(id) and contact:
            id = id[1:-1]
            contact = contact.replace('mailto:','').replace('&','@')
            if organization and name:
                name = ', '.join([name,organization])
            elif organization:
                name = organization
            if name:
                contact = formataddr((name,contact))
            contacts[id] = contact
            contact_count += 1
            #print ','.join([id,contact])
        line_count += 1
        if progress is not None:
            if math.floor(time.time())!=last_update:
                progress(line_count,contact_count)
                last_update = math.floor(time.time())
    if progress is not None:
        progress(line_count,contact_count)
    return contacts
        
def parse_service_list(source, contacts=None, progress=None):
    def lookup_contact(c):
        if c and c[0]=='[' and c[-1]==']':
            c = c[1:-1]
        if c and contacts.has_key(c):
            c = contacts[c]
        return c
        
    line_count = 0
    service_count = 0
    whitelist = re.compile(r'^[A-Za-z0-9\-]+$')
    blacklist = re.compile(r'(unassigned)|(de-?registered)', re.I)
    if contacts is None:
        contacts = {}
    last_update = math.floor(time.time())
    for line in source:
        name = line[:17].strip()
        try:
            port = int(line[17:23])
        except ValueError:
            port=None
        protocol = line[23:35].strip()
        description = line[38:67].strip()
        assignee = lookup_contact(line[67:147].strip())
        contact = lookup_contact(line[147:205].strip())
        registration = line[205:216].strip()
        try:
            registration = datetime.datetime.strptime(registration, "%Y-%m-%d")
        except ValueError:
            registration=None
        modification = line[218:229].strip()
        try:
            modification = datetime.datetime.strptime(modification, "%Y-%m-%d")
        except ValueError:
            modification=None
        reference = line[231:261].strip()
        #if name and not whitelist.match(name):
        #    print 'skip',name
        if name and whitelist.match(name) and protocol and protocol in NetworkService.PROTOCOLS and not blacklist.match(name):
            #print ','.join(str(s) for s in [name,port,protocol,description,assignee,contact,registration,modification,reference])
            srv = NetworkService(
                             id=('_'+name+'._'+protocol),
                             name=name,
                             port=port,
                             description=description,
                             protocol=protocol,
                             assignee=assignee,
                             contact=contact,
                             registration=registration,
                             modification=modification,
                             reference=reference
                             )
            srv.put()
            service_count += 1 
        if progress is not None:
            if math.floor(time.time())!=last_update:
                progress(line_count,service_count)
                last_update = math.floor(time.time())
        line_count += 1
    if progress is not None:
        progress(line_count,service_count)

if __name__ == "__main__":
    import sys
    source = open(sys.argv[1],'r')
    contacts = parse_contact_list(source)
    source.close()        
    source = open(sys.argv[1],'r')
    parse_service_list(source, contacts=contacts)
    source.close()        
