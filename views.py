#!/usr/bin/env python
#
import hmac, hashlib, binascii, decimal, sys, json, os, uuid, logging, datetime

import webapp2, jinja2
from google.appengine.api import users, taskqueue, channel, search
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from webapp2_extras import securecookie
from webapp2_extras import security
from webapp2_extras.appengine.users import login_required, admin_required

from wtforms.ext.appengine.ndb import model_form, model_fields
import wtforms
import mimerender

from models import NetworkService, ApiAuthorisation, ServiceLocation
from serviceparser import parse_service_list, parse_contact_list
from settings import cookie_secret, csrf_secret 

mimerender = mimerender.Webapp2MimeRender()

templates = jinja2.Environment(
                               loader=jinja2.FileSystemLoader(
                                                              os.path.join(os.path.dirname(__file__),'templates')
                                                              ),
                               extensions=['jinja2.ext.autoescape'])

NetworkServiceForm = model_form(NetworkService, exclude=('md','pt',))

def flatten(items):
    """Converts an object in to a form suitable for storage.
    flatten will take a dictionary, list or tuple and inspect each item in the object looking for
    items such as datetime.datetime objects that need to be converted to a canonical form before
    they can be processed for storage.
    """
    if isinstance(items,dict):
        rv={}
    else:
        rv = []
    for item in items:
        key = None
        if isinstance(items,dict):
            key = item
            item = items[key]
        if isinstance(item,(datetime.datetime,datetime.time)):
            iso = item.isoformat()
            if not item.utcoffset():
                iso += 'Z'
            item = iso
        elif isinstance(item,(datetime.date)):
            item = item.isoformat()
        elif isinstance(item,long):
            item = '%d'%item
        elif isinstance(item,(unicode,str,decimal.Decimal)):
            item = str(item).replace("'","\'")
        elif isinstance(item,(dict,list)):
            item = flatten(item)
        if key:
            rv[key]=item
        else:
            rv.append(item)
    if items.__class__ == tuple:
        return tuple(rv)
    return rv

def from_isodatetime(date_time):
    """
    Convert an ISO formated date string to a datetime.datetime object
    """
    if not date_time:
        return None
    if date_time[:2]=='PT':
        if 'M' in date_time:
            dt = datetime.datetime.strptime(date_time, "PT%HH%MM%SS")
        else:
            dt = datetime.datetime.strptime(date_time, "PT%H:%M:%S")
        secs = (dt.hour*60+dt.minute)*60 + dt.second
        return datetime.timedelta(seconds=secs)
    if 'T' in date_time:
        return datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%SZ")
    if not 'Z' in date_time:
        try:
            return datetime.datetime.strptime(date_time, "%Y-%m-%d")
        except ValueError:
            return datetime.datetime.strptime(date_time, "%d/%m/%Y")
    return datetime.datetime.strptime(date_time, "%H:%M:%SZ").time()

        
class RequestHandler(webapp2.RequestHandler):
    HOME_PAGE_TITLE="Service discovery"
    CLIENT_COOKIE_NAME='discovery'
    CSRF_COOKIE_NAME='csrf'
    
    def create_context(self, title=None, **kwargs):
        context = {
                   "title":self.HOME_PAGE_TITLE if title is None else title,
                   "uri_for":self.uri_for
                   }
        for k,v in kwargs.iteritems():
            context[k] = v
        if title: #self.request.uri!=self.uri_for('home'):
            context["breadcrumbs"]={"title":self.HOME_PAGE_TITLE,
                                    "href":self.uri_for('home')}
        context['user'] = self.user = users.get_current_user()
        if self.user:
            context['logout'] = users.create_logout_url(self.uri_for('home'))
            context["is_current_user_admin"]=users.is_current_user_admin()
        else:
            context['login'] = users.create_login_url(self.uri_for('home'))
        context['remote_addr'] = self.request.remote_addr
        return context
    
    def generate_csrf(self,context):
        """generate a CSRF token as a hidden form field and a secure cookie"""
        csrf = security.generate_random_string(length=32)
        sig = hmac.new(csrf_secret,csrf,hashlib.sha1)
        sig.update(self.request.headers['X-AppEngine-country'])
        sig.update(self.request.headers['User-Agent'])
        sig = sig.digest()
        context['csrf_token'] ='<input type="hidden" name="csrf_token" value="%s" />'%binascii.b2a_base64(sig)
        sc = securecookie.SecureCookieSerializer(cookie_secret)
        cookie = sc.serialize(self.CSRF_COOKIE_NAME, csrf)
        self.response.set_cookie(self.CSRF_COOKIE_NAME, cookie, httponly=True, max_age=3600)
        
    def check_csrf(self):
        """check that the CSRF token from the cookie and the submitted form match"""
        sc = securecookie.SecureCookieSerializer(cookie_secret)
        csrf = sc.deserialize(self.CSRF_COOKIE_NAME, self.request.cookies[self.CSRF_COOKIE_NAME])
        self.response.delete_cookie(self.CSRF_COOKIE_NAME)
        if csrf:
            try:
                token = self.request.params['csrf_token']
                sig = hmac.new(csrf_secret,csrf,hashlib.sha1)
                sig.update(self.request.headers['X-AppEngine-country'])
                sig.update(self.request.headers['User-Agent'])
                sig_hex = sig.hexdigest()
                tk_hex = binascii.b2a_hex(binascii.a2b_base64(token))
                return sig_hex==tk_hex 
            except KeyError:
                pass
        return False
        
    def check_authorisation(self):
        rv = None
        try:
            sc = securecookie.SecureCookieSerializer(cookie_secret)
            appid = sc.deserialize(self.CLIENT_COOKIE_NAME, self.request.cookies[self.CLIENT_COOKIE_NAME])
            if appid:
                rv = ApiAuthorisation.query(ApiAuthorisation.apikey==appid).get()
        except KeyError:
            rv = None
        return rv

class MainPage(RequestHandler):
    def get(self):
        context = self.create_context() 
        context["headers"]=[]
        appid = ak = None
        ak = self.check_authorisation()
        if ak:
            context['authenticated']=True
        #for k in self.request.headers.keys():
        #    if k.lower()!='cookie':
        #        context['headers'].append((k,self.request.headers[k]))
        #if appid and ak:
        #    context["services"]=[]
        #    for ns in ServiceLocation.query(ServiceLocation.public_address==self.request.remote_addr,
        #                                     ServiceLocation.country==self.request.headers['X-AppEngine-country']).iter():
        #        for addr in ns.internal_addresses.split(','):
        #            context["services"].append({'name':ns.name,'uid':ns.uid,'address':addr.strip(), 'port':ns.port})
        template = templates.get_template('index.html')
        self.response.write(template.render(context))

class NotAuthorisedException(Exception):
    pass

class SearchHandler(RequestHandler):
    """search for devices on the local network"""
    def render_json_exception(exception):
        return json.dumps(dict(error=str(exception)))

    def render_html_exception(exception):
        template = templates.get_template('error.html')
        return template.render(dict(error=str(exception), title="Search for devices"))

    def render_json(services, handler):
        return json.dumps(dict(services=services))

    def render_html(services, handler):
        context = handler.create_context("Search for devices")
        context["services"] = services
        template = templates.get_template('discovery.html')
        return template.render(context)

    @mimerender.map_exceptions(
                               mapping=[
                                        (NotAuthorisedException,'401 Not authorised'),
                                        ],
                               html = render_html_exception,
                               json = render_json_exception,
                               )
    @mimerender(
                default = 'html',
                html = render_html,
                json = render_json,
                )
    def get(self, service_type=None):
        rv = []
        ak = self.check_authorisation()
        if not ak:
            raise NotAuthorisedException('This device is not registered to use this service')
        q = ServiceLocation
        if service_type:
            srv = NetworkService.query(NetworkService.name == service_type).get()
            if srv:
                q = q.ancestor(srv)
        q = q.query(ServiceLocation.public_address==self.request.remote_addr,
                    ServiceLocation.country==self.request.headers['X-AppEngine-country'])
        for ns in q:
            for addr in ns.internal_addresses.split(','):
                rv.append({'name':ns.name,'uid':ns.uid,'address':addr.strip(), 'port':ns.port})
        return {"services":rv, "handler":self}
            
class RegistrationHandler(RequestHandler):
    """register a device or an API"""
    @login_required
    def get(self,reg_type):
        context = self.create_context("Register a device", reg_type=reg_type, new_user=False)
        user = users.get_current_user()
        #if not user:
        #    self.redirect(users.create_login_url(self.request.uri))
        #    return
        ak = None
        ak = self.check_authorisation()
        if not ak:
            ak = ApiAuthorisation.query(ApiAuthorisation.user==user).get()
        if reg_type=='api':
            #if not users.is_current_user_admin():
            #    template = templates.get_template('not-auth.html')
            #else:
            template = templates.get_template('api.html')
            self.generate_csrf(context)
            context['title']='Register an API'
            context['ajax_url'] = self.uri_for('services-ajax')
            context['ajax_key'] = ak.apikey if ak is not None else user.id
            context['services'] = [] #NetworkService.query().iter()
            self.response.write(template.render(context))
            return
        if not ak:
            context['new_user']=True
            ak = ApiAuthorisation(
                                  apikey=uuid.uuid4().get_hex(),
                                  secret=security.generate_random_string(length=20, pool=security.ASCII_PRINTABLE),
                                  user=user,
                                  country=self.request.headers['X-AppEngine-country'],
                                  description=self.request.headers['User-Agent'])
        ak.modified = datetime.datetime.now()
        ak.put()
        sc = securecookie.SecureCookieSerializer(cookie_secret)
        cookie = sc.serialize(self.CLIENT_COOKIE_NAME, str(ak.apikey))
        self.response.set_cookie(self.CLIENT_COOKIE_NAME, cookie, httponly=True)
        template = templates.get_template('register.html')
        self.response.write(template.render(context))
                
    def post(self,reg_type=None):
        if reg_type=='api':
            user = users.get_current_user()
            if not user:
                self.redirect(users.create_login_url(self.request.uri))
                return
            context = self.create_context("Register an API", reg_type=reg_type, new_user=True)
            if not users.is_current_user_admin():
                template = templates.get_template('error.html')
                context['error'] ='Not authorised'
                self.response.write(template.render(context))
                return
            ak = ApiAuthorisation(
                                  apikey = uuid.uuid4().get_hex(),
                                  secret=security.generate_random_string(length=20, pool=security.ALPHANUMERIC+'$!:@;.,^#[]{}'),
                                  user = user,
                                  service=self.request.POST.get('service'),
                                  country=self.request.headers['X-AppEngine-country'],
                                  description=self.request.params['description'].strip()
                                  )
            ak.put()
            context['ak'] = ak
            template = templates.get_template('register.html')
            self.response.write(template.render(context))
            return
        authenticated = False
        secret = None
        status='failed'
        try:
            auth =  self.request.headers['Authorization'].strip().split(' ')
            if auth and auth[0]=='SRV':
                appid,sig = auth[1].split(':')
                appid = appid.strip()
                auth = ApiAuthorisation.query(ApiAuthorisation.apikey==appid).get()
                if auth:
                    authenticated=True
                    sig = binascii.a2b_base64(sig)
                    sig = binascii.b2a_hex(sig)
        except (KeyError, TypeError, ValueError):
                pass
        if not authenticated:
            self.response.headers['WWW-Authenticate']='SRV'
            self.error(401)
            return
        sigcheck = hmac.new(str(auth.secret),appid,hashlib.sha1)
        try:
            name=self.request.params['name'].strip() 
            addresses = self.request.POST.getall('address')
            uid = self.request.params['uid'].strip()
            port = int(self.request.params['port'])
            service_type = self.request.params['srv'].strip()
            srv = NetworkService.get_by_id(service_type)
            if not srv:
                srv = NetworkService.query(NetworkService.name==service_type).get()
            if not srv:
                logging.info('Unable to find service '+service_type)
                raise ValueError
            sigcheck.update(service_type)
            sigcheck.update(name)
            sigcheck.update(uid)
            sigcheck.update('%05d'%port)
            for addr in addresses:
                sigcheck.update(addr)
        except (KeyError,ValueError),e:
            logging.info('registration error '+str(e))
            pass
        sigcheck = sigcheck.hexdigest()
        if sigcheck==sig:
            status='ok'
            try:
                location = self.request.headers['X-AppEngine-CityLatLong']
            except KeyError:
                location = ndb.GeoPt(0,0)
            loc = ServiceLocation(id=uid,
                                  parent=srv.key,
                                  name=name, 
                                  country=self.request.headers['X-AppEngine-country'],
                                  uid = uid,                      
                                  public_address = self.request.remote_addr,
                                  location = location,
                                  port = port,
                                  internal_addresses = ', '.join(addresses))
            loc.put()
        self.response.content_type='application/json'
        self.response.write('{"status":"%s", "to":"%s", "address":"%s"}'%(status,uid,self.request.remote_addr))

class NetworkServiceSearch(webapp2.RequestHandler):
    """ajax search api for service names"""
    @login_required
    def get(self):
        query_string = self.request.params.get('q')
        try:
            page_limit = int(self.request.params.get('page_limit',5))
        except ValueError:
            page_limit=5
        options=search.QueryOptions(
                                    limit=page_limit,
                                    returned_fields=['name', 'description', 'protocol', 'port'],
                                    )
        query = search.Query(query_string=query_string, options=options)
        results = search.Index(name=NetworkService.INDEX_NAME).search(query)
        rv = {"services": []}
        if results:
            for result in results:
                item = {}
                for f in options.returned_fields:
                    if result[f]:
                        item[f] = result[f][0].value
                rv["services"].append(item)
        self.response.content_type='application/json'
        self.response.write(json.dumps(rv))
        
class UnregistrationHandler(RequestHandler):
    def get(self, key=None):
        context = self.create_context(title="Unregister this device")
        if key is None:
            self.response.delete_cookie(self.CLIENT_COOKIE_NAME)
        else:
            key = ndb.Key(urlsafe=key)
            context['title']='Authorisation removed'
            key.delete()
        template = templates.get_template('unregister.html')
        self.response.write(template.render(context))

class ImportWorker(webapp2.RequestHandler):
    def post(self):
        batch = json.loads(self.request.POST['batch'])
        for item in batch:
            item['modification'] = from_isodatetime(item['modification'])
            srv = NetworkService(**item)
            srv.put()

class EditNetworkService(RequestHandler):
    """Create or edit a service definition"""
    @admin_required
    def get(self, service_type=None):
        self.post(service_type)
        
    def post(self, service_type=None):
        context = self.create_context("Add a service")
        if not users.is_current_user_admin():
            context['error']='Only a site administrator can create a new service'
            template = templates.get_template('error.html')
            return
        service = None
        if service_type is not None:
            service = NetworkService.get_by_id(service_type)
            if not service:
                service = NetworkService.query(NetworkService.name==service_type).get()
            if not service:
                self.response.write('Service not found')
                self.response.set_status(404)
                return
        form = NetworkServiceForm(self.request.POST, obj=service)
        if self.request.method=='POST':
            if self.check_csrf() and form.validate():
                if service and (service.name!=form.nm.data or service.protocol!=form.pr.data):
                    service.delete()
                    service=None 
                if service is None:
                    service=NetworkService(id='_'+form.nm.data+'._'+form.pr.data)
                field_names = NetworkService._properties.keys() 
                for k in field_names:
                    try:
                        setattr(service, NetworkService.NAME_MAPPING[k], form[k].data)
                    except KeyError:
                        pass
                service.modification = datetime.datetime.now()
                if '.' in service.name:
                    service.name = service.name.split('.')[0]
                if service.name[0]=='_':
                    service.name = service.name[1:]
                service.put()
                self.redirect(self.uri_for('home'))
                return        
        self.generate_csrf(context)
        context['form'] = form
        context['object'] = service
        template = templates.get_template('edit-object.html')
        self.response.write(template.render(context))
        
def parse_services_blob(blob_key, client_id, worker_url, wipe=False):
    outer = { "lines":0, "contacts":0, "batch":[], "todo":10 }
    def contact_progress(lc,cc):
        outer["lines"] = lc
        outer["contacts"] = cc
        #logging.info('contact %s %s'%(str(lc),str(cc)))
    def service_progress(lc,sc):
        channel.send_message(client_id, '{"service_line":%d, "num_services":%d}'%(lc,sc))
        #logging.info('service %s %s'%(str(lc),str(sc)))
    def db_batch_store(**kwargs):
        outer['batch'].append(kwargs)
        outer["todo"] -= 1
        if outer["todo"]==0:
            taskqueue.add(url=worker_url, queue_name='import-worker', params={'batch':json.dumps(flatten(outer['batch']))})
            outer['batch']=[]
            outer["todo"] = 10
    if wipe==True:
        NetworkService.empty_database()
        deferred.defer(parse_services_blob, blob_key, client_id, worker_url, wipe=False)
        return
    blob_reader = blobstore.BlobReader(blob_key)
    contacts = parse_contact_list(blob_reader, contact_progress)
    blob_reader.close()
    channel.send_message(client_id, '{"num_lines":%d, "num_contacts":%d}'%(outer["lines"],outer["contacts"]))
    #logging.info('Found %d contacts, %d lines in file'%(outer["contacts"],outer["lines"]))
    blob_reader = blobstore.BlobReader(blob_key)
    parse_service_list(blob_reader, contacts=contacts, progress=service_progress,db_store=db_batch_store)
    if outer['batch']:
        taskqueue.add(url=worker_url, queue_name='import-worker', params={'batch':json.dumps(flatten(outer['batch']))})
    blob_reader.close()
    blobstore.delete(blob_key)

class UploadServiceList(RequestHandler):
    class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
            
        def post(self):
            context = self.outer.create_context(title="Upload service list")
            upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
            if len(upload_files)==0:
                self.outer.get()
                return
            blob_info = upload_files[0]
            context['channel_token'] = channel.create_channel(self.outer.user.user_id() + 'networkservice')        
            deferred.defer(parse_services_blob,
                           blob_key=blob_info.key(),
                           client_id=self.outer.user.user_id()+'networkservice', 
                           worker_url=self.outer.uri_for("import-worker"),
                           wipe=self.request.POST.get('wipe',False))
            template = templates.get_template('import-services.html')
            self.response.write(template.render(context))
            
    def __init__(self, request, response):
        self.initialize(request, response)
        self.upload_handler = self.UploadHandler(request, response)
        self.upload_handler.outer = self
        self.post = self.upload_handler.post
        
    def get(self):
        context = self.create_context(title="Upload service list")
        if not users.is_current_user_admin():
            context['error']='Only a site administrator can upload a service list'
            template = templates.get_template('error.html')
        else:
            template = templates.get_template('import-services.html')
            context['upload_url'] = blobstore.create_upload_url(self.request.uri)
        self.response.write(template.render(context))
                    
class ChannelHandler(webapp2.RequestHandler):
    def post(self, *args, **kwargs):
        client_id = self.request.get('from')
        self.response.content_type='application/json'
        self.response.write('{"status":"ok"}')

class RegistrationList(RequestHandler):
    @admin_required
    def get(self):
        context = self.create_context(title="Registration database")
        context['authorisation']=ApiAuthorisation.query().iter()
        template = templates.get_template('registration.html')
        self.response.write(template.render(context))
        
class MaintenanceWorker(webapp2.RequestHandler):
    def get(self):
        updated=[]
        delete_me=[]
        for auth in ApiAuthorisation.query():
            if auth.apikey=='' or auth.apikey is None:
                delete_me.append(auth.key)
            elif auth.created is None:
                auth.created = datetime.datetime.now()
                auth.modified = datetime.datetime.now()
                updated.append(auth.apikey)
                auth.put()
        ndb.delete_multi(delete_me)
        self.response.content_type='text/plain'
        self.response.write('cleanup done '+str(updated))                             