#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging, random, urllib
from datetime import datetime,timedelta
from re import compile
from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.api import mail
from google.appengine.api.memcache import get as from_cache,set as to_cache,delete as decache
from models import *

def get_user_by_key(uid,usecache=True):
    """ Get SuiUser entity from datastore by key_name, return None if not existent. 
    @param uid: fb_1234 like
    @param usecache: if True, Get from memcache first, and Put in memcache or not, default is True.
    """
    if usecache:
        u = from_cache(uid)
    else:
        u = None
    if not u:
        logging.debug('UID %s not in memcache'%uid)
        try:
            u = SuiUser.get_by_key_name(uid)
            if u is None:
                logging.debug('User not in SuiUser')
                return u
            if usecache:
                u._cache_time = datetime.utcnow()
                to_cache(uid, u, PLAYER_CACHE_SECS)
        except Exception,e:
            logging.error('helper.get_user_by_key(%s) error:%s' % (uid,e))
            raise
    return u

def query_user_by_key(uid):
    u = from_cache(uid)
    if not u:
        u = SuiUser.get_by_key_name(uid)
    return u

def create_user(uid,fullname,emailaddr=None,save=True):
    """ Create SuiUser entity and save in datastore and memcache as well. 
        Dau record is added as new-registers count of today.
        @param uid: such as "FB_1234567"
        @param fullname: such as "Ted Wen"
        @param emailaddr: user's email address is any
    """
    try:
        u = SuiUser(key_name=uid,name=fullname,email=emailaddr)
        td = datetime.utcnow()
        if save:
            u.save()
            #u.put()
            #to_cache(uid, u, PLAYER_CACHE_SECS)
        taskqueue.add(url='/task/dau',params={'act':'register','usr':uid})
        try:
            send_email('SuiComics New User: %s[%s]'%(uid, fullname or ''), 'Email: %s, Time: %s'%(emailaddr or '',datetime.utcnow()))
        except:
            logging.warning('helper.create_user(%s,%s) failed to send_email'%(uid,fullname)) 
            pass
        return u
    except:
        logging.error('helper.create_user() SuiUser put error')
        raise
        
def unregister_user(uid):
    """ Set user's active status to False because Facebook user issued a remove app, etc.
    """
    try:
        u = SuiUser.get_by_key_name(uid)
        if u:
            u.active = False
            u.put()
            decache(uid)
        else:
            logging.warning('User %s not found while de-authorizing'%uid)
    except Exception,e:
        logging.exception(e)
        
def load_media(keyname):
    """ Load an image from MediaStore, if a page image, return None. """
#    logging.info('loading media %s'%keyname)
    if keyname.startswith('bp'):
        return None
    mm = MediaStore.load_by_key(keyname)
#    if not mm and keyname.startswith('bkc_'):
#        mm = MediaStore.load_by_key(keyname.replace('bkc_','bk_'))
    return mm

def send_email(sbj, txt, toemail='customer@suinova.com'):
    """ email Suinova customer service group by admin upon user registration """
    try:
        mail.send_mail(sender='tedwen@suinova.com', to=toemail, subject=sbj, body=txt)
    except Exception,e:
        logging.error('error notifyOwner:%s'%e)

def notify_followers(abid,subject,body):
    """ Send email to all followers one by one via MailQueue. followers are {"uid":"email",..} """
    sfs = SuiFollower.all().filter('id =', abid).fetch(100)
    fans = {}
    for sf in sfs:
        fans.update(sf.get_fans())  #{"uid":"email",..}
    if len(fans) <= 0:
        return
    queue = Queue('MailQueue')
    for ts in fans.values():
        if mail.is_email_valid(ts):
            queue.add(Task(url='/task/mail',params={'to':rto,'sbj':subject,'bdy':body}))    #task will call send_email above

def email(request):
    """ Called by task queue /task/mail
    """
    to = self.request.get('to')
    sbj = self.request.get('sbj')
    bdy = self.request.get('bdy')
    #logging.debug('Sending %s to %s' % (sbj,to))
    send_email(sbj,bdy,to)

def log(request):
    """ taskqueue routine to log important activities. 
        'usr':me.key().name(),'act':'buy %d %s'%(qty,itm),'dt':'2011-01-01 01:01:01.1234'
    """
    us = request.get('usr')
    ac = request.get('act')
    dt = request.get('dt')
    if not dt:
        dt = datetime.utcnow()
    if dt.find('.')>0:
        dt = dt[:dt.find('.')]
    t = datetime.strptime(dt,'%Y-%m-%d %H:%M:%S')
    lg = SuiLog(user=us,action=ac,donetime=t)
    lg.put()
    
def dau(request):
    """ New DAU routine to log a user's session.
        /task/dau?usr=uid&act=<action>  
        <action>: register, login, open(book_id), buy(item_id)
    """
    usr = request.get('usr')
    act = request.get('act')
    par = request.get('par')
    qty = request.get('qty')
    SuiDau.add(usr,act,par,qty)
    
def add_book_to_genre(request):
    """ From task/genre """
    genres = request.get('genre')    #can be multiple separated by commas
    bkid = request.get('bkid')
    for genre in list(set(genres.split(','))):
        if not genre: continue
        g = SuiGenre.get_by_key_name(genre)
        if g:
            if g.books:
                g.books.append('%s'%bkid)
            else:
                g.books = ['%s'%bkid]
            g.put()
    SuiGenre.clear_cache()

def dau_deprecated(request):
    """ taskqueue routine to store number of daily visits. """
    nusers = nregisters = nvisits = npays = 0
    susers = request.get('users')
    if susers != '':
        try: 
            nusers = int(susers)
        except: pass
    sregisters = request.get('registers')
    if sregisters != '':
        try:
            nregisters = int(sregisters)
        except: pass
    svisits = request.get('visits')
    if svisits != '':
        try:
            nvisits = int(svisits)
        except: pass
    spays = request.get('pays')
    if spays != '':
        try:
            npays = int(spays)
        except: pass
    book = request.get('book')
    if book == '': book = '-'
    dt = request.get('dt')
    if dt == '':
        dt = str(datetime.date(datetime.utcnow()))
    dt_book = '%s_%s' % (dt,book)
    def txn():
        dau = SuiDau.get_by_key_name(dt_book)
        if dau is None:
            dau = SuiDau(key_name=dt_book,visits=nvisits,users=nusers,registers=nregisters,pays=npays,book=book)
        else:
            dau.visits += nvisits
            dau.users += nusers
            dau.registers += nregisters
            dau.pays += npays
        dau.put()
    try:
        db.run_in_transaction(txn)
    except Exception,e:
        logging.error('helper.dau error:%s'%e)

def send_emails(me, toemails, msg):
    """ send email to toemails.
        TODO: this may not work since me may not be a Google Account user!
    """
    if not mail.is_email_valid(toemails):
        raise Exception('Invalid email address')
    try:
        logging.debug('Sending email to %s'%toemails)
        mail.send_mail(sender=me.email, to=toemails, subject='You are invited by your friend!', body=msg)
    except Exception,e:
        logging.error('error send_mail(%s,%s,%s,%s):%s'%(me.key().name(),toemails,'',msg,e))
        raise
    
def get_news():
    """ read system news if any """
    news = from_cache(gGameNewsCacheKey)
    if news is None:
        return '[]'
    newsbuf = []
    td = datetime.utcnow()
    for ns in news:
        if ns[1] > td:
            newsbuf.append(ns[0])
    return newsbuf

def get_new_stories(N=10):
    """ Load N latest stories, return [[key,title],..] """
    stories = from_cache('NewStories')
    if stories is None:
        qs = SuiStory.all().order('-postime').fetch(N)
        stories = [[str(q.key()),q.title] for q in qs]
        to_cache('NewStories',stories)  #only when new stories added, invalidate this cache
    return stories
    
def load_stories(game='all',cursor='',pagesize=50,sortorder='-postime'):
    """ Return a page of stories.
        This function makes use of cursor mechanism to fetch pages and cache them for efficient repeated queries.
        Once a page of SuiStory entities are loaded, they are memcached with the cursor.
        If not enough entities are loaded, cursor is None meaning no more pages.
        Stories are sorted for display by postime in descending order.
        Pages are always in memcache of 'Stories', invalidated when a new story is added.
        @param game : game key or all
        @param cursor : from which cursor to fetch, '' = first page
        @param pagesize : how many for a page, default 30
        @param sortorder : postime in descending by default, can be 'title', 'author'
        @return : ([SuiStory,...],cursor) tuple of a list of SuiStory entities or None
    """
    cachekey = 'Stories_%s_%s'%(game,cursor)
    stories = from_cache(cachekey)
    if stories is None:
        if game != 'all':
            query = SuiStory.all().filter('game =',game).order(sortorder)
        else:
            query = SuiStory.all().order(sortorder)
        if cursor != '':
            query.with_cursor(cursor)
        mstories = query.fetch(pagesize)
        if len(mstories) > 0:
            c = None
            if len(mstories) >= pagesize:
                c = query.cursor()
            stories = (mstories,c or '')
            to_cache(cachekey,stories)
        else:
            stories = ([],'')
    return stories
    
def filter_tag(m):
    """ Filter out HTML tags except single-letter ones such as <p> </p>. """
    if len(m.group(1)) < 3:
        return m.group(0)
    else:
        return ''
        
XML_REPTN=compile(r'</?([^>]*)>')

def add_story(me,title,content,game):
    """ save a story in my name.
    """
    if title is None or title == '':
        logging.warning('title is empty')
        raise Exception('No title')
    if content is None or content == '':
        logging.warning('content is empty')
        raise Exception('No content')
    s = SuiStory()
    s.title = title.replace('<','&lt;')
    #s.text = content.replace('<','&lt;').replace('\n','<br/>').replace('\r','')
    s.game = game
    s.author = me.key().name()
    s.aname = me.name
    s.postime = datetime.utcnow()
    s.put()
    #save content text into SuiContent
    c = SuiContent(parent=s)
    if content.find('\n')>=0:
        content = content.replace('\r\n','<br>').replace('\n','<br>');
    c.text = XML_REPTN.sub(filter_tag, content)
    c.length = len(c.text)
    c.put()
    pages = from_cache('Stories_all')
    if pages is not None:
        page1 = pages[0]
        if len(page1[0]) > 40:
            decaches(['Stories_all','NewStories'])
        else:
            page1[0].insert(0,s)
            to_cache('Stories_all',pages)
            decache('NewStories')
    
def load_comments(story,page=0):
    """ Load all SuiContent entities for story and return text and comments of first entity.
        @param story - key string of SuiStory
        @param page - which entity of SuiContent for this story, 0 first by default, can be 10 pages maximum.
    """
    if isinstance(story,basestring):
        skey = db.Key(story)
    else:
        skey = story
    mckey = str(skey)+'_cms'
    content = from_cache(mckey)
    if content is None:
        content = SuiContent.all().ancestor(skey).fetch(10)
        if content:
            to_cache(mckey, content)
        else:
            return None
    if len(content) > page:
        return content[page]
    else:
        return content[-1]
        
def load_comments0(story,page=0,pagesize=50):
    """ Load a page of comments for a story. Page of comments are also memcached until a new comment is added.
    """
    if isinstance(story,SuiStory):
        skey = story.key()
    elif isinstance(story,basestring):
        skey = db.Key(story)
    else:
        skey = story
    mckey = str(skey)+'_cms'
    comments = from_cache(mckey)
    if comments is None:
        query = SuiComment.all().filter('story =',skey).order('-postime')
        cmts = query.fetch(pagesize)
        if len(cmts) > 0:
            c = None
            if len(cmts) >= pagesize:
                c = query.cursor()
            comments = [(cmts,c)]
            to_cache(mckey, comments)
        else:
            return [([],None)]
    elif page >= len(comments) and comments[-1][1] is not None:
        query = SuiComment.all().filter('story =',skey).order('-postime')
        query.with_cursor(comments[-1][1])
        cmts = query.fetch(pagesize)
        if len(cmts) >= pagesize:
            comments.append((cmts,query.cursor()))
        else:
            comments.append((cmts,None))
        to_cache(mckey,comments)
    return comments[page]
    
def add_comment(me,story,comment):
    """ Add a comment """
    if isinstance(story,basestring):
        skey = db.Key(story)
    else:
        skey = story
    if not comment:
        return
    elif comment.find('\n'):
        comment = comment.replace('\r\n','<br>').replace('\n','<br>')
    mckey = str(skey)+'_cms'
    content = from_cache(mckey)
    if content is None:
        content = SuiContent.all().ancestor(skey).fetch(10)
        if not content:
            raise Exception('Story not found')
    c = content[-1]
    cp = 'c%d' % c.count
    c.count += 1
    pfx = '[%s:%s@%s]'%(me.key().name(),me.name,datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H:%M:%S'))
    setattr(c, cp, '%s%s'%(pfx, XML_REPTN.sub(filter_tag, comment)))
    c.put()
    to_cache(mckey, content)
    
def add_comment0(me,story,content):
    """ Add a comment to a story. """
    c = SuiComment()
    c.story = db.Key(story)
    logging.debug(story)
    c.text = content
    c.author = '%s[%s]'%(me.name,me.key().name())
    c.postime = datetime.utcnow()
    c.put()
    mckey = str(story)+'_cms'
    if mckey is not None:
        pages = from_cache(mckey)
        if pages is not None:
            page1 = pages[0][0]
            if len(page1) > 60:
                decache(mckey)
            else:
                page1.insert(0,c)
                to_cache(mckey,pages)
    
def lock_process(lock_key):
    """ Emulate a lock to stop the code going on if the process is still going on.
        This can happen when a user repeatedly clicks on buy button that causes invalid transaction.
        If memcache is not available, this will definately raise an exception and causes the routine to fail.
        Algorithm: check whether a memcache is available, if not, add it for 30 seconds, and return, if yet, raises ServerBusy exception.
    """
    lock = from_cache(lock_key)
    if lock is None:
        if to_cache(lock_key,lock_key,30) == False:
            raise Exception('Server Error, try later')
    else:
        raise Exception('Server Busy, try later')
        
def unlock_process(lock_key):
    """ Unlock the process/method that's just locked.
    """
    decache(lock_key)
    
def add_signature(params, secret):
    """ Sort all key=value pairs in params dict and add secret string to the end and make a md5 signature hexdigest and add "sig":signature to the params.
        If params has sig key, then it is deleted.
    """
    if params is None or secret is None:
        logging.error('param or secret None')
        raise Exception('Param or secret None')
    if 'sig' in params:
        del params['sig']
    s = ''.join(['%s=%s'%(k,params[k]) for k in sorted(params.keys())])
    logging.debug('helper.add_signature, s=[%s]'%s)
    sigs = hashlib.md5(s + secret).hexdigest()
    params['sig'] = sigs
    logging.debug('secret=[%s],sig=[%s]'%(secret,sigs))
    
def save_page_image(u,bkid,pgid,ext,imgdata):
    """ Validate user, book author, page existence, and image size 
    """
    bk = SuiBook.seek_by_id(bkid)
    if not bk:
        raise Exception('Book not found')
    if u.key().name() not in bk.authors:
        raise Exception('Author only')
    pg = SuiPage.get_by_id(int(pgid))
    if not pg:
        raise Exception('Page not found')
    imgkey = 'bp%s_%s' % (bkid,pgid)
    img = MediaStore.get_by_key_name(imgkey)
    if not img:
        img = MediaStore(key_name=imgkey,book=bkid,page=int(pgid),usage='0',format=ext.lower())
    else:
        pg.version += 1
        img.decache()
    from google.appengine.api import images
    m = images.Image(imgdata)
    if m.width > 740:
        m.resize(740)
        if ext=='jpg':
            img.stream = db.Blob(m.execute_transforms(images.JPEG))
        else:
            img.stream = db.Blob(m.execute_transforms())
    else:
        img.stream = db.Blob(imgdata)
    img.width = m.width
    img.height = m.height
    img.put()
    a = u.get_author()
    a.spaceused += len(db.model_to_protobuf(img).Encode())
#    logging.info('helper.save_page_image, image size=%d'%len(db.model_to_protobuf(img).Encode()))
    a.save()
    u.recache()
    
def fb_app_atoken(app_id,app_secret):
    """ Get Facebook access_token for application. """
    access_token = None
    args = {'grant_type':'client_credentials','client_id':app_id,'client_secret':app_secret}
    file = None
    try:
        file = urllib.urlopen('https://graph.facebook.com/oauth/access_token',urllib.urlencode(args))
        resp = file.read()
        if resp.startswith('access_token='):
            access_token = resp[13:]
            logging.debug('access_token=%s'%access_token)
        else:
            logging.error('Facebook access_token returned %s'%resp)
    finally:
        if file: file.close()
    return access_token

def fb_app_feed(args):
    """ post feed to the app wall """
    FACEBOOK_APP_ID = "179008415461930" #Suinova Comics (http://apps.facebook.com/suicomics)
    FACEBOOK_APP_SECRET = "9e194f115ba46d6ba6daafb1e6fe3d86"
    access_token = fb_app_atoken(FACEBOOK_APP_ID,FACEBOOK_APP_SECRET)
    if not access_token:
        return
    args['access_token']=access_token
    file = None
    try:
        file = urllib.urlopen('https://graph.facebook.com/%s/feed'%FACEBOOK_APP_ID,urllib.urlencode(args))
        resp = file.read()
        #logging.debug('post to wall return:%s'%resp)
    finally:
        if file: file.close()

def post_feed(cmd,request):
    """ Post sns feed to facebook application page.
    curl -F grant_type=client_credentials -F client_id=179008415461930 -F client_secret=9e194f115ba46d6ba6daafb1e6fe3d86 https://graph.facebook.com/oauth/access_token
    curl -d "access_token=179008415461930|lNzzs_rKfeEguA5l3Zs_vKYfcOw&message=Hello+world" https://graph.facebook.com/179008415461930/feed
    """
    if cmd == 'add_book':
        uid = request.get('uid')
        bkid = request.get('bkid')
        uname = request.get('uname')
        title = request.get('title')
        intro = request.get('intro')
        if uid and bkid and uname and title:
            args={'name':'New Book: %s'%title,'caption':'By %s'%uname}
            args['link']='http://apps.facebook.com/suicomics/book/'+bkid
            args['picture']='http://suicomics.appspot.com/mm/bk_'+bkid+'.jpg'
            args['description']=intro[:400]
            fb_app_feed(args)
    elif cmd == 'add_page':
        uname = request.get('uname')
        bkid = request.get('bkid')
        title = request.get('title')
        if uname and bkid and title:
            args={'message':'Book Update: %s by %s'%(title,uname)}
            args['actions']='{"name":"Read","link":"http://apps.facebook.com/suicomics/book/%s"}'%bkid
            fb_app_feed(args)
            
def remind_users(web,args=None):
    """ Weekly job to check users not login for over a week, and remind by a fb bookmark counter plus or email notification.
        If uid is fb_xxx, send bookmark counter+1, else if has email, send a note.
        Each time, fetch 1000 users.
        Not send every week, but follow this pattern: every time first month, every other time next two months, then every third time, and forth.
        After a year, stop sending anything.
        NOTE: only Facebook bookmark counter supported, no emails are sent
        TODO: use query cursor and repeated tasks to finish all updates
    """
    #web.require_admin()    #for admin or taskqueue call only
    #SEND_WEEKS = [1,2,3,4, 6,8, 10,12, 15,18,21,24, 28,32,36,40, 44,48,52]  #not used for now, just facebook supported currently
    today = datetime.utcnow()
    lastweek = today - timedelta(days=7)
    lastyear = today - timedelta(days=365)
    logging.debug('helper.remind_users: weekly task to find users to add fb count')
    usrs = SuiUser.all(keys_only=True).filter('lastime <',lastweek).filter('lastime >',lastyear).fetch(1000)
    fbus = []
    for u in usrs:
        if u.name().startswith('fb_'):
            fbus.append(u.name()[3:])
    if fbus:
        # https://api.facebook.com/method/dashboard.multiIncrementCount?uids=
        FACEBOOK_APP_ID = "179008415461930" #Suinova Comics (http://apps.facebook.com/suicomics)
        FACEBOOK_APP_SECRET = "9e194f115ba46d6ba6daafb1e6fe3d86"
        access_token = fb_app_atoken(FACEBOOK_APP_ID,FACEBOOK_APP_SECRET)
        if not access_token:
            logging.warning('helper.remind_users: failed to get APP access_token')
            return
        args = {'access_token':access_token,'uids':'[%s]'%','.join(['"%s"'%s for s in fbus])}
        file = None
        try:
            logging.debug('helper.remind_users: sending %s to multiIncrementCount'%args)
            url = 'https://api.facebook.com/method/dashboard.multiIncrementCount?%s'%(urllib.urlencode(args))
            file = urllib.urlopen(url)
#            file = urllib.urlopen('https://api.facebook.com/method/dashboard.multiIncrementCount',urllib.urlencode(args))
            resp = file.read()
            if resp and resp.find('<error_code>') > 0:
                logging.debug('helper.remind_users multiIncrementCount returned: %s'%resp)
        except:
            logging.warning('helper.remind_users urlfetch error, ignored')
        finally:
            if file: file.close()
    else:
        logging.debug('helper.remind_users: no users to remind')

def clear_fb_count(uid):
    """ if fb bookmarks count > 0, reset it. """
    FACEBOOK_APP_ID = "179008415461930"
    FACEBOOK_APP_SECRET = "9e194f115ba46d6ba6daafb1e6fe3d86"
    access_token = fb_app_atoken(FACEBOOK_APP_ID,FACEBOOK_APP_SECRET)
    url = 'https://api.facebook.com/method/dashboard.setCount?count=0&uid=%s&access_token=%s'%(uid,access_token)
    file = None
    try:
        logging.debug('helper.clear_fb_count')
        file = urllib.urlopen(url)
        resp = file.read()
        if resp and resp.find('<error_code>') > 0:
            logging.debug('helper.clear_fb_count dashboard.setCount returned: %s'%resp)
    finally:
        if file: file.close()

def load_gifts(uid=None):
    """ Load gift ids from SuiBirthdayGift entities and store in memcache by BD_GIFTS_ALL or BD_GIFTS_creatorID
        Maximum number of gifts in use for all is 10000, while any creator can have no more than 20
    """
    if uid:
        gs = from_cache('BD_GIFTS_%s'%uid)
        if not gs:
            es = SuiBirthdayGift.all(keys_only=True).filter('creator =',uid).fetch(50)
            gs = [e.id_or_name() for e in es]
            to_cache('BD_GIFTS_%s'%uid, gs)
    else:
        gs = from_cache('BD_GIFTS_ALL')
        if not gs:
            es = SuiBirthdayGift.all(keys_only=True).fetch(10000)
            gs = [e.id_or_name() for e in es]
            to_cache('BD_GIFTS_ALL', gs)
    return gs

def update_gift_cache(op,gid,uid=None):
    gs = from_cache('BD_GIFTS_ALL')
    if gs and not gid in gs:
        if op == 'add':
            gs.append(gid)
        elif op == 'del':
            gs.remove(gid)
        to_cache('BD_GIFTS_ALL', gs)
    gs = from_cache('BD_GIFTS_%s'%uid)
    if gs and not gid in gs:
        if op == 'add':
            gs.append(gid)
        elif op == 'del':
            gs.remove(gid)
        to_cache('BD_GIFTS_%s'%uid)
        
def run_send_as_task(web, args=None):
    taskqueue.add(url='/task/birthday',params={})
    
def send_birthday_gifts(web,args=None):
    """ Check a list of users friends for birthdays and send gifts accordingly.
        Called every 24 hours, 
        get all registered users for sending gifts,
        issue a task for each user as /task/bdaygift?u=uid&g=gid
        
    """
    #web.require_admin()    #for admin or taskqueue call only
    #logging.debug('helper.send_birthday_gifts: enter')
    uq = SuiBirthdayUser.all()
    #logging.debug('helper.send_birthday_gifts: SuiBirthdayUser.all() returned')
    cursor = web.request.get('cursor')
    #logging.debug('helper.send_birthday_gifts: cursor=%s'%cursor)
    if cursor:
        uq.with_cursor(cursor)
    usrs = uq.fetch(500)
    if not usrs:
        logging.debug('helper.send_birthday_gifts: no birthday user')
        return
    today = datetime.utcnow()
    tk = '%02d-%02d' % (today.month,today.day)
    count = 0
    gs = load_gifts()
    if not gs:
        logging.debug('helper.send_birthday_gifts: no gifts available')
        return
    n = len(gs)-1
    for u in usrs:
        #if u.key().name()=='fb_669391906':
        #    logging.debug('TODO: remove this test mode')
        #    continue
        bdays = u.get_birthdays()
        excludes = u.get_excludes()
        logging.debug('helper.send_birthday_gifts: date:%s, user %s(%s) has %s birthday friends'%(tk,u.key().name(),u.name or '',len(bdays)))
        if tk in bdays:
            for uid in bdays[tk].split(','):
                if not uid: continue
                if uid[0] in ['M','F']:
                    gender = uid[0]
                    uid = uid[1:]
                else:
                    gender = 'B'
                if not uid in excludes:
                    if u.usemyown and u.mygifts:
                        mgs = u.get_mygifts()
                        if mgs and len(mgs)>0:
                            gift = get_random_gift(mgs,gender)
                        else:
                            gift = get_random_gift(gs,gender)
                    else:
                        gift = get_random_gift(gs,gender)
                    if gift:
                        logging.debug('helper.send_birthday_gifts: issue task to send gift %s to %s'%(gift,uid))
                        taskqueue.add(url='/task/bdaygift',params={'uid':uid,'at':u.access_token,'g':gift}) 
        count += 1
    if count >= 500:
        logging.debug('helper.send_birthday_gifts: more than 500, issue another task')
        taskqueue.add(url='/task/birthday',params={'cursor':uq.cursor()})

def get_random_gift(gs,gender):
    """ Find a same-gender gift from gs, if no same-gender one in 10 tries, randomly choose one. """
    n = len(gs)-1
    if n < 0: return None
    if gender.startswith('B'):
        return gs[random.randint(0,n)]
    for i in xrange(10):
        g = gs[random.randint(0,n)]
        if g.startswith(gender):
            return g
    return gs[random.randint(0,n)]

def send_gift(web):
    uid = web.request.get('uid')
    access_token = web.request.get('at')
    gift = web.request.get('g')
    if not uid:
        logging.debug('helper.send_gift: no uid')
        return
    if not access_token:
        logging.debug('helper.send_gift: no access_token')
        return
    if not gift:
        logging.debug('helper.send_gift: no gift')
        return
    logging.debug('helper.send_gift (task): sending gift to %s'%uid)  
    args = {'access_token':access_token}
    args['message'] = 'Happy Birthday!'
    args['name'] = 'Here is a virtual gift for you!'
    args['link'] = 'http://apps.facebook.com/suicomics/gift/open?g=%s'%gift
    args['caption'] = "Open to see what's in it."
    args['picture'] = 'http://suicomics.appspot.com/img/gift.png?v=2'
    args['actions'] = '{"name":"Open it!","link":"http://apps.facebook.com/suicomics/gift/open?g=%s"}'%gift 
    #args['description']=''
    file = None
    try:
        file = urllib.urlopen('https://graph.facebook.com/%s/feed'%uid,urllib.urlencode(args))
        resp = file.read()
#        logging.debug('helper.send_gift: feed posted to %s, result: %s'%(uid,resp))
    except:
        logging.warning('helper.send_gift: urlfetch error, ignored')
    finally:
        if file: file.close()
    
def get_friends(me,fields=None):
    """ FB Get friends using graph api with fields.
    """
    url = 'https://graph.facebook.com/me/friends?access_token=%s'%me.access_token
    if fields:
        url += '&fields=%s'%fields
    resp = None
    try:
        logging.debug('helper.get_friends, about to call graph api')
        #file = urllib.urlopen(url,urllib.urlencode(args))
        file = urllib.urlopen(url)
        resp = file.read()
        logging.debug('helper.get_friends: read=%s'%resp)
    finally:
        if file: file.close()
    return resp

GIFT_VIEW_HTML='''<html><head></head><body><div style="text-align:center;"><table style="margin:5px auto;background:url(/img/bg1.png);border-top:1px solid yellow;border-left:1px solid yellow;border-right:1px solid black;border-bottom:1px solid black;"><tr><td style="padding:32px;">
<div style="background-color:white;padding:10px;text-align:center"><img onclick="javascript:location.href='/fb/?use=gift';" valign="middle" src="http://suicomics.appspot.com/mm/bdg_%s"/></div></td></tr></table>
<div>This gift was designed by <a href="http://www.facebook.com/profile.php?id=%s" target="_top"><img valign="middle" src="http://graph.facebook.com/%s/picture"/></a> for the free Birthday-Gift Agent on <a href="http://www.facebook.com/apps/application.php?id=179008415461930" target="_blank">Suinova Comics</a>.</div>
<div><input type="checkbox" checked="checked"> I like this gift-sending agent, too! <a href="/fb/?use=gift">Check it out</a>.</div>
</div></body></html>
'''
    
def gen_gift_view(gid):
    """ Return a html page for gift view.
    """
    uid = None
    gs = SuiBirthdayGift.get_by_key_name(gid)
    if gs:
        uid = gs.creator
        if uid.startswith('fb_'):
            uid=uid[3:]
    if not uid: uid = '669391906'
    html = GIFT_VIEW_HTML % (gid,uid,uid)
    return html
