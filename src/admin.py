#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "$Revision: 1 $"
# $Source$

import os,re
import logging
from datetime import datetime

from google.appengine.ext import db
from google.appengine.api.memcache import get_multi,delete_multi,flush_all
from models import *
import helper

realpath = os.path.dirname(__file__)

KINDS = ['SuiUser','SuiBook']

CMDS='''<html><body><h2>Admin Commands:</h2><ul>
<li>/admin/db_clear</li>
<li>/admin/decache/cachename or /clear_cache</li>
<li>/admin/author_request/uid, /admin/accept_author/uid</li>
<li>/admin/list_zines, (/admin/edit_zine/zineid)</li>
<li>/admin/init_forums, /admin/init_genres</li>
<li>/admin/mediastore</li>
</body></html>
'''

def default(web, args=None):
    """ list admin only commands.
    """
    if web.get_var('admin') is None:
        web.fail('Admin only')
        return
    web.succeed(CMDS)
    
def init_forums(web,args=None):
    if web.get_var('admin') is None:
        web.fail('Admin only')
        return
    SuiForum.init_data()
    web.succeed('Done')
def init_genres(web,args=None):
    if web.get_var('admin') is None:
        web.fail('Admin only')
        return
    SuiGenre.init_data()
    web.succeed('Done')
    
def db_clear(web, args=None):
    """ Delete all entities of a kind or of all kinds as well as memcache. 
        This is for testing period only, production server should remove this!
        /admin/admin/db_clear
    """
    web.require_admin()
    usrs = SuiUser.all(keys_only=True).fetch(1000)
    uids = [u.name() for u in usrs]
    logging.info('deleting %s'%uids)
    delete_multi(uids)
    db.delete(usrs)
    isles = SuiBook.all(keys_only=True).fetch(1000)
    db.delete(isles)
    web.succeed('OK - SuiUser and SuiBook deleted up to 1000 records')
    
def decache(web, args=None):
    """ delete memcache object.
        Available caches: Stories_all,NewStories,<SuiStory.key()>_cms,
        /admin/admin/decache/Stories_all
    """
    if web.get_var('admin') is None:
        web.fail('Admin only')
        return
    if args is None:
        web.fail('No cache name')
        return
    if delete_multi(args):
        web.succeed('OK - %s deleted'%args)
    else:
        web.fail('All or some keys are not deleted: %s'%args)
    
def populate_books(web, args=None):
    """ Populate SuiBook with test data.
    """
    def random_str():
        n = random.randint(2, 5)
        return ' '.join([chr(97+random.randint(0,25)) * random.randint(2,6) for i in xrange(n)])
    def random_author(x):
        n = random.randint(0,2)
        aus = ['test','test1','test2']
        a = [aus[n]]
        if n+1<len(aus):
            a.append(aus[n+1])
        return a
    def random_date():
        ds = random.randint(10,100)
        return datetime.utcnow() - timedelta(days=ds)
    def random_toc():
        chs = random.randint(5,20)
        buf = []
        for x in xrange(chs):
            buf.append('<li>Chapter %d: %s</li>' % (x+1, random_str()))
        return '<ul>%s</ul>'%''.join(buf)
        
    BOOKS = 100
    for x in xrange(BOOKS):
        b = SuiBook()
        b.title = '%s (Test Book %d)' % (random_str(),x)
        b.initial = b.title[0]
        b.authors = random_author(x)
        b.published = random_date()
        b.started = b.published + timedelta(days=random.randint(5,50))
        b.status = ['active','finished'][random.randint(0,1)]
        b.intro = '<p>Introduction of book [%s]:</p> %s' % (x+1,''.join([random_str() for i in xrange(random.randint(1,5))]))
        b.genre = ['fantasy','romance','scifi','history'][random.randint(0,3)]
        b.toc = random_toc()
        b.put()
    web.succeed()
    
def clear_cache(web, args=None):
    web.require_admin()
    r = flush_all()
    web.succeed('Deleted: %s'%r)
    
def populate_users(web, args=None):
    """ Add some test users including readers and authors.
    """
    web.require_admin()
    READERS = 100
    AUTHORS = 10
    for x in xrange(READERS+AUTHORS):
        ukey = 'gg_%d'%(x+1)
        u = SuiUser(key_name=ukey)
        u.name = ukey
        u.email = '%s@example.com'%u.name
        if x > READERS:
            u.role = 'A'
        u.put()
        
from templite import render_text, jsonize

def update_users(web, args=None):
    web.require_admin()
    usrs = SuiUser.all().fetch(100)
    for u in usrs:
        if u.role == 'A':
            qa = SuiAuthor(key_name=u.key().name())
            qa.name = u.name
            bks = SuiBook.all().filter('authors =',qa.name).fetch(5)
            wrks = dict((str(b.key().id()),[datetime.strftime(b.started,'%Y-%m-%d %H:%M:%S'),b.pages,0]) for b in bks)
            qa.works = jsonize(wrks)
            qa.intro = 'Self-introduction for %s'%qa.name
            qa.links = '{"web":"http:","blog":"http:","twitter":"1233","facebook":"323"}'
            qa.put()
        #db.delete(u)
        u.put()
    web.succeed()
    
AUTHOR_INFO = '''<html><body><h3>User Request of Authorship</h3><div><table border="1"><tr><td>User:</td><td>%s %s %s</td></tr>
<tr><td>Email:</td><td>%s</td></tr>
<tr><td>Address:</td><td>%s</td></tr>
<tr><td>Role:</td><td>%s</td></tr>
<tr><td>Intro:</td><td>%s</td></tr>
<tr><td>Links:</td><td>%s</td></tr>
</table></div><a href="/admin/accept_author/%s">Accept</a> or write an email for enquiry or rejection(reject form here).
'''

def author_request(web,args=None):
    """ Admin handles reader request authorship.
        /admin/author_request/uid
        Read author info from SuiAuthor, and click Accept or Reject accordingly.
    """
    if not args:
        logging.warning('admin/author_request/None')
        web.fail('Invalid author-request')
        return
    uid = args[0]
    u = SuiUser.get_by_key_name(uid)
    if not u:
        web.fail('User not found')
        return
    if u.isAuthor():
        web.succeed('Already done')
        return
    a = SuiAuthor.get_by_key_name(uid)
    if not a:
        web.warning('admin/author_request, uid %s not in SuiAuthor'%uid)
        web.fail('User application not recorded')
        return
    html = AUTHOR_INFO % (a.title,a.firstname,a.lastname,a.email,a.address,a.job,a.intro,a.links,a.key().name())
    web.succeed(html)
    
WELCOME_LETTER='''Welcome to Suinova Comics (%s) as a creator! 
'''

def accept_author(web,args=None):
    """ After reviewing author application, click Accept link and here.
        Change SuiUser.role from 'R' to 'A', send this user an email as notification.
    """
    web.require_admin()
    if not args:
        logging.warning('admin/accept_author/None')
        web.fail('Invalid author accept call')
        return
    uid = args[0]
    bda = web.request.get('bda')
    a = SuiAuthor.get_by_key_name(uid)
    if not a:
        web.fail('User not recorded')
        return
    u = SuiUser.get_by_key_name(uid)
    if u.role != 'A':
        u.role = 'A'
        a.confirmed = True
        try:
            db.put([a,u])
            u.recache()
            a.recache()
            if uid.startswith('fb_'):
                lts = WELCOME_LETTER % 'http://apps.facebook.com/suicomics/'
            else:
                lts = WELCOME_LETTER % 'http://suicomics.appspot.com/'
            if bda == '1':
                lts += 'gift'
            helper.send_email('Application Accepted',lts,a.email)
            if bda == '1':
                bu = SuiBirthdayUser.get_by_key_name(uid)
                if not bu:
                    bu = SuiBirthdayUser(key_name=uid,name=u.name,access_token=u.access_token) #update access_token when user change password
                    bu.creator = True
                bu.put()
            web.succeed('Done')
        except Exception,e:
            logging.exception(e)
            web.fail('Accept not successful, please notify admin')
            return
    else:
        web.succeed('User is already author')

def list_zines(web,args=None):
    """ Return a list of SuiZines as HTML """
    zines = SuiZine.all().fetch(1000)
    buf = []
    for z in zines:
        buf.append('<tr><td><a href="/admin/edit_zine/%s">'%z.key().id())
        buf.append(z.title)
        buf.append('</a></td></tr>')
    buf.append('<tr><td><a href="/admin/edit_zine">New Periodical</a></td></tr>')
    web.succeed('<html><body><h1>List of Comic Periodicals</h1><table>%s</table></body></html>'%''.join(buf))
    
ZINE_HTML='''<html><body><h1>Periodical: %s</h1><form method="POST" action="/admin/edit_zine">
<input type="hidden" name="zine" value="%s"/>
<table><tr><td>Title:</td><td><input name="title" value="%s"/></td></tr>
<tr><td>Owner(change):</td><td><input name="owner" value="%s"/></td></tr>
<tr><td>Authors:</td><td><input name="authors" value="%s"/></td></tr>
<tr><td>Period:</td><td><select name="period"><option value="monthly" selected="selected">Monthly</option><option value="bimonthly">Bi-monthly</option></select></td></tr>
<tr><td>Note:</td><td><textarea name="note" rows="8">%s</textarea></td></tr>
<tr><td colspan="2" style="text-align:center"><input type="submit" value="Submit"/></td></tr>
</table></form>
</body></html>
'''

def edit_zine(web,args=None):
    """ Add new or edit old SuiZine entity.
        title = db.StringProperty(indexed=False)
        owner = db.StringProperty() #Author.key_name
        startime = db.DateTimeProperty(auto_now_add=True)
        issues = db.TextProperty()  #[{id:book_id,title:'',date:''},..]
        authors = db.StringListProperty() #[uid,uid,..]
        period = db.StringProperty(indexed=False)   #monthly,bimonthly,free
        note = db.TextProperty()
    """
    web.require_admin()
    zine = None
    if args: zine = args[0]
    pkeys = ['title','owner','authors','period','note']
    title,owner,authors,period,note = web.get_params(pkeys)
    if not title:
        #edit page
        if not zine:
            zinehtml=ZINE_HTML%('New','','','','','')
        else:
            z = SuiZine.get_by_id(int(zine))
            zinehtml=ZINE_HTML%(z.title,z.key().id(),z.title,z.owner,z.authors,z.note)
        web.succeed(zinehtml)
    else:
        #save from form
        if zine:
            z = SuiZine.get_by_id(int(zine))
        else:
            z = SuiZine()
            z.title = title
            z.owner = owner or web.user.key().name()
            sauthors = [z.owner]
            if authors: sauthors = [s for s in re.split(r'[ ,;]',authors) if s]
            z.authors = sauthors #["uid","uid",..]
            z.period = period
            z.note = note
        z.put()
        web.succeed('Done')

IMG_LUKUP_PAGE='''<html><head></head><body><h1>MediaStore Lookup</h1>
<form method="post" action="/admin/mediastore"><select name="type">
<option value="date">By Date</option><option value="author">By Author</option><option value="book">By Book</option></select>
ID: <input type="text" name="key"/><br/><input type="submit" value="Look Up"/></form><hr/>
<div>%s</div><div><form method="post" action="/admin/mediastore/update" enctype="multipart/form-data">
<table><tr><td>Key_name (avatar_1):</td><td><input type="text" name="keyname"/></td></tr>
<tr><td>Book:</td><td><input type="text" name="book"/></td></tr>
<tr><td>page:</td><td><input type="text" name="page"/></td></tr>
<tr><td>usage:</td><td><input type="text" name="usage"/></td></tr>
<tr><td>width:</td><td><input type="text" name="width"/></td></tr>
<tr><td>height:</td><td><input type="text" name="height"/></td></tr>
<tr><td>File:</td><td><input type="file" name="stream"/></td></tr>
<tr><td colspan="2"><input type="submit" value="Submit"/></td></tr>
</table></form></body></html>
'''
def mediastore(web,args=None):
    """ Load all mediastore items by date(after), author, or book. """
    web.require_admin()
    if args:
        if args[0] == 'update':
            pkeys = ['keyname','book','page','usage','width','height','stream']
            imgkey,bk,pg,use,w,h,stream = web.get_params(pkeys)
            if not imgkey:
                web.fail('No key name')
                return
            mm = MediaStore.get_by_key_name(imgkey)
            if not mm:
                mm = MediaStore(key_name=imgkey)
            else:
                mm.decache()
            if bk: mm.book=bk
            if pg: mm.page=int(pg)
            if use: mm.usage=use
            if stream:
                imgfile = web.request.POST.get('stream').filename
                mm.format = imgfile[imgfile.rfind('.')+1:].lower()
                mm.stream = stream
            mm.put()
            web.succeed('Done')
    else:
        qkeys = ['type','key']
        type,keys = web.get_params(qkeys)
        if not type:
            html=IMG_LUKUP_PAGE%''
            web.succeed(html)
        else:
            if type == 'date':
                dt = datetime.strptime(keys,'%Y-%m-%d')
                qs = MediaStore.all().filter('timestamp >',dt).fetch(500)
            elif type == 'book':
                qs = MediaStore.all().filter('book =',keys).fetch(500)
            else:
                web.succeed('type %s not supported'%type)
                return
            buf = []
            for q in qs:
                buf.append('<div>Key_name:%s, Book:%s, Page:%s, Width:%d, Height:%d, Format:%s<br><img src="/mm/%s"/></div>'%(q.key().name(),
                                                                                                                              q.book,q.page,q.width or 0,q.height or 0,q.format,q.key().name()))
            web.succeed(IMG_LUKUP_PAGE%''.join(buf))
            