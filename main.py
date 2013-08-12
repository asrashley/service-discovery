#!/usr/bin/env python
#
import logging
import webapp2

import views
from routes import routes
from settings import DEBUG

webapp_routes = []
for name,route in routes.iteritems():
    webapp_routes.append(webapp2.Route(template=route.template, handler=route.handler, name=name))
    
app = webapp2.WSGIApplication(webapp_routes, debug=DEBUG)
