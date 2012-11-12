#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
#from google.appengine.ext import db
#from google.appengine.api import memcache
#from google.appengine.api import images
#from gdb.models import SuiGoods,MediaStore
import helper
from main import WebRequest

class PayRequest(WebRequest):
    """ Request handler for /pay/buysus and other https notifications from GC or PP """
    def post(self):
        logging.info('in PayRequest.post')
        self.response.headers.add_header('Access-Control-Allow-Origin', 'http://suicomics.appspot.com')
        WebRequest.post(self)
        
    def options(self,*args,**kwargs):
        self.post(*args,**kwargs)
        self.response.clear()
        
def main():
    handlers = [('.*',PayRequest)]
    
    app = webapp.WSGIApplication(handlers, debug=True)
    run_wsgi_app(app)

if __name__ == '__main__':
    main()
