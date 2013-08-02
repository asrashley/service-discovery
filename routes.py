#import views

class Route(object):
    def __init__(self,template,handler,title,parent=None):
        self.template=template
        self.handler=handler
        self.title=title
        self.parent=parent

routes = {
    "search-by-type":Route(r'/discover/<service_type:[\w\-_\.]+>/', handler='views.SearchHandler', parent="search", title="Search by type"),
    "search":Route(r'/discover', handler='views.SearchHandler', parent="home", title="Search for devices"),
    "deregister":Route(r'/unregister/<key:[\w\-]+>', handler='views.UnregistrationHandler', parent="home", title="Unregister a device"),
    "unregister":Route(r'/unregister', handler='views.UnregistrationHandler', parent="home", title="Unregister this device"),
    "register":Route(r'/register/<reg_type:\w+>', handler='views.RegistrationHandler', parent="home", title="Register this device"),
    "services-ajax":Route(r'/services/search', handler='views.NetworkServiceSearch', parent="home", title="Services"),
    "add-service":Route(r'/services/add', handler='views.EditNetworkService', parent="home", title="Add a service"),
    "edit-service":Route(r'/services/<service_type:[\w\-_\.]+>/edit', handler='views.EditNetworkService', parent="home", title="Edit service"),
    "upload-services":Route(r'/services/upload', handler='views.UploadServiceList', parent="home", title="Upload service list"),
    "import-worker":Route(r'/work/import', handler='views.ImportWorker', parent="home", title="import"),
    "maintenance":Route(r'/work/maintenance', handler='views.MaintenanceWorker', parent="home", title="maintenance"),
    "registered":Route(r'/registered/', handler='views.RegistrationList', parent="home", title="Registered devices"),
    "channel":Route(r'/_ah/channel/<:(dis)?connected>/', handler='views.ChannelHandler', parent="home", title="channel"),
    "logging":Route(r'/logs/', handler='views.Logging', parent="home", title="Discovery logs"),
    "all-logs":Route(r'/logs/event_logs', handler='views.LoggingAPI', parent="home", title="Discovery logs"),
    "log-by-id":Route(r'/logs/event_logs/<id:[\w\-]+>', handler='views.LoggingAPI', parent="home", title="Discovery logs"),
    "log-by-date":Route(r'/logs/event_logs/date/<date:\d{4}-\d+-\d+>', handler='views.LoggingAPI', parent="logging", title="Logs for date"),
    #UID 4d9cf5f4-4574-4381-9df3-1d6e7ca295ffe
    "log-by-uid":Route(r'/logs/event_logs/uid/<uid:[0-9a-f]+-[0-9a-f]+-[0-9a-f]+-[0-9a-f]+-[0-9a-f]+>', handler='views.LoggingAPI', parent="logging", title="Logs for UUID"),
    "home":Route(r'/', handler='views.MainPage', title="Service discovery"),
}

for name,r in routes.iteritems():
    r.name = name 