#!/usr/bin/env python
#
import webapp2

import views
    
app = webapp2.WSGIApplication([
    webapp2.Route(r'/discover/<service_type:[\w\-_\.]+>/', handler=views.SearchHandler, name="search"),
    webapp2.Route(r'/discover', handler=views.SearchHandler, name="search"),
    webapp2.Route(r'/unregister/<key:[\w\-]+>', handler=views.UnregistrationHandler, name="deregister"),
    webapp2.Route(r'/unregister', handler=views.UnregistrationHandler, name="unregister"),
    webapp2.Route(r'/register/<reg_type:\w+>', handler=views.RegistrationHandler, name="register"),
    webapp2.Route(r'/services/search', handler=views.NetworkServiceSearch, name="services-ajax"),
    webapp2.Route(r'/services/add', handler=views.EditNetworkService, name="add-service"),
    webapp2.Route(r'/services/<service_type:[\w\-_\.]+>/edit', handler=views.EditNetworkService, name="edit-service"),
    webapp2.Route(r'/services/upload', handler=views.UploadServiceList, name="upload-services"),
    webapp2.Route(r'/work/import', handler=views.ImportWorker, name="import-worker"),
    webapp2.Route(r'/work/maintenance', handler=views.MaintenanceWorker, name="maintenance"),
    webapp2.Route(r'/registered/', handler=views.RegistrationList, name="registered"),
    webapp2.Route(r'/_ah/channel/<:(dis)?connected>/', handler=views.ChannelHandler, name="channel"),
    webapp2.Route(r'/log/', handler=views.Logging, name="logging"),
    webapp2.Route(r'/log/<date:\d{4}-\d+-\d+>/', handler=views.Logging, name="log-by-date"),
    #UID 4d9cf5f4-4574-4381-9df3-1d6e7ca295ffe
    webapp2.Route(r'/log/<uid:[0-9a-f]+-[0-9a-f]+-[0-9a-f]+-[0-9a-f]+-[0-9a-f]+>/', handler=views.Logging, name="log-by-uid"),
    webapp2.Route(r'/', handler=views.MainPage, name="home"),
], debug=True)
