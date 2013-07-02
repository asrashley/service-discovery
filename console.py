#!/usr/bin/python
import sys
APP_ENGINE='c:/Program Files (x86)/Google/google_appengine/'

sys.path.append(APP_ENGINE)
sys.path.append(APP_ENGINE+"lib/yaml/lib")
sys.path.append(APP_ENGINE+"lib/django_1_3")
sys.path.append(APP_ENGINE+"lib/fancy_urllib")
sys.path.append(APP_ENGINE+"lib/webob")
sys.path.append(APP_ENGINE+"lib/simplejson")

import os
import code
import getpass
import datetime
import logging

logging.disable(10) # disable debugging logs

#import setup_django_version
from google.appengine.ext import db
from google.appengine.ext.remote_api import remote_api_stub


def auth_func():
    return raw_input('Username:'), getpass.getpass('Password:')


def log_to_console(str):
    import inspect
    date = datetime.datetime.now()
    module = inspect.stack()[1][3]
    print ("%s %s] %s" % (date, module, str))

DEFAULT_APP_ID = 'service-discovery'

app_id = DEFAULT_APP_ID
host = DEFAULT_APP_ID + '.appspot.com'

if len(sys.argv) > 1 and sys.argv[1] != '':
    input_app_id = sys.argv[1]
    if input_app_id in ('local', 'localhost'):
        host = 'localhost:9080'
        auth_func = lambda: ('test@example.com', '')
    else:
        app_id = input_app_id
        host = input_app_id + '.appspot.com'


if __name__ == "__main__":

    # set logging to console
    logging.info = logging.error = logging.warn = logging.exception = log_to_console

    # Always use UTC here so entities timestamps get updated with UTC
    os.environ['TZ'] = 'UTC'

    remote_api_stub.ConfigureRemoteDatastore(None, '/_ah/remote_api', auth_func, host)

    namespace = locals().copy()
    banner = '\033[92m\nApp Engine interactive console for %s \033[0m' % app_id

    #try:
    #    from IPython.Shell import IPShellEmbed
    #    ipshell = IPShellEmbed(user_ns=namespace, banner=banner)
    #    ipshell()
    #except:
    #    from IPython.frontend.terminal.interactiveshell import TerminalInteractiveShell
    #    shell = TerminalInteractiveShell(user_ns=namespace)
    #    shell.mainloop()
    #else:
    code.interact(banner, None, namespace)