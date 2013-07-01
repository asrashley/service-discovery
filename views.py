#!/usr/bin/env python
#
from datetime import datetime
import hmac, hashlib, binascii, sys, json, os, uuid, logging

import webapp2, jinja2
from google.appengine.api import users, taskqueue, channel, search
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from webapp2_extras import securecookie
from webapp2_extras import security
from webapp2_extras.appengine.users import login_required, admin_required

from models import NetworkService, ApiAuthorisation
from serviceparser import parse_service_list, parse_contact_list

from settings import cookie_secret 
templates = jinja2.Environment(
                               loader=jinja2.FileSystemLoader(
                                                              os.path.join(os.path.dirname(__file__),'templates')
                                                              ),
                               extensions=['jinja2.ext.autoescape'])


class RequestHandler(webapp2.RequestHandler):
    HOME_PAGE_TITLE="Service discovery"
    CLIENT_COOKIE_NAME='discovery'
    
    def create_context(self, title=None, **kwargs):
        context = {
                   "title":self.HOME_PAGE_TITLE if title is None else title,
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

class MainHandler(RequestHandler):
    def get(self):
        context = self.create_context() 
        context["headers"]=[]
        appid = ak = None
        ak = self.check_authorisation()
        if ak:
            context['authenticated']=True
        for k in self.request.headers.keys():
            if k.lower()!='cookie':
                context['headers'].append((k,self.request.headers[k]))
        if appid and ak:
            context["services"]=[]
            for ns in ServiceLocation.query(ServiceLocation.public_address==self.request.remote_addr,
                                             ServiceLocation.country==self.request.headers['X-AppEngine-country']).iter():
                for addr in ns.internal_addresses.split(','):
                    context["services"].append({'name':ns.name,'uid':ns.uid,'address':addr.strip(), 'port':ns.port})
        template = templates.get_template('index.html')
        self.response.write(template.render(context))
        
class SearchHandler(RequestHandler):
    def get(self, service_type=None):
        rv = []
        ak = self.check_authorisation()
        if ak:
            q = ServiceLocation.all()
            if service_type:
                srv = NetworkService.query(NetworkService.name == service_type).get()
                if srv:
                    q = q.ancestor(srv)
            q = q.filter(ServiceLocation.public_address==self.request.remote_addr)
            q = q.filter(Service.country==self.request.headers['X-AppEngine-country'])
            for ns in q:
                for addr in ns.internal_addresses.split(','):
                    rv.append({'name':ns.name,'uid':ns.uid,'address':addr.strip(), 'port':ns.port})
        self.response.content_type='application/json'
        self.response.write(json.dumps(rv))
        
class RegistrationHandler(RequestHandler):
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
                template = templates.get_template('not-auth.html')
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
            context['apikey'] = ak.apikey
            context['secret'] = ak.secret
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
            srv = NetworkService.query(NetworkService.name==service_type).get()
            if not srv:
                raise ValueError
            sigcheck.update(srv.name)
            sigcheck.update(name)
            sigcheck.update(uid)
            sigcheck.update('%05d'%port)
            for addr in addresses:
                sigcheck.update(addr)
        except (KeyError,ValueError):
            pass
        sigcheck = sigcheck.hexdigest()
        if sigcheck==sig:
            status='ok'
            try:
                location = self.request.headers['X-AppEngine-CityLatLong']
            except KeyError:
                location = '0,0'
            loc = ServiceLocation(key_name=uid,
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
    def get(self):
        self.response.delete_cookie(self.CLIENT_COOKIE_NAME)
        context = self.create_context(title="Unregister this device")
        template = templates.get_template('unregister.html')
        self.response.write(template.render(context))


def parse_services_blob(blob_key, client_id):
    num = { "lines":0, "contacts":0 }
    def contact_progress(lc,cc):
        num["lines"] = lc
        num["contacts"] = cc
        logging.info('contact %s %s'%(str(lc),str(cc)))
    def service_progress(lc,sc):
        channel.send_message(client_id, '{"service_line":%d, "num_services":%d}'%(lc,sc))
        logging.info('service %s %s'%(str(lc),str(sc)))
    blob_reader = blobstore.BlobReader(blob_key)
    contacts = parse_contact_list(blob_reader, contact_progress)
    blob_reader.close()
    channel.send_message(client_id, '{"num_lines":%d, "num_contacts":%d}'%(num["lines"],num["contacts"]))
    logging.info('Found %d contacts, %d lines in file'%(num["contacts"],num["lines"]))
    blob_reader = blobstore.BlobReader(blob_key)
    parse_service_list(blob_reader, contacts=contacts, progress=service_progress)
    blob_reader.close()
    blobstore.delete(blob_key)
        
class NetworkServiceHandler(RequestHandler):
    class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
            
        def post(self):
            context = self.outer.create_context(title="Upload service list")
            upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
            if len(upload_files)==0:
                self.outer.get()
                return
            if self.request.POST.get('wipe'):
                NetworkService.empty_database()
            blob_info = upload_files[0]
            #self.redirect('/serve/%s' % blob_info.key())
            context['channel_token'] = channel.create_channel(self.outer.user.user_id() + 'networkservice')        
            deferred.defer(parse_services_blob,blob_info.key(),self.outer.user.user_id() + 'networkservice')
            template = templates.get_template('networkservice.html')
            self.response.write(template.render(context))
            
    def __init__(self, request, response):
        # Set self.request, self.response and self.app.
        self.initialize(request, response)
        self.upload_handler = self.UploadHandler(request, response)
        self.upload_handler.outer = self
        self.post = self.upload_handler.post
        
    def get(self):
        context = self.create_context(title="Upload service list")
        if not users.is_current_user_admin():
            template = templates.get_template('not-auth.html')
        else:
            template = templates.get_template('networkservice.html')
            context['upload_url'] = blobstore.create_upload_url(self.request.uri)
        self.response.write(template.render(context))
        
#    def post(self):
#        if not users.is_current_user_admin():
#            template = templates.get_template('not-auth.html')
#            self.response.write(template.render(context))
#            return
#        source = self.request.POST.get('file').file
#        taskqueue.add(url=self.url_from("import-worker"))
#        deferred.defer(parse_service_list,source)
#        template = templates.get_template('networkservice.html')
#        self.response.write(template.render(context))
        
            
class ChannelHandler(webapp2.RequestHandler):
    def post(self, *args, **kwargs):
        client_id = self.request.get('from')
        self.response.content_type='application/json'
        self.response.write('{"status":"ok"}')
        