import datetime, decimal, os

from google.appengine.api import apiproxy_stub_map
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import ndb

def flatten(item):
    """Converts an object in to a form suitable for storage.
    flatten will take a dictionary, list or tuple and inspect each item in the object looking for
    items such as datetime.datetime objects that need to be converted to a canonical form before
    they can be processed for storage.
    """
    rv=item
    if isinstance(item,dict):
        rv={}
        for key,val in item.iteritems():
            rv[key] = flatten(val)
    elif isinstance(item,(list,tuple)):
        rv = []
        for val in item:
            rv.append(flatten(val))
        if item.__class__ == tuple:
            rv = tuple(rv)
    elif isinstance(item,ndb.Model):
        field_names = item._properties.keys()
        rv = {} 
        for k in field_names:
            value = getattr(item, k)
            rv[k] = flatten(value)
    elif isinstance(item,ndb.GeoPt):
        rv = {'lat':item.lat, 'lon':item.lon}
    elif isinstance(item,(datetime.datetime,datetime.time)):
        rv = item.isoformat()
        if not item.utcoffset():
            rv += 'Z'
    elif isinstance(item,(datetime.date)):
        rv = item.isoformat()
    #elif isinstance(item,long):
    #    rv = '%d'%item
    elif isinstance(item,(unicode,str,decimal.Decimal)):
        rv = str(item).replace("'","\'")
    elif isinstance(item,(dict,list,tuple)):
        rv = flatten(item)
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
        try:
            return datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            pass
        try:
            return datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%MZ")        
    if not 'Z' in date_time:
        try:
            return datetime.datetime.strptime(date_time, "%Y-%m-%d")
        except ValueError:
            return datetime.datetime.strptime(date_time, "%d/%m/%Y")
    return datetime.datetime.strptime(date_time, "%H:%M:%SZ").time()


#
# The following code is from djangoappengine/utils.py
#
have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

#if have_appserver:
#    appid = get_application_id()
#else:
#    try:
#        from google.appengine.tools import dev_appserver
#        from .boot import PROJECT_DIR
#        appconfig = dev_appserver.LoadAppConfig(PROJECT_DIR, {},
#                                                default_partition='dev')[0]
#        appid = appconfig.application.split('~', 1)[-1]
#    except ImportError, e:
#        raise Exception("Could not get appid. Is your app.yaml file missing? "
#                        "Error was: %s" % e)

on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')
