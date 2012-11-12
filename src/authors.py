#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging
from datetime import datetime
from google.appengine.ext import db
#from google.appengine.api import memcache
#from google.appengine.api import images
from google.appengine.api import taskqueue
#from google.appengine.api import urlfetch
from models import *
import helper

def default(web, args=None):
    """ Default handler to return the home page and call js to switch to author view. """
    import home
    web.add_var('pageview','authors')
    home.default(web, args)

APP_MSG='''User %s applied for authorship in Suinova Comics.
E-mail: %s
Web links (please check these):
Facebook: %s
%s
Please follow http://suicomics.appspot.com/admin/accept_author/%s?bda=%s to approve.
'''

def profile(web,args=None):
    """ Readers apply for authorship or authors update their profile.
        Form is submitted and it returns the main page with authors as pageview.
        User input will be saved in SuiAuthor entity but SuiUser.role is still 'R'.
        An email will be sent to admin who will then review the author and change R to A, and notify the author.
    """
    if not web.logged_in:
        web.redirect_with_msg('Login required')
        return
    me = web.user
    parms=['title','fname','lname','email','address','job','intro','web','blog','facebook','twitter','linkedin','other','bda']
    title,fname,lname,email,address,job,intro,webs,blog,facebook,twitter,linkedin,other,bda=web.get_params(parms)
    if me.isAuthor():
        a = SuiAuthor.get_by_key_name(me.key().name())
    else:
        a = SuiAuthor(key_name=me.key().name(),name=me.name)
    if title: a.title = title
    if fname: a.firstname = fname
    if lname: a.lastname = lname
    if email: a.email = email
    if address: a.address = address
    if job: a.job = job
    if intro:
        ins = intro.replace('"','&quot;').replace('<','&lt;')
        a.intro = ins 
        #a.intro = ''.join(['<p>%s</p>'%ls.strip() for ls in intro.replace('<','&lt;').split('\n')])
    lnks = []
    if webs: lnks.append('Web: %s'%webs)
    if blog: lnks.append('Blog: %s'%blog)
#    if facebook: lnks.append('Facebook: %s'%facebook)
    if facebook: a.fbpage = facebook
    if twitter: lnks.append('Twitter: %s'%twitter)
    if linkedin: lnks.append('LinkedIn: %s'%linkedin)
    if other: lnks.append('Other: %s'%other)
    if lnks:
        a.links = '[%s]'%','.join(['"%s"'%s for s in lnks])  #["web:http:..","twitter:",..]
    try:
        a.put()
        if me.role == 'R':
            me.role = 'a'
            me.save()
            msg = APP_MSG % (me.name,me.email or '',facebook,'\r\n'.join(lnks),me.key().name(),bda)
            helper.send_email('[Suinova Comics] %s appled for Authorship'%me.name,msg,'suinova@gmail.com')
        else:
            me.detach_author()
    except Exception,e:
        logging.exception(e)
        web.redirect_with_msg('Server error, retry later')
        return
    if bda == '1':
        web.redirect('/gift')
    else:
        web.redirect('/authors')
    #default(web,args)
    
    