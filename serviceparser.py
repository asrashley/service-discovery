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
                                            self.contact,
                                            self.modification])

def put_in_database(**kwargs):
    srv = NetworkService(**kwargs)
    srv.put()

def parse_contact_list(source, progress=None):
    id_re = re.compile(r'^\[[A-Za-z0-9\-_]+\]$')
    contacts = {}
    line_count = -1
    contact_count = 0
    next_update = time.time()+1
    for line in source:
        line_count += 1
        id= line[:58].strip()
        if not id_re.match(id):
            continue
        contact = line[106:168].strip()
        if not contact:
            continue
        name = line[58:84].strip()
        organization = line[84:106].strip()
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
        if progress is not None:
            if time.time()>next_update:
                progress(line_count,contact_count)
                next_update = time.time()+1
    if progress is not None:
        progress(line_count,contact_count)
    return contacts
        
def parse_service_list(source, contacts=None, progress=None, db_store=None):
    def lookup_contact(c):
        if c and c[0]=='[' and c[-1]==']':
            c = c.split(']')[0][1:]
        if c and contacts.has_key(c):
            c = contacts[c]
        return c
        
    last = None
    line_count = -1
    service_count = 0
    whitelist = re.compile(r'^[A-Za-z0-9\-]+$')
    blacklist = re.compile(r'(unassigned)|(de-?registered)|(IANA assigned)|(well-formed)', re.I)
    if progress is None:
        progress = lambda a,b: None
    if contacts is None:
        contacts = {}
    if db_store is None:
        db_store = put_in_database
    next_update = time.time()+1
    for line in source:
        line_count += 1
        name = line[:17].strip()
        description = line[38:67].strip()
        protocol = line[23:35].strip()
        if last and (not name) and (not protocol):
            if description:
                last['description'] = ' '.join([last['description'],description])
            elif last:
                db_store(**last)
                last = None  
        if (not name) or (not description) or blacklist.search(description):
            if last:
                db_store(**last)
                last = None  
            continue
        if not whitelist.match(name):
            continue
        if not (protocol and protocol in NetworkService.PROTOCOLS):
            continue
        try:
            port = int(line[17:23])
        except ValueError:
            port=None
        assignee = lookup_contact(line[67:147].strip())
        contact = lookup_contact(line[147:205].strip())
        modification = line[218:229].strip()
        try:
            modification = datetime.datetime.strptime(modification, "%Y-%m-%d")
        except ValueError:
            modification=None
        if modification is None:
            try:
                registration = line[205:216].strip()
                registration = datetime.datetime.strptime(registration, "%Y-%m-%d")
                modification = registration
            except ValueError:
                pass
        if modification is None:
            modification = datetime.datetime.now().date()
        if last:
            db_store(**last)
        last = dict(
                 id=('_'+name+'._'+protocol),
                 name=name,
                 port=port,
                 description=description,
                 protocol=protocol,
                 assignee=assignee,
                 contact=contact,
                 modification=modification
                 )
        service_count += 1 
        if time.time()>next_update:
            progress(line_count,service_count)
            next_update = time.time()+1
    if last:
        db_store(**last)
    progress(line_count,service_count)

if __name__ == "__main__":
    import sys
    source = open(sys.argv[1],'r')
    contacts = parse_contact_list(source)
    source.close()        
    source = open(sys.argv[1],'r')
    parse_service_list(source, contacts=contacts)
    source.close()        
