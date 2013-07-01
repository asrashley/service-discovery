#!/usr/bin/env python
#
import webapp2

import views
    
app = webapp2.WSGIApplication([
    webapp2.Route(r'/', handler=views.MainHandler, name="home"),
    webapp2.Route(r'/discover/<service_type:[\w\-_\.]+>', handler=views.SearchHandler, name="search"),
    webapp2.Route(r'/discover', handler=views.SearchHandler, name="search"),
    webapp2.Route(r'/unregister', handler=views.UnregistrationHandler, name="unregister"),
    webapp2.Route(r'/register/<reg_type:\w+>', handler=views.RegistrationHandler, name="register"),
    webapp2.Route(r'/services', handler=views.NetworkServiceHandler, name="services"),
    webapp2.Route(r'/services/search', handler=views.NetworkServiceSearch, name="services-ajax"),
    #webapp2.Route(r'/work/import', handler=views.ImportWorker, name="import-worker"),
    webapp2.Route(r'/_ah/channel/<:(dis)?connected>/', handler=views.ChannelHandler, name="channel"),
], debug=True)
