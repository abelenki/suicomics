#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "$Revision: 1 $"
# $Source$

import logging, time, cgi, hashlib, os, base64, re, hmac, urllib
from datetime import datetime, timedelta

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import taskqueue
from google.appengine.api.memcache import get as from_cache,set as to_cache,delete as decache

from templite import render_text, jsonize
import helper

# change to use Facebook OpenGraph
import facebook
FACEBOOK_APP_ID = "" #Suinova Comics (suicomics.appspot.com)
FACEBOOK_APP_SECRET = ""
FACEBOOK_API_KEY = ""

COOKIE_SECRET = '5121acea344842ee835824525f0ba807'  #from uuid.uuid4()

SNSES = ['fb','gg','ms','web']

realpath = os.path.dirname(__file__)

class PermitException(Exception):
    pass

class BaseRequest(webapp.RequestHandler):
    """ Common POST or GET request handler.
    This is platform-independent. Facebook requests use FacebookRequest class derived from this class.
    Another derived class AdminRequest is used for admin operations.
    User authentication is done in the derived class initialization phase.
    This design allows for extending the services to other networks such as Bebo etc.
    All concrete operations will be implemented in separate modules such as party.py and
    the functions are dynamically called in a RPC fashion. For example,
    /fb/patch/plant?p=PatchKey&s=SeedKey
    will call plant(BaseRequest) function in module patch.py. This module will be loaded
    first time used in the Python interpreter.
    The user object is created in the initialization method after authentication, and
    accessible as self.user in the module functions through the web parameter.
    The web parameter is BaseRequest->webapp.RequestHandler in this case.
    It is App Engine determined, but can be redefined if porting to other web servers.
    The basic attributes used include BaseRequest.user, BaseRequest.sns (fb),
    and operations include BaseRequest.renderPage, BaseRequest.addVar, 
    and webapp.RequestHandler.request.get[_all], webapp.RequestHandler.response.out. 
    """
    def post(self):
        """ Facebook requests are POST requests.
        REST-style requests are formatted as:
        /[fb|gg|web|admin]/[module]/[function][/REST_terms/..]?[name=value&...]
        """
        paths = self.parse_path(self.request.path)
#        logging.debug(paths)
        module_name = paths['module']
        function_name = paths['function']
        try:
            mod = __import__(module_name)   # the modules will be loaded only once whatsoever
        except ImportError:
            msg = 'Module "%s" not found' % module_name
            logging.error(msg)
            self.response.out.write(msg)
            return
        except DeadlineExceededError,e:
            logging.error('Module "%s" caused DeadlineExceededError' % module_name)
            self.response.clear()
            self.response.out.write('%s (Please retry later)'%e)
            return
        #params = dict((k,self.request.get(k)) for k in self.request.arguments())
        #logging.debug('post params=%s'%params)
        try:
            if hasattr(mod, function_name):
                getattr(mod, function_name)(self, paths['args'])    #mod.func(web,arg_list=None)
            else:
                getattr(mod, 'default')(self, [function_name] + paths['args'])
        except DeadlineExceededError,e:
            logging.error('Module "%s.%s" caused DeadlineExceededError' % (module_name, function_name))
            self.response.clear()
            self.response.out.write('%s (Please retry later)'%e)
            return
        except PermitException,e:
            self.fail(str(e))
        except Exception,e:
            logging.exception(e)
            self.fail(str(e))
        #else:
            #msg = 'Module "%s" has no function "%s"' % (modname,funcname)
            #logging.error(msg)
            #self.response.out.write(msg)
            
    def get(self):
        """ Admin uses GET requests.
        /admin/[module]/[function]?[name=value&...]
        """
        if self.request.path.startswith('/admin'):
            self.post()
        else:
            self.response.out.write('GET is not allowed')
    
    def parse_path(self,path):
        """ Parse request.path to get sns, module, function, and arguments.
            If no module is given, it uses 'home', if no function is given, it uses 'default'.
            sns is also optional, if included, it's the first term, and module the next and function follows.
            @return {'module':mod,'function':func,'sns':sns,'args':args}
        """
        mod = func = sns = None
        args = []
        for s in path.split('/'):
            if s == '': continue
            if mod is None:
                if s not in SNSES:  #['fb','gg','ms','web']
                    mod = s
                else:
                    sns = s
            elif func is None:
                func = s
            else:
                args.append(s)
        if mod is None: mod = 'home'
        if func is None: func = 'default'
        return {'module':mod,'function':func,'sns':sns,'args':args}
        
    def get_param(self,pname,default=None):
        """ Returns the value for a request parameter. 
        @param pname: parameter key
        @param default: return it if pname is empty, or if None and key's value is '', raise exception, else returns default
        @raise Exception if default is None and pname not given
        """
        v = self.request.get(pname)
        if v == '':
            if default is None:
                raise Exception('Param %s not given'%pname)
            return default
        return v
        
    def get_params(self,pname):
        """ Returns a list of values for a parameter or a list of parameters. """
        if isinstance(pname,list):
            return [self.request.get(k) for k in pname]
        return self.request.get_all(pname)
    
    def get_var(self, vname):
        """ Returns the value of a variable in self.tempvars, or None if not found """
        if vname in self.tempvars:
            return self.tempvars[vname]
        else:
            return None
        
    def add_var(self, kod, val=None):
        """ Add a key:value pair or a dict of key:value pairs.
        @param kod: key str or dict
        @param val: value str or None for k=dict 
        """
#        logging.info('add_var: k,v=%s,%s'%(kod,val))
        if not hasattr(self,'tempvars') or self.tempvars is None: 
            self.tempvars = {}
        if isinstance(kod, dict):
#            logging.info('kod is dict')
            for k,v in kod.items():
                self.tempvars[k] = v
        elif val is not None:
#            logging.info('kod,val')
            self.tempvars[kod] = val
        #logging.info('add_var: k=%s,v=%s'%(kod,self.tempvars[kod]))
        
    def succeed(self, result=None):
        """ Return successful JSON data to the client.
        """
        if result is None:
            self.response.out.write('{"RE":"OK"}')
        elif isinstance(result, dict):
            result['RE'] = 'OK'
            self.response.out.write(jsonize(result))
        elif isinstance(result, list):
            self.response.out.write(jsonize(result))
        elif isinstance(result, basestring):
            self.response.out.write(result)

    def fail(self, msg=None, format='JSON', page='error.html'):
        """ Return a failure message to the client. If use error.html, replace {{ error }} with msg.
        @param msg: message text to return or None, can also be a dict with 'error' in it.
        @param format: JSON or HTML to return
        @param page: error.html by default for format=='HTML'
        @return: {"error":"msg"} #{'RE':'Fail',msg:'...'} 
        """
        if format == 'JSON':
            if msg:
                if isinstance(msg,basestring):
                    err = '{"error":"%s"}'%msg
                else:
                    err = jsonize(msg)
            else:
                err = '{"error":"Unknown error"}'
            self.response.out.write(err)
        elif format == 'HTML':
            if page == '':
                logging.error('main.fail(): page not given')
                return
            if msg: self.add_var('error',msg)
            self.render_page(page)
    
    def redirect_with_msg(self, msg, path=''):
        """ Redirect to page path with a msg before relocating the page. """
        if path.startswith('/'): path = path[1:]
        self.response.out.write('<html><head><meta http-equiv="refresh" content="3;url=/%s"></head><body><h3>%s</h3>Jump in 3 seconds.</body></html>'%(path,msg))
        
    def render_page(self, page, render=True, vars=None):
        """ Return an html page to the client.
        @param page: html page file name without path or .html
        @param render: if False, return file directly, if True, substitute variables with their values in the page by the template engine Templite.
        @param vars: additional variable dict in addition to self.tempvars.
        """
        if not page:
            logging.error('main.return_page error: page is None')
            raise Exception('Invalid parameter page')
        if page.find('.') < 0:
            page = '%s.html' % (page)
        path = os.path.join(realpath, page)
        try:
            import codecs
            fi = codecs.open(path,'r','utf-8')
            text = fi.read()
            fi.close()
        except:
            logging.error('render_page(%s) file not found'%path)
            self.response.out.write('File open error')
            return
        if render:
            if vars:
                if isinstance(vars,dict):
                    self.tempvars.update(vars)
                else:
                    logging.error('render_page error: vars is not dict')
            #logging.info('self.tempvars: %s' % self.tempvars)
            render_text(text,self.tempvars,self.response.out)
        else:
            self.response.out.write(text)

    @property
    def logged_in(self):
        return hasattr(self,'user') and self.user
    
    def require_login(self):
        """ Returns nothing if user logged in, else raises an exception. """
        if not self.logged_in:
            raise PermitException('Login required')
        
    def require_author(self):
        """ Returns nothing if user logged in as an Author, else raises an exception. """
        self.require_login()
        if not self.user.isAuthor():
            raise PermitException('Author only')
        
    def require_admin(self):
        """ Returns nothing if user is admin, else raises an exception. """
        self.require_login()
        #self.require_author()
        from google.appengine.api import users
        if not users.is_current_user_admin():
            raise Exception('Admin only')   #will log this behavior to see who did this
    
    
REDIRECT_HTML='''<html><head><meta http-equiv="refresh" content="0;url=/">
</head><body onload="javascript:location.replace('%s')"></body></html>
'''
FACEBOOK_LOGIN0="""<html><head></head><body><fb:login-button perms="email,status_update,publish_stream"></fb:login-button><div id="fb-root"></div>
<script>
  window.fbAsyncInit = function() {
    FB.init({appId: '%s', status: true, cookie: true, xfbml: true});
    FB.Event.subscribe('auth.login',function(response){
        var browser = navigator.userAgent.toLowerCase();
        if (browser.indexOf('safari') > 0 && browser.indexOf('chrome') < 0){
        //alert('safari');
            var d=document.getElementsByTagName('body')[0];
            var dv=document.createElement('div');
            dv.innerHTML='<form id="sessionform" enctype="application/x-www-form-urlencoded" action="http://suicomics.appspot.com/fb/" action="post"></form>';
            d.appendChild(dv);
            var f=document.getElementById('sessionform');
            f.submit();
        }else
          window.top.location = 'http://apps.facebook.com/suicomics';
    });
  };
  (function(){
    var e = document.createElement('script');
    e.type = 'text/javascript';
    e.src = document.location.protocol + '//connect.facebook.net/en_US/all.js';
    e.async = true;
    document.getElementById('fb-root').appendChild(e);
  }());
</script></body></html>"""%FACEBOOK_APP_ID
FACEBOOK_LOGIN='''<html><head>
<script>
window.top.location = "https://graph.facebook.com/oauth/authorize?client_id=179008415461930"
+"&redirect_uri=http://apps.facebook.com/suicomics/";
</script>
</head></html>
'''

def padtrans(b64s):
    """ Add = padding to multiple of 4.
        And replace - with +, _ with /
    """
    n = 4 - len(b64s) % 4 & 3
    return b64s.replace('-','+').replace('_','/') + '='*n
    
PTN = re.compile(r'"([^"]+)"\s?:\s?"?([^"}]+)"?')
def parse_signed_request(signed_request, secret):
    """ Parse Facebook OAuth 2.0 signed_request.user_id,oauth_token,expires,profile_id(on profile_tab)
    """
    encoded_sig, payload = signed_request.split('.')
    sig = base64.b64decode(padtrans(encoded_sig))
    datas = base64.b64decode(padtrans(payload))
    data = dict((k,v) for k,v in PTN.findall(datas))
    if data['algorithm'].upper() != 'HMAC-SHA256':
        logging.error('parse_signed_request error, hmac-sha256 expected')
        return None
    expected_sig = hmac.new(secret, msg=payload, digestmod=hashlib.sha256).digest()
    if expected_sig != sig:
        logging.error('parse_signed_request error: bad signature')
        return None
    return data
    
class FacebookRemove(webapp.RequestHandler):
    def post(self):
        logging.info('FacebookRemove.post: received a Deauthorize Call')
        sr = self.request.get('signed_request')
        if sr:
            data = parse_signed_request(sr, FACEBOOK_APP_SECRET)
            logging.debug('FacebookRemove.post: data=%s'%data)
            if 'user_id' in data:
                uid = data['user_id']
                ukey = 'fb_%s'%uid
                logging.debug('De-authorizing FB user %s'%uid)
                helper.unregister_user(ukey)
            else:
                logging.warning('No user_id in signed_request for /fb/remove callback')
        else:
            logging.error('FB /fb/remove without signed_request')
            
class FacebookRequest(BaseRequest):
    """ Web Request Handler for Facebook requests with URL as /fb/*.
    User is authenticated through Facebook connection, and stored in the database
    if first time.  Once the user login, the self.user object is created.
    self.sns is set to 'fb' and can be used as path '/fb/'. 
    """
    def initialize(self, request, response):
        """ Check cookies, load user session before handling requests. Necessary here? can be merged into POST or GET.
        """
        webapp.RequestHandler.initialize(self, request, response)
        if self.request.get('use') == 'gift':
            self.authorize()
            return
        sr = self.request.get('signed_request')
        if sr:
            data = parse_signed_request(sr, FACEBOOK_APP_SECRET)
            logging.debug('FacebookRequest.initialize: signed_request = %s'%data)
            if data:
                if 'oauth_token' not in data:
                    logging.debug('FacebookRequest.initialize: signed_request has no oauth_token, redirect to oauth/authorize')
                    self.authorize()
                    return
                else:
                    logging.debug('FacebookRequest.initialize: ready to login')
                    self.login(data['user_id'],data['oauth_token'])
            else:
                logging.debug('FacebookRequest.initialize: Bad signed_request, return home page without login')
        else:
            fbcookie = facebook.get_user_from_cookie(self.request.cookies, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
            if fbcookie:
                logging.debug('FacebookRequest.initialize: fbcookie = %s'%fbcookie)
                self.login(fbcookie['uid'],fbcookie['access_token'])
            else:
                code = self.request.get('code')
                if code:
                    logging.debug('FacebookRequest.initialize: got code from oauth-authorize exchange for access_token')
                    aargs={'client_id':FACEBOOK_APP_ID,'client_secret':FACEBOOK_APP_SECRET,'code':code,'redirect_uri':self.request.path_url}
                    response = cgi.parse_qs(urllib.urlopen("https://graph.facebook.com/oauth/access_token?"+urllib.urlencode(aargs)).read())
                    logging.debug('FacebookRequest.initialize: response from oauth/access_token: %s'%response)
                    if response and 'access_token' in response:
                        access_token = response["access_token"][-1]
                        graph = facebook.GraphAPI(access_token)
                        profile = graph.get_object('me')
                        logging.debug('FacebookRequest.initialize: got graph profile of me:%s'%profile)
                        self.login(profile['id'],access_token)
                    else:
                        logging.debug('FacebookRequest.initialize: Bad result from oauth/access_token, return home page without login')
                else:
                    logging.debug('FacebookRequest.initialize: no code, try oauth/authorize')
                    self.authorize()
                    
    def authorize(self):
        use = self.request.get('use')
        scope = 'email,status_update,publish_stream'
        ex = ''
        if use == 'gift':
            logging.debug('FacebookRequest.authorize: use=gift')
            scope += ',friends_birthday,offline_access'
            ex = 'gift/permit'
        self.get = self.post = (lambda *args: None)
        #args={'client_id':FACEBOOK_APP_ID,'redirect_uri':self.request.path_url,'scope':'email,status_update,publish_stream'}
        #self.redirect('https://graph.facebook.com/oauth/authorize?'+urllib.urlencode(args))
        args={'client_id':FACEBOOK_APP_ID,'redirect_uri':'http://apps.facebook.com/suicomics/%s'%ex,'scope':scope}
        fbs='''<script>top.location="https://graph.facebook.com/oauth/authorize?%s";</script>'''%urllib.urlencode(args)
        self.response.out.write(fbs)
        
    def login(self,uid,access_token):
        """ Login routine.
            From FacebookRequest: login(facebook_uid
        """
        self.sns = 'fb'
        ukey = '%s_%s' % (self.sns, uid)
        u = helper.from_cache(ukey)
        if not u:
            u = helper.get_user_by_key(ukey,False) #memcache=False
            if not u:
                graph = facebook.GraphAPI(access_token)
                profile = graph.get_object('me')
                u = helper.create_user(ukey,profile['name'],profile.get('email',None),False)    #save=False
                if not u:
                    logging.error('FacebookRequest.login: helper.create_user failed')
                    self.redirect_with_msg('Server in maintenance, please try later, thank you.')
                    self.get = self.post = (lambda *args: None)
                    return
                u.access_token = access_token
                u.save()
                logging.debug('FacebookRequest.login: New User %s saved'%ukey)
            else:
                now = datetime.utcnow()
                u._cache_time = now
                if helper.to_cache(ukey, u, helper.PLAYER_CACHE_SECS): #2 hours, if memcache fails, do not task/dau or send_email
#                    if u.lastime.day != now.day or u.lastime.month != now.month:
#                        taskqueue.add(url='/task/dau',params={'usr':ukey,'act':'login'})
                    taskqueue.add(url='/task/dau',params={'usr':ukey,'act':'login'})
                    if ukey not in ['fb_669391906','fb_1464710918','fb_1842536962','fb_1831016858']:
                        helper.send_email('Login SuiComics: %s(%s) @ %s'%(u.name,ukey,now), 'OK')
                    else:
                        helper.send_email('Login SuiComics: %s(%s) @ %s'%(u.name,ukey,now), 'OK - to remove this')
        else:
            #got user from memcache
            if u.access_token != access_token:
                u.access_token = access_token
                u.save()
                logging.debug('FacebookRequest.login: access_token updated while %s still in memcache'%ukey)
            elif hasattr(u,'_cache_time'):
                if (datetime.utcnow()-u._cache_time).seconds >= 3600:
                    u._cache_time = datetime.utcnow()
                    helper.to_cache(ukey, u, helper.PLAYER_CACHE_SECS)
        if self.request.headers.get('User-Agent','').find('MSIE')>=0:
            #logging.debug('addHeader P3P for MSIE')
            #self.response.headers.add_header('P3P','CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi IVDi CONi HIS OUR IND CNT"')
            self.response.headers.add_header('P3P','CP="SuiComics"')
        args = get_session_from_cookie(self.request.cookies)
        if not args or args['uid'] != ukey:
            put_cookie(self.response.headers, ukey, u.token, self.sns)
        self.user = u
        self.tempvars = {'user':u,'sns':'fb','login':True,'uname':u.name,'onFacebook':True}
        if self.request.get('ref')=='bookmarks':
            c = self.request.get('count')
            if c != '0':
                helper.clear_fb_count(uid)
            
    def get(self):
        self.post()
        
    def jsondict(self,json):
        """ Make a dict out of simple dict in JSON, only string and int allowed, string does not contain comma or }. """
        ptn = re.compile(r'"(\w+)":\s*([^,}]+)')
        data = {}
        for k,v in ptn.items():
            if v.startswith('"'):
                data[k] = v.strip('"')
            else:
                data[k] = int(v)
        return data

    def handle_order(self):
        """ This is the routine to handle user payment transactions from facebook.
        """
        signed_request = parse_signed_request(self.request.get('signed_request'), FACEBOOK_APP_SECRET)
        if not signed_request:
            logging.warning('fb/order: invalid signed_request')
            web.fail('Unauthorized request')
            return
        logging.debug('/fb/order: signed_request = %s'%signed_request)
        payload = signed_request['credits']
        order_id = payload['order_id']
        method = self.request.get('method')
        data = {'content':[]}
        if method == 'payments_get_items':
            order_info = payload['order_info']
            logging.debug('/fb/order: order_info=%s'%order_info)
            item = self.jsondict(order_info)
            logging.debug('self.jsondict: parsed item=%s'%item)
            item['price'] = int(item['price'])
#            if not item['product_url'].startswith('http://'):
#                item['product_url'] = 'http://%s' % item['product_url']
#            if not item['image_url'].startswith('http://'):
#                item['image_url'] = 'http://%s' % item['image_url']
#            if 'test_mode' in payload:
#                item['title'] = '[Test Mode] %s' % item['title']
#                item['description'] = '[Test Mode] %s' % item['description']
            data['content'].append(item)
            return_value = {"content":[{"title":"",
                "description":"",
                "item_id":"",
                "image_url":"",
                "product_url":"",
                "price":10,
                "data":""}],
                "method":"payments_get_items"}
        elif method == 'payments_status_update':
            #get: order_id (int),status:(placed,reserved,settled,canceled),order_details:
            status = payload['status']
            ret = {'order_id':order_id}
            if status == 'placed':
                ret['status'] = 'settled'
            elif status == 'settled':
                #save user purchase transaction here
                logging.debug('/fb/order: settled status received, about to save transaction')
                order_info = payload['order_info']
                item = self.jsondict(order_info)
                logging.debug('/fb/order: status=%s,item=%s'%(status,item))
                import pay
                data = {'quantity':1,'price':item['price'],'item_id':item['item_id'],'buyer':item['data'],'currency':'FC','method':'FC','order_number':order_id}
                logging.debug('/fb/order: save_exchange, data=%s'%data)
                pay.save_exchange(buyer, datetime.utcnow(), 0, data)
                ret['status'] = 'settled'
            elif status == 'refunded':
                logging.warning('fb sent refunded')
            data['content'].append(ret)
        data['method'] = method
        logging.debug('/fb/order: returning back to fb:%s'%data)
        web.succeed(data)

class GoogleRequest(BaseRequest):
    """ Google Request handler for public Web requests /gg/*.
        The idea is that, by default the root request goes to WebRequest handler, and once user chooses login via Google,
        it redirects to /gg/home location and processed by this class. After user logged in, set the cookie and let the
        browser refreshes the location to / again and the WebRequest will load the logged in user according to the cookie.
        If user logged in via Google account, it will return a cookie and redirect to / home.
        If user not logged in, it will redirect to Google login page.
        This requires user has a Google account.
        TODO: how to use Google contact etc for social event.
    """
    def initialize(self, request, response):
        """ Authenticate through Google account.
        """
        webapp.RequestHandler.initialize(self, request, response)
        from google.appengine.api import users
        user = users.get_current_user()
        if not user:
            logging.debug('GoogleRequest.initialize: not login, redirect to /gg')
            self.redirect(users.create_login_url("/gg/home"))
            self.get = (lambda *args: None)
            self.post = (lambda *args: None)
        else:
            #user logged in google account,check our cookie
            sns = 'gg'  #Google: how to make use of GMail contact, chat etc? via OAuth
            uid = '%s_%s' % (sns, user.user_id())
            logging.debug('GoogleRequest.initialize: %s visit via Google, try login'%uid)
            su = helper.from_cache(uid)
            if not su:
                su = helper.get_user_by_key(uid,False)  #no memcache
                if su is None:
                    logging.debug('GoogleRequest.initialize: New user, try create')
                    em = user.email()
                    name = em[:em.find('@')]
                    su = helper.create_user(uid, name, em)  #auto cached if successful
                    if su is None:
                        logging.error('GoogleRequest.initialize: create_user(%s,%s,%s) failed'%(uid,name,em))
                        self.response.out.write('Server in maintenance, please come back later. Thank you.')
                        self.get = self.post = (lambda *args: None) #stop calling request handler
                        return
                else:
                    logging.debug('GoogleRequest.initialize: new session today, try cache')
                    su._cache_time = datetime.utcnow()
                    if helper.to_cache(uid, su, helper.PLAYER_CACHE_SECS):
                        logging.debug('GoogleRequest.initialize: Memcached, task dau and send email to admin')
                        taskqueue.add(url='/task/dau',params={'usr':uid,'act':'login'})
                        #if uid not in ['gg_109722387073140662444','gg_108772542023352813713']:
                        helper.send_email('Login SuiComics: %s(%s) @ %s'%(su.name,uid,datetime.utcnow()), 'OK')
            else:
                #in memcache
                logging.debug('GoogleRequest.initialize: in memcache, revisit')
                if hasattr(su,'_cache_time'):
                    if (datetime.utcnow()-su._cache_time).seconds >= 3600:
                        su._cache_time = datetime.utcnow()
                        helper.to_cache(uid, su, helper.PLAYER_CACHE_SECS)
            self.tempvars = {'user':su,'sns':'gg','login':True,'uname':su.name,'onFacebook':False}
            args = get_session_from_cookie(self.request.cookies)
            if not args:
                put_cookie(self.response.headers, uid, su.token, sns)    #a generated random token
            else:
                self.tempvars.update(args)  #['sns','uid','token']
            self.sns = sns
            self.user = su

    def get(self):
        """ Get for direct access. """
        self.post()
        
class AdminRequest(GoogleRequest):
    """ Web Request Handler for Admin requests with URL as /admin/*.
    """
    def initialize(self, request, response):
        """ authenticate Admin through Google User.
        """
        GoogleRequest.initialize(self, request, response)
        from google.appengine.api import users
        user = users.get_current_user()
        if not users.is_current_user_admin():
            url = users.create_logout_url('/')
            greeting = ("Admin only. (<a href=\"%s\">Sign out</a> and retry)" % url)
            self.response.out.write(greeting)
            self.get = (lambda *args: None)
            self.post = (lambda *args: None)
        else:
            self.add_var('admin',True)
            self.admin = True

MIME = {'png':'image/png','jpg':'image/jpeg','gif':'image/gif','swf':'application/x-shockwave-flash','mid':'audio/mid','mp3':'audio/mpeg','jpeg':'image/jpeg'}
class MediaReader(webapp.RequestHandler):
    """ Fetch images etc from MediaStore by key_name. """
    def get(self):
        """ get an image etc. by Key string.
        /mm/filename.jpg?v=1.0 a filename.
        """
        fname = self.request.path[self.request.path.rfind('/')+1:]
        if fname.find('.') > 0: 
            fname = fname[:fname.find('.')]
        if fname.find('?') > 0: 
            fname = uc[:fname.find('?')]
        ie = helper.load_media(fname)
        if ie:
            self.response.headers['Content-Type'] = MIME[ie.format]
            self.response.out.write(ie.stream)
        elif fname.startswith('u_'):
            #return default user logo
            fname = 'avatar_1'
            ie = helper.load_media(fname)
            self.response.headers['Content-Type'] = MIME[ie.format]
            self.response.out.write(ie.stream)
            #self.redirect('/img/avatar.png')
        else:
            self.error(400)

def put_cookie(headers,uid,token,sns):
    """ Create a session cookie after login onto the client browser so that the server will know who is the user during this session.
        Set-Cookie: SC_Session="uid=FB1234&token=xxxx.3333_22xx&sns=fb&expires=2134353.3443&sig=abdf3434"; expires=Fri, 01 Jan 2010 11:48:41 GMT; path=/;
        Note that sig = md5(expires=dddddtoken=xxxxxuid=xxxxxCOOKIE_SECRET), is used to verify this cookie is from this server without tampering.
        @param headers : self.response.headers
        @param uid : like FB1234353455
        @param token : server generated token string, can be the access_token from FB
    """
    xt = datetime.utcnow() + timedelta(hours=2)
    session_vars = {'uid':uid,'token':token,'sns':sns,'expires':int(time.time())+7200}
    s = ''.join('%s=%s'%(k,session_vars[k]) for k in sorted(session_vars.keys()))
    sig = hashlib.md5(s + COOKIE_SECRET).hexdigest()
    session_vars['sig'] = sig
    sg_session = '&'.join('%s=%s'%(k,v) for k,v in session_vars.items())
    cookies = 'SC_Session="%s"; expires=%s; path=/;' % (sg_session, xt.strftime('%a, %d %b %Y %H:%M:%S GMT'))
    logging.info('put_cookie: %s'%cookies)
    headers.add_header('Set-Cookie', cookies)
    
def delete_cookie(headers,cookies):
    """ Call this with delete_cookie(self.response.headers,self.request.cookies)
    """
    cookie = cookies.get('SC_Session','')
    if cookie:
        xt = datetime.utcnow() - timedelta(hours=2)
        cookie = 'SC_Session="uid=&token=&sns=&expires=%d"; expires=%s; path=/;'%(int(time.time())-7200,xt.strftime('%a, %d %b %Y %H:%M:%S GMT'))
        headers.add_header('Set-Cookie',cookie)
    
def get_session_from_cookie(cookies):
    """ Check whether there is session cookie issued by this module after user login through a SNS such as Facebook.
        Cookie: SC_Session="uid=FB1234&token=xxxx.3333_22xx&expires=2134353.3443&sig=abdf3434";
    """
    cookie = cookies.get('SC_Session','')
    if not cookie:
#        logging.debug('get_session_from_cookie, no cookie SC_Session')
        return None
    return parse_session(cookie)

def get_session_from_request(request):
    """ Check whether session data are in request parameters. This method is used by Flash clients.
        The cookie text is the same, but in SC_Session="uid=xxx&token=xxxx..."
    """
    session = request.get('SC_Session')
    if session:
        return parse_session(session)
    return None
    
def parse_session(cookie):
    args = dict((k,v[0]) for k,v in cgi.parse_qs(cookie.strip('"')).items())
    sortit = ''.join('%s=%s'%(k,args[k]) for k in sorted(args.keys()) if k != 'sig')
    sig = hashlib.md5(sortit + COOKIE_SECRET).hexdigest()
    expires = int(args['expires'])
    #logging.debug('get_session_from_cookie, args=%s'%args)
    #if sig == args['sig'] and (expires == 0 or time.time() < expires):
    #    return args
    #return None
    if sig != args['sig']:
        logging.warning('get_session_from_cookie, sig(%s) != args.sig args=%s'%(sig,args))
    elif expires > 0 and time.time() > expires:
        logging.warning('get_session_from_cookie, expires < time(%d) args=%s'%(time.time(),args))
    else:
        return args
    return None
    
class LogoutRequest(webapp.RequestHandler):
    """ Clear cookie if any, and redirect to home / """
    def post(self):
        delete_cookie(self.response.headers, self.request.cookies)
        #self.redirect('/')
        self.response.out.write('/')
        
SNS_PREPS = {'fb':'<div id="fb-root"></div>'}

class WebRequest(BaseRequest):
    """ New design: Common request handler either before or after login.
        The SNS-specific request handlers are for authentication only where cookies are set for a login session.
    """
    def initialize(self, request, response):
        """ Check cookies, load user session before handling requests. Necessary here? can be merged into POST or GET.
        """
        webapp.RequestHandler.initialize(self, request, response)
        self.tempvars = {}
        args = get_session_from_cookie(self.request.cookies)
#        logging.info('WebRequest.initialize args=%s'%args)
        if not args:
            args = get_session_from_request(self.request)
        if not args:
            fbcookie = facebook.get_user_from_cookie(self.request.cookies, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
            if fbcookie:
                self.get = self.post = (lambda *a: None)
                self.redirect('/fb/')
                return
            self.sns = 'web'
            self.user = None
            #self.tempvars = {'sbs':'web'}
            self.tempvars['login'] = False
        else:
            self.tempvars['login'] = True
            self.sns = args['sns']
            if self.sns == 'fb': 
                self.tempvars['onFacebook'] = True
                fbcookie = facebook.get_user_from_cookie(self.request.cookies, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
                if fbcookie and fbcookie['uid'] != args['uid'][3:]:
                    self.get = self.post = (lambda *a: None)
                    self.redirect('/fb/')
                    return
            self.tempvars.update(args)  #['sns','uid','token']
            #self.tempvars['SNS_PREP'] = SNS_PREPS.get(args['sns'],'')
            try:
                self.user = helper.get_user_by_key(args['uid'])
                self.tempvars['user'] = self.user   #???
                self.tempvars['uname'] = self.user.name
            except Exception,e:
                self.response.out.write('Error:%s'%e)
                self.get = self.post = (lambda *args: None)
            
    def get(self):
        """ With public get, only the first page or an image is shown."""
        BaseRequest.post(self)
        
def valid_signature(handler,secret=FACEBOOK_APP_SECRET):
    """ Validate all parameters from self.request against the signature using md5 and raises an exception if invalid.
        All parameters in handler.request.arguments() will be considered excluding 'sig'. These arguments are sorted
        in alphabetical order and hashed using md5 and then compare with sig value.
        @param handler : webapp.RequestHandler object
        @exception : Invalid signature exception
    """
    sig = handler.request.get('sig')
    if sig != '':
        s = ''.join(['%s=%s'%(k,handler.request.get(k)) for k in sorted(handler.request.arguments()) if k != 'sig'])
        csig = hashlib.md5(s + secret).hexdigest()
        if sig != csig:
            logging.warning('Wrong sig: s=%s,\nsecret=%s,\nsig=%s,\ncsig=%s'%(s,secret,sig,csig))
            return False
    else:
        logging.warning('main.valid_signature(): sig = "", signature not validated')
    return True
    
class TaskQueueRequest(webapp.RequestHandler):
    """ Sysadmin to update today's statistics. 
        And log important activities for admin purpose.
        /task/dau?
        /task/log?user=key_name&game=key_name&action=string&donetime=datetime
        /task/genre/add_book?genre=Fantasy
    """
    def post(self):
        paths = self.request.path
        if paths == '/task/dau':
            helper.dau(self.request)
        elif paths == '/task/log':
            helper.log(self.request)
        elif paths == '/task/mail':
            helper.email(self.request)
        elif paths == '/task/genre/add_book':
            helper.add_book_to_genre(self.request)
        elif paths.startswith('/task/feed/add_'):
            helper.post_feed(paths[11:],self.request)
        elif paths == '/task/uremind':
            helper.remind_users(self)
        elif paths == '/task/birthday':
            #logging.debug('TaskQueueRequest.post: %s'%paths)
            helper.send_birthday_gifts(self)
        elif paths == '/task/bdaygift':
            helper.send_gift(self)
        else:
            logging.error('Unknown TaskQueue request path:%s'%paths)
            
    def get(self):
        self.post()

class MySpaceRequest(webapp.RequestHandler):
    """
        OAuth consumer key: http://www.myspace.com/552003400
        OAuth secret: ee27668b30f241c7a6630fdd0715d911b67ea77cd9fa42479b69df7cf2ca3a81
    """
    def post(self):
        """ 
            http://suicomics.appspot.com/ms/install when MySpace user installs this app
            http://suicomics.appspot.com/ms/remove when MySpace user uninstalls this app
            e.g.:
            http://www.example.com/install?oauth_consumer_key=http%3A%2F%2Ffoobartestapp%2Ftestappdsadfsafsd&oauth_nonce=633744074946959871&oauth_signature=e5UArG999f7Lo7rzdHq35Iiwrp8%3D&oauth_signature_method=HMAC-SHA1&oauth_timestamp=1238810694&oauth_version=1.0&opensocial_owner_id=198216895&opensocial_viewer_id=198216895&sourceURL=http%3A%2F%2Fwww.myspace.com%2F317482931
        """
        paths = self.request.path
        if paths.endswith('/ms/install'):
            logging.info('MySpace user installs app') #request is signed with uid
            consumer_key = self.request.get('oauth_consumer_key') #http://..
            oauth_nonce = self.request.get('oauth_nonce') #6337934334343
            oauth_signature = self.request.get('oauth_signature') #e5Ua..
            oauth_signature_method = self.request.get('oauth_signature_method') #HMAC-SHA1
            oauth_timestamp = self.request.get('oauth_timestamp') #12323423
            oauth_version = self.request.get('oauth_version') #1.0
            opensocial_owner_id = self.request.get('opensocial_owner_id') #23434
            opensocial_viewer_id = self.request.get('opensocial_viewer_id') #23432
            sourceURL = self.request.get('sourceURL')   #http..
            
        elif paths.endswith('/ms/remove'):
            logging.info('MySpace user uninstalls app')
        
class CrossDomainAccess(webapp.RequestHandler):
    def get(self):
        f = open('crossdomain.xml')
        txt=f.read()
        f.close()
        self.response.headers.add_header('Content-Type','application/xml')
        self.response.out.write(txt)
        
class GooglebotRequest(webapp.RequestHandler):
    def get(self):
        f = open('robots.txt')
        txt = f.read()
        f.close()
        self.response.out.write(txt)

class GiftViewRequest(webapp.RequestHandler):
    def get(self):
        gid = self.request.get('g')
        if gid:
            self.response.out.write(helper.gen_gift_view(gid))
    def post(self):
        self.get()

class FacebookPayment(webapp.RequestHandler):
    def post(self):
        import pay
        pay.pay_via_facebook_credit(self, FACEBOOK_APP_SECRET)
    def get(self):
        logging.error('/fb/order using get')
                
class PageUploadRequest(webapp.RequestHandler):
    """ Page image upload request via Flash file uploader (YUI).
        No cookie is used, so can't use BaseRequest, the session is passed as parameter 'ck'.
    """
    def post(self):
        ck = self.request.get('ck')
        if not ck or ck.find('SC_Session')<0:
            self.fail('No cookie')
            return
        cki = re.findall(r'SC_Session="([^"]+)"',ck)[0]
        args = parse_session(cki)   #uid,token,sns,expires
        if not args:
            logging.warning('PageUploadRequest. parse_session return None')
            self.fail('Invalid upload')
            return
        uid = args['uid']
        u = helper.get_user_by_key(uid, None, False)
        if not u:
            logging.warning('User %s not found'%uid)
            self.fail('Invalid user')
            return
        fname = self.request.get('Filename')
        x = fname.rfind('.')
        if x < 0:
            self.fail('Invalid image file')
            return
        ext = fname[x+1:]
        if not ext in ['jpg','png','gif','jpeg']:
            self.fail("Not supported image format (only .jpg,.png,.gif)")
            return
        bkid = self.request.get('bk')
        pgid = self.request.get('pg')
        if not bkid or not pgid:
            self.fail('No proper book or page')
            return
        try:
            helper.save_page_image(u,bkid,pgid,ext,self.request.get('Filedata'))
            self.response.out.write('OK')
        except Exception,e:
            logging.exception(e)
            self.fail(e)
        
    def fail(self,msg):
        self.response.out.write('{"error":"%s"}' % msg)

def main():
    handlers = [
        ('/fb/remove',FacebookRemove),
        ('/fb/gift/open',GiftViewRequest),
        ('/fb/order',FacebookPayment),
        ('/gift/open',GiftViewRequest),
        ('/fb/.*',FacebookRequest),
        ('/admin/.*',AdminRequest),
        ('/gg/.*',GoogleRequest),
        ('/task/.*',TaskQueueRequest),
        ('/mm/.*',MediaReader),
        ('/ms/.*',MySpaceRequest),
        ('/robots.txt',GooglebotRequest),
        ('/crossdomain.*',CrossDomainAccess),
        ('/upload',PageUploadRequest),
        ('/logout',LogoutRequest),
        ('/.*',WebRequest)
        ]
    
    app = webapp.WSGIApplication(handlers, debug=True)
    run_wsgi_app(app)

#webapp.template.register_template_library('dtfilter')

if __name__ == '__main__':
    main()
