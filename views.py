#!/usr/bin/env python
#
import hmac, hashlib, binascii, decimal, sys, json, os, uuid, logging, datetime, urllib

import webapp2, jinja2
from google.appengine.api import users, taskqueue, channel, search
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.datastore.datastore_query import Cursor
from webapp2_extras import securecookie
from webapp2_extras import security
from webapp2_extras.appengine.users import login_required, admin_required

from wtforms.ext.appengine.ndb import model_form, model_fields
import wtforms
import mimerender

from models import NetworkService, ApiAuthorisation, ServiceLocation, LogEntry, EventLog
from serviceparser import parse_service_list, parse_contact_list
from settings import cookie_secret, csrf_secret
from routes import routes
from utils import on_production_server, flatten, from_isodatetime

mimerender = mimerender.Webapp2MimeRender()

templates = jinja2.Environment(
                               loader=jinja2.FileSystemLoader(
                                                              os.path.join(os.path.dirname(__file__),'templates')
                                                              ),
                               extensions=['jinja2.ext.autoescape'])

NetworkServiceForm = model_form(NetworkService, exclude=('md','pt',))
        
class RequestHandler(webapp2.RequestHandler):
    CLIENT_COOKIE_NAME='discovery'
    CSRF_COOKIE_NAME='csrf'
    
    def create_context(self, **kwargs):
        route = routes[self.request.route.name]
        context = {
                   "title": kwargs.get('title', route.title),
                   "uri_for":self.uri_for,
                   "on_production_server":on_production_server
                   }
        #parent = app.router.match()
        #(route, args, kwargs)
        for k,v in kwargs.iteritems():
            context[k] = v
        p = route.parent
        context["breadcrumbs"]=[]
        while p:
            p = routes[p]
            context["breadcrumbs"].insert(0,{"title":p.title,
                                           "href":self.uri_for(p.name)})
            p = p.parent
        context['user'] = self.user = users.get_current_user()
        if self.user:
            context['logout'] = users.create_logout_url(self.uri_for('home'))
            context["is_current_user_admin"]=users.is_current_user_admin()
        else:
            context['login'] = users.create_login_url(self.uri_for('home'))
        context['remote_addr'] = self.request.remote_addr
        context['request_uri'] = self.request.uri
        return context
    
    def generate_csrf(self,context):
        """generate a CSRF token as a hidden form field and a secure cookie"""
        csrf = security.generate_random_string(length=32)
        sig = hmac.new(csrf_secret,csrf,hashlib.sha1)
        sig.update(self.request.headers['X-AppEngine-country'])
        sig.update(self.request.headers['User-Agent'])
        sig = sig.digest()
        context['csrf_token'] ='<input type="hidden" name="csrf_token" value="%s" />'%urllib.quote(binascii.b2a_base64(sig))
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
                token = urllib.unquote(self.request.params['csrf_token'])
                sig = hmac.new(csrf_secret,csrf,hashlib.sha1)
                sig.update(self.request.headers['X-AppEngine-country'])
                sig.update(self.request.headers['User-Agent'])
                sig_hex = sig.hexdigest()
                tk_hex = binascii.b2a_hex(binascii.a2b_base64(token))
                return sig_hex==tk_hex 
            except KeyError:
                pass
        return False

    def password_hash(self, api_auth, uid):
        """Calculate the password hash for a given ApiAuthorisation and UID""" 
        sha1 = hashlib.sha1()
        sha1.update(uid)
        sha1.update(':')
        sha1.update(api_auth.apikey)
        sha1.update(':')
        sha1.update(api_auth.secret)
        return sha1.hexdigest()
        
    def check_authorisation(self):
        rv = None
        try:
            sc = securecookie.SecureCookieSerializer(cookie_secret)
            appid = sc.deserialize(self.CLIENT_COOKIE_NAME, self.request.cookies[self.CLIENT_COOKIE_NAME])
            if appid:
                rv = ApiAuthorisation.query(ApiAuthorisation.apikey==appid).get()
        except KeyError:
            rv = None
        if rv is None:
            try:
                auth =  self.request.headers['Authorization'].strip().split(' ')
                if auth and auth[0]=='SRV':
                    appid,uid,sig = auth[1].split(':')
                    appid = appid.strip()
                    rv = ApiAuthorisation.query(ApiAuthorisation.apikey==appid).get()
                    if rv:
                        sigcheck = hmac.new(self.password_hash(rv, uid),appid,hashlib.sha1)
                        sigcheck.update(self.request.uri)
                        sigcheck = sigcheck.hexdigest()
                        if sigcheck!=sig:
                            rv = None
            except (KeyError, TypeError, ValueError):
                rv=None            
        return rv

class MainPage(RequestHandler):
    def get(self, **kwargs):
        context = self.create_context(**kwargs) 
        context["headers"]=[]
        context['routes'] = routes
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
        return template.render(dict(error=str(exception)))

    def render_json(services, handler):
        return json.dumps(dict(services=services))

    def render_html(services, handler):
        context = handler.create_context()
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
        q = q.query(ServiceLocation.public_address==self.request.remote_addr)
        #ServiceLocation.country==self.request.headers['X-AppEngine-country'])
        for ns in q:
            for addr in ns.internal_addresses.split(','):
                rv.append({'path':ns.path,'uid':ns.uid,'address':addr.strip(), 'port':ns.port})
        return {"services":rv, "handler":self}
            
class RegistrationHandler(RequestHandler):
    """register a device or an API"""
    @login_required
    def get(self,reg_type):
        if not on_production_server:
            logging.info('GET Registration request %s'%str(reg_type))
        context = self.create_context(reg_type=reg_type, new_user=False)
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
        if not on_production_server:
            logging.debug('POST Registration request %s'%str(reg_type))
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
        try:
            addresses = self.request.POST.getall('address')
            uid = self.request.params['uid'].strip()
            port = int(self.request.params['port'])
            service_type = self.request.params['srv'].strip()
            path=self.request.params['path'].strip() 
            srv = NetworkService.get_by_id(service_type)
            if not srv:
                srv = NetworkService.query(NetworkService.name==service_type).get()
            if not srv:
                logging.debug('Unable to find service '+service_type)
                raise ValueError
            sigcheck = hmac.new(self.password_hash(auth, uid),appid,hashlib.sha1)            
            sigcheck.update(':')
            sigcheck.update(service_type)
            sigcheck.update(':')
            sigcheck.update(uid)
            sigcheck.update(':')
            sigcheck.update('%05d'%port)
            sigcheck.update(':')
            sigcheck.update(path)
            for addr in addresses:
                sigcheck.update(':')
                sigcheck.update(addr)
            sigcheck = sigcheck.hexdigest()
            #logging.info('sig check %s %s'%(sigcheck,sig))
            if sigcheck==sig:
                status='ok'
                if path and path[0]=='/':
                    path = path[1:]
                loc = ServiceLocation(id=uid,
                                      parent=srv.key,
                                      uid = uid,                      
                                      public_address = self.request.remote_addr,
                                      port = port,
                                      path=path, 
                                      internal_addresses = ', '.join(addresses))
                loc.put()
        except (KeyError,ValueError),e:
            logging.info('registration error '+str(e))
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
        context = self.create_context()
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
        context = self.create_context()
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
        context = self.create_context()
        context['authorisation']=ApiAuthorisation.query().iter()
        template = templates.get_template('registration.html')
        self.response.write(template.render(context))

class LoggingAPI(RequestHandler):
    """REST API to access logging data
    """
    LINK_TEMPLATE=r'<{url}?cursor={cursor}>; rel="{rel}"'
    
    def get(self, uid=None, date=None, id=None):
        if not users.is_current_user_admin():
            context['error']='Only a site administrator can use this service'
            template = templates.get_template('error.html')
        #context = {'handler':self}
        cursor = self.request.get('cursor')
        if cursor and '%25' in cursor:
            # double-escaped URL
            cursor = urllib.unquote(cursor)
            logging.info(cursor)
        cursor = urllib.unquote(cursor)
        curs = Cursor(urlsafe=cursor)
        if id is not None:
            key = ndb.Key(urlsafe=id)
            logs = [key.get()]
        else:
            query = EventLog.query()
            try:
                per_page = int(self.request.get('per_page'))
            except ValueError:
                per_page=20
            if per_page>50:
                per_page=50
            if uid is not None:
                query = query.filter(EventLog.uid==uid)
                #context["title_link"]=self.uri_for('logging')
                #context['uid'] = uid
            if date is not None:
                date = from_isodatetime(date)
            if date is not None:
                #context["title_link"]=self.uri_for('logging')
                #context["date"] = date
                query = query.filter(EventLog.date==date)
            forward_order = EventLog.date
            backward_order = -EventLog.date
            if self.request.get('sort_by')=='uid':
                order_by = EventLog.uid
            if self.request.get('order')=='desc':
                forward_order,backward_order = (backward_order,forward_order)
            logs, next_curs, next = query.order(forward_order).fetch_page(per_page, start_cursor=curs)
            #context["logs"] = logs
            #if uid and logs:
            #    context['info']={}
            #    for log in logs:
            #        if log.loc.lat or log.loc.lon:
            #            context['map'] = True
            #            context['info']['location'] = log.loc
            #        for f in ['addr','name','city','client']:
            #            if getattr(log,f):
            #                context['info'][f] = getattr(log,f) 
            #        if log.extra:
            #            try:
            #                context['info']['extra'].update(log.extra)
            #            except KeyError:
            #                context['info']['extra']= dict(log.extra)                        
        prev_curs=prev=None
        if self.request.get('cursor'):
            rev_curs = curs.reversed()
            logs2, prev_curs, prev = query.order(backward_order).fetch_page(per_page, start_cursor=rev_curs)
        flogs = []
        fentries = []
        sideload=self.request.get('sideload',False)
        for log in logs:
            fl = flatten(log)
            fl['id'] = log.key.urlsafe()
            flogs.append(fl)
            if sideload:
                keys = []
                index=0
                for e in fl['entries']:
                    e['id'] = '#'.join([fl['id'],str(index)])
                    keys.append(e['id'])
                    fentries.append(e)
                    index += 1
                fl['event_ids'] = keys
                del fl['entries']
        if id is not None:
            if sideload:
                js = {'event_log':flogs[0],'events':fentries}
            else:
                js = flogs[0]
        else:
            js = { 'event_logs':flogs } if sideload else flogs
            links = [self.LINK_TEMPLATE.format(url=self.request.path_url, cursor='',rel="first")]
            if next and next_curs:
                links.append(self.LINK_TEMPLATE.format(url=self.request.path_url, cursor=urllib.quote(next_curs.urlsafe()),rel="next"))
            if prev and prev_curs:
                links.append(self.LINK_TEMPLATE.format(url=self.request.path_url, cursor=urllib.quote(prev_curs.urlsafe()),rel="prev"))
            self.response.headers.add('Link', ', '.join(links))                
            if sideload:
                js['events'] = fentries
        self.response.content_type='application/json'
        self.response.write(json.dumps(js))

class Logging(RequestHandler):
    def get(self, **kwargs):
        context = self.create_context()
        context['route'] = kwargs
        template = templates.get_template('logging.html')
        self.response.write(template.render(context))

    def make_key(self, uid, start_time):
        return ('u%s%s'%(uid,start_time.date().isoformat())).replace('-','')
        
    def get_log_entry(self, uid, start_time):
        log=None
        try:
            id = self.make_key(uid,start_time)
            log = self.cache[id]
        except KeyError:                        
            log = EventLog.query(EventLog._key==ndb.Key(EventLog,id)).get()
            if not log:
                log = EventLog(id=id, entries=[], uid=uid, date=start_time, client=False)
            #log.sort_entries()
            self.cache[id] = log
        return log
        
    def set_location_fields(self,log):
        try:
            lat,lng = self.request.headers['X-AppEngine-CityLatLong'].split(',')
            log.loc = ndb.GeoPt(float(lat),float(lng))
        except (KeyError, ValueError):
            if log.loc is None:
                log.loc = ndb.GeoPt(0,0)
                #log.loc = ndb.GeoPt(51.52,0.11)
        log.addr = self.request.remote_addr
        try: 
            log.city = ', '.join([self.request.headers['X-AppEngine-City'],
                                  self.request.headers['X-AppEngine-Region'],
                                  self.request.headers['X-AppEngine-Country']])
        except KeyError,e:
            logging.debug(str(e))
            # These geo-ip headers don't exist on the dev server
            pass
        
    def post(self):
        if self.request.content_type!='application/json':
            self.response.status=400
            logging.error('invalid content type %s'%self.request.content_type)
            self.response.write('invalid content type')
            return
        ak = self.check_authorisation()
        if not ak:
            self.response.headers['WWW-Authenticate']='SRV'
            self.error(401)
            return
        self.cache = {}
        data = json.load(self.request.body_file)
        #{"devices":[{"date":"2013-07-22T11:40:51Z","uid":"4d9cf5f4-4574-4381-9df3-1d6e7ca295ff","events":[{"time":"2013-07-22T11:40:51Z","event":"start"},{"method":"upnp","time":"2013-07-22T11:40:53Z","event":"found"},{"method":"cloud","time":"2013-07-22T11:40:53Z","event":"found"},{"time":"2013-07-22T11:40:53Z","event":"end"},{"method":"zeroconf","time":"2013-07-22T11:40:59Z","event":"found"}]}],"extra":{"client":{"uid":"af290300-bef5-4bfd-838c-e05c3c99f73e"},"dhcp":{"dns1":"172.20.0.102","dns2":"172.20.0.106","gatewayMAC":"00:90:0b:25:6c:f6","gatewayIP":"172.20.0.1","address":"172.20.4.42","netmask":"255.255.248.0"},"wifi":{"bssid":"02:e6:fe:91:a5:c3","mac":"60:a4:4c:91:a5:c3","ip":"172.20.4.42"}}}
        try:
            for dev in data['devices']:
                uid = dev['uid']
                start_time = from_isodatetime(dev['date'])
                log = self.get_log_entry(uid, start_time)
                try:
                    log.name = dev['name']
                except KeyError:
                    pass
                self.set_location_fields(log)
                for event in dev['events']:
                    timestamp = from_isodatetime(event['time'])
                    if event['event']=='found' and event.has_key('method'):
                        event['event'] = event['method']
                        del event['method']
                    # cause a ValueError exception if the event type is invalid
                    LogEntry.EVENT_TYPES.index(event['event'])                    
                    le = LogEntry(ts=timestamp, ev=event['event'])
                    log.entries.append(le)
                try:
                    if log.extra is None:
                        log.extra = {}
                    log.extra.update(data['extra'])
                    if log.extra.has_key('client'):
                        del log.extra['client']
                except KeyError,e:
                    logging.info(str(e))
                    pass
            try:
                puid = data['extra']['client']['uid']
                start_time = data['extra']['client'].get('date', datetime.datetime.now())
                clog = self.get_log_entry(puid, start_time)
                clog.client=True
                self.set_location_fields(clog)
                clog.extra = {}
                clog.extra.update(data['extra'])
                del clog.extra['client']
                clog.extra['locations']=[]
                q = ServiceLocation.query(ServiceLocation.public_address==self.request.remote_addr)
                #ServiceLocation.country==self.request.headers['X-AppEngine-country'])
                for ns in q:
                    clog.extra['locations'].append({'uid':ns.uid,'addresses':ns.internal_addresses})
            except KeyError,e:
                logging.info(str(e))
                pass
            values = self.cache.values()
            for log in values:
                log.sort_entries()
                #logging.info('log for %s'%log.uid)
                #log.put()
            ndb.put_multi(values)
            self.response.content_type='text/plain'
            self.response.write('logs accepted')                                             
        except (ValueError,KeyError),e:
            self.response.content_type='text/plain'
            self.response.write('Invalid data: %s'%(str(e)))                                             
            self.response.status=400
            logging.error(str(e))

class UploadLogs(Logging):
    class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):            
        def post(self):
            context = self.outer.create_context()
            upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
            if len(upload_files)==0:
                self.outer.get()
                return
            blob_info = upload_files[0]
            blob_reader = blobstore.BlobReader(blob_info.key())
            try:
                js = json.load(blob_reader)
                self.outer.cache = {}
                for event in js['event_logs']:
                    uid = event['uid']
                    start_time = from_isodatetime(event['date'])
                    log = self.outer.get_log_entry(uid, start_time)
                    for ev in event['entries']:
                        le = LogEntry(ts=from_isodatetime(ev['ts']), ev=ev['ev'])
                        log.entries.append(le)
                    log.client = event['client']
                    log.name = event['name']
                    if event.has_key('loc') and event['loc'] is not None:
                        log.loc = ndb.GeoPt(lat=event['loc']['lat'], lon=event['loc']['lon'])
                    log.city = event['city']
                    log.addr = event['addr']
                    log.extra = event['extra']
                values = self.outer.cache.values()
                for log in values:
                    log.sort_entries()
                context['logs'] = values
                ndb.put_multi(values)
            except:
                raise 
            finally:
                blob_reader.close()
            template = templates.get_template('import-logs.html')
            self.response.write(template.render(context))
            
    def __init__(self, request, response):
        self.initialize(request, response)
        self.upload_handler = self.UploadHandler(request, response)
        self.upload_handler.outer = self
        self.post = self.upload_handler.post
        
    def get(self):
        context = self.create_context()
        if not users.is_current_user_admin():
            context['error']='Only a site administrator can upload event logs'
            template = templates.get_template('error.html')
        else:
            template = templates.get_template('import-logs.html')
            context['upload_url'] = blobstore.create_upload_url(self.request.uri)
        self.response.write(template.render(context))
        
class MaintenanceWorker(webapp2.RequestHandler):
    def get(self):
        expiry = datetime.datetime.now() - datetime.timedelta(hours=8)
        expired_locations = ServiceLocation.query(ServiceLocation.last_update<expiry).fetch(keys_only=True)
        ndb.delete_multi(expired_locations)
        #updated=[]
        #delete_me=[]
        #for auth in ApiAuthorisation.query():
        #    if auth.apikey=='' or auth.apikey is None:
        #        delete_me.append(auth.key)
        #    elif auth.created is None:
        #        auth.created = datetime.datetime.now()
        #        auth.modified = datetime.datetime.now()
        #        updated.append(auth.apikey)
        #        auth.put()
        #ndb.delete_multi(delete_me)
        self.response.content_type='text/plain'
        self.response.write('cleanup done')                             