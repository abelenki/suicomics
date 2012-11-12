#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging,re

from google.appengine.ext import db
from models import *

SHARED_SECRET = 'c1cc7130f68f498b91ed97869e97281a'  #common secret for signature by all games while each game has an individual secret

def default(web, terms=None):
    """ Default handler of this module. """
#    logging.debug('home.default, trying to render home.html')
    web.add_var('genres',pack_genres(SuiGenre.query() or []))
    #allbks = SuiBook.query_by_title() or []
    recommended = SuiBook.query_top_recommended(10) or []
    newbks = SuiBook.query_new_books() or []
    promoted = SuiBook.get_promoted() or ''
    web.add_var('recommended',recommended)
    web.add_var('newbooks',newbks)
    web.add_var('promoted',promoted)
    #web.add_var('stories', helper.get_new_stories() or [])
    ids = recommended + newbks + [promoted]
    if web.logged_in:
        me = web.user
        myreads = me.get_reads()
        web.add_var('myreads',myreads)
        ids += myreads.keys()
        web.add_var('mybooks',{})
        if me.isAuthor():
            ma = SuiAuthor.get_by_key_name(me.key().name())
            if ma:
                myworks = ma.get_works()
                web.add_var('mybooks',myworks)
                ids += myworks.keys()
        #web.add_var('activities',helper.load_activities(web.user))  # NOT implemented yet
        web.add_var('myinfo',{'uid':me.key().name(),'role':me.role,'pts':me.points,'recs':me.recommends or '','inv':me.inventory or {}})
    else:
        web.add_var({'mybooks':{},'mybooks':{},'myreads':{},'myinfo':{}})
    web.add_var('books',pack_books(list(set(ids))))
    web.render_page('home.html')
    
def pack_genres(grs):
    if not grs: return []
    #gr = []
    #for g in grs:
    #    gr.append([g.genre,len(g.books or []),g.books])
    return [[g.genre,len(g.books or []),g.books] for g in grs]
    
def pack_books(ids):
    """ Load all SuiBook entities for ids and pack as brief format for display on web page.
        @return : {id:{"title":"...","authors":["",""],...},...}
    """
    bks = SuiBook.load_by_ids(ids)
    if not bks:
        return '{}'
    #key().id(),title,authors,status,intro,genre,stars,visits,toc,recommends,promoted,version
    buf = []
    anames = SuiAuthor.get_names()   #{id:name,..}
    for bid,bk in bks.items():
        #buf.append(str(bk.key().id()))
        #buf.append(':{')
        pps = []
        bk.authors = ['%s:%s'%(a,anames[a]) for a in bk.authors]
        for p,t in bk.properties().items():
            pps.append('"%s":%s' % (p,format_property(t,p,getattr(bk,p))))
        #buf.append(','.join(pps))
        buf.append('"%s":{%s}'%(str(bk.key().id()),','.join(pps)))
    return '{%s}'%','.join(buf)
    
def format_property(proptype,propname,propval):
    """ Format DateTimeProperty to ISO format, and strings with " as \" """
    if propval is None:
        return '""'
    elif isinstance(proptype, db.DateTimeProperty):
        return '"%s"'%datetime.strftime(propval,'%Y-%m-%d %H:%M:%S')
    elif isinstance(proptype, db.StringProperty):
        if propval.find('"')>=0:
            return '"%s"'%propval.replace('"','\\"')
        else:
            return '"%s"'%propval
    elif isinstance(proptype, db.TextProperty):
        if not propval:
            return '""'
        elif propval[0] in ['[','{']:
            if propname == 'quests':
                if propval.find('items')>0:
                    import re
#                    return re.sub(r'"items":\[[^ ]*\],','',propval)
                    return re.sub(r'"items":\[[^ ]*\],',lambda s:'"items":[%s],'%','.join(re.findall(r'vgid":(\d+),',s.group(0))),propval)
            return propval
        else:
            return '"%s"'%propval
    elif isinstance(proptype, db.BooleanProperty):
        if propval:
            return 'true'
        else:
            return 'false'
    elif isinstance(proptype, db.StringListProperty):
        return '[%s]'%','.join('"%s"'%s for s in propval)
    return propval
    
def authors(web, args=None):
    """ Return a list of authors for the authors page. Ignore those confirm == False
        [{"uid":"gg_xx","name":"name","job":"Artist","books":4,"intro":"..."},..]
    """
    from templite import jsonize
    def pack_authors(athrs):
        buf = []
        for a in athrs:
            if not a.confirmed: continue
            bks = len(re.findall('\[',a.works or ''))
            buf.append('{"uid":"%s","name":"%s","job":"%s","books":%d,"intro":%s}' % (a.key().name(),a.name,a.job,bks,jsonize(a.intro)))
        return '[%s]'%','.join(buf)
    athrs = SuiAuthor.query_authors()
    web.succeed(pack_authors(athrs))
    
def books(web,args=None):
    """ Load books by author. """
    if not args:
        web.fail('Not enough parameter')
        return
    if args[0] == 'author':
        aid = args[1]
        #bks = SuiBook.query_by_author(aid)
        #buf = []
        #for bk in bks:
        #    buf.append('"%s"'%bk.id())
        #using SuiAuthor is easier
        logging.debug('home.books, aid=%s'%aid)
        a = SuiAuthor.get_by_key_name(aid)
        if not a:
            web.fail('Author not found')
            return
        bks = a.get_works().keys()
        logging.debug('.works=%s,bks=%s'%(a.works,bks))
        web.succeed(bks)
    elif args[0] == 'genre':
        genre = args[1]
        aus = SuiAuthor.get_names()
        buks = SuiBook.query_by_genre(genre)  #[id,..]
        #bks = [[bk.key().id(),bk.title,['%s:%s'%(a,aus[a]) for a in bk.authors],bk.version] for bk in buks]
        #logging.debug('/home/books/genre/%s: %s'%(genre,bks))
        bks = {"genre":"%s"%genre,"books":buks or []}
        web.succeed(bks)
    elif args[0] == 'ids':
        ids = args[1].split(',')
        #bks = SuiBook.load_by_ids(ids)
        web.succeed(pack_books(ids))
    else:
        web.fail('Not supported argument %s'%args[1])
        
def book(web,args=None):
    """ Query a single book entity and return JSON dict. /home/book/book_id """
    if not args:
        web.fail('Not enough parameter')
        return
    logging.debug('home.book, args[0]=%s'%args[0])
    web.succeed(pack_books([args[0]]))
    
def goods(web,args=None):
    """ Load goods by author or book. 
        args = ['author','aid'] or ['ids','1,2,3,..n']
    """
    def pack_goods(gds):
        """ name,type,book,author,price,display,note,likes """
        buf = []
        for gk,g in gds.items():
            buf.append('{"id":"%s","name":"%s","type":"%s","book":"%s","price":%d,"display":"%s","likes":%d,"note":"%s","version":%d,"gallery":"%s"}' % (g.key().id(),
                       g.name,g.type,g.book,g.price or 0,g.display,g.likes or 0,g.note,g.version or 0,g.gallery))
        return '[%s]'%','.join(buf)
    if not args:
        web.fail('Not enough argument')
        return
    if args[0] == 'author':
        aid = args[1]
        gds = SuiGoods.query_by_author(aid)
        web.succeed(pack_goods(gds))
    elif args[0] == 'ids':
        vgs = web.get_param('ids')
        logging.debug('home.goods/ids=%s'%vgs)
        vgids = vgs.split(',')
        if len(vgids)==1 and vgids[0] == '':
            web.fail('No id given')
            return
        gds = SuiGoods.load_by_ids(vgids)
        web.succeed(pack_goods(gds))
    else:
        web.fail('Not supported parameter %s'%args[1])
    
def make_sig(d, params, game_secret):
    """ Generate a signature for the user-session parameters with the shared_secret and game_secret. """
    import hashlib
    buf = ''.join(['%s=%s'%(k,d.get(k)) for k in sorted(params)])
    sig = hashlib.md5(buf + SHARED_SECRET + game_secret).hexdigest()
    logging.debug('game.make_sig, buf=[%s],sig=%s'%(buf,sig))
    return sig
    
def galleries(web,args=None):
    """ Return galleries.
    """
    tops = dict((u.key().name(),u.items) for u in SuiGallery.query_top_collectors() or [])
    actives = dict((u.key().name(),datetime.strftime(u.lastime,'%Y-%m-%d %H:%M:%S')) for u in SuiGallery.query_latest_actives() or [])
    rts = {'top':tops,'active':actives}
    #logging.debug('home.galleries: rts=%s'%rts)
    if web.logged_in:
        friends = web.user.friends
        if friends:
            rts['friends'] = friends
    web.succeed(rts)

def forums(web,args=None):
    """ Return list of forums: {'forums':[{id:2,forum:'',note:'',group:2,order:2,posts:0,moderators:''},..],'posts':[{id:1,author:'',time:'',subject:''},
    """
    forums = SuiForum.load_all()
    if not forums:
        web.succeed('{}')
        return
    s = []
    for f in forums:
        s.append('{"id":%d,"forum":"%s","note":"%s","group":%d,"order":%d,"posts":%d,"mods":"%s"}' % (f.key().id(),f.forum,f.note,f.group,f.order,f.posts,f.moderators))
    fs = '"forums":[%s]'%','.join(s)
    logging.info('forums.load_by_forum, forum.key.id=%d'%forums[0].key().id())
    posts = SuiPost.load_by_forum(forums[0].key().id())
    s = []
    for p in posts:
        s.append('{"id":%d,"author":"%s","time":"%s","subject":"%s"}'%(p.key().id(),p.author,datetime.strftime(p.postime,'%Y-%m-%d %H:%M:%S'),p.subject))
    ps = '"posts":[%s]'%','.join(s)
    web.succeed('{%s,%s}'%(fs,ps))
    
def posts(web,args=None):
    """ Return a list of posts of a forum.
        /home/posts/forum_id
    """
    if not args:
        fid = web.get_param('fid')
    else:
        fid = args[0]
    posts = SuiPost.load_by_forum(fid)
    s = []
    for p in posts:
        s.append('{"id":%d,"author":"%s","time":"%s","subject":"%s"}'%(p.key().id(),p.author,datetime.strftime(p.postime,'%Y-%m-%d %H:%M:%S'),p.subject))
    ps = '[%s]'%','.join(s)
    web.succeed(ps)
    
def post(web,args=None):
    """ Load post content and comments of it.
        post,author,content,comments:[comment0,..commentN]
    """
    if not args:
        pid = web.get_param('pid')
    else:
        pid = args[0]
    pc = SuiContent.all().filter('post =',int(pid)).get()    #TODO: may get multiple records later?
    cmts = []
    for x in xrange(pc.comments):
        cmts.append('"%s"'%getattr(pc,'comment%d'%x))
    s = '{"post":%s,"author":"%s","cnt":"%s","cmts":%s}' % (pid,pc.author,pc.content,'[%s]'%','.join(cmts))
    web.succeed(s)
    
def newpost(web,args=None):
    """ /home/newpost?sub=subject&cnt=text
        New post: subject length no longer than 120 chars, content not longer than 2000.
    """
    if not web.logged_in:
        web.fail('Not logged in')
        return
    frm,sub,cnt = web.get_params(['frm','sub','cnt'])
    if not frm:
        logging.warning('/home/newpost?frm not found')
        web.fail('Invalid parameter')
        return
    if not sub:
        logging.warning('/home/newpost?sub not found')
        web.fail('Invalid parameter')
        return
    if not cnt:
        logging.warning('/home/newpost?cnt not found')
        web.fail('Invalid parameter')
        return
    if len(sub)>120: sub = sub[:121]
    if len(cnt)>2000: cnt = cnt[:2001]
    madekey = db.Key.from_path('SuiPost',1)
    pid = db.allocate_ids(madekey,1)[0]
    p = SuiPost(key=db.Key.from_path('SuiPost',pid),forum=int(frm),subject=sub)
    p.author = '%s:%s'%(web.user.key().name(),web.user.name)
    c = SuiContent(post=pid,author=p.author,content=cnt)
    db.put([p,c])
    SuiPost.decache_by_forum(frm)
    web.succeed('{"id":%d,"author":"%s","time":"%s","subject":"%s"}'%(p.key().id(),p.author,datetime.strftime(p.postime,'%Y-%m-%d %H:%M:%S'),p.subject))
    
def newcomment(web,args=None):
    """ /home/newcomment?p=post_id&cmt=text
        Comment text length <= 200
    """
    if not web.logged_in:
        web.fail('Not logged in')
        return
    pid,cmt = web.get_params(['p','cmt'])
    if not pid:
        logging.warning('/home/newcomment?no p')
        web.fail('Invalid parameter')
        return
    if not cmt:
        logging.warning('/home/newcomment?no cmt')
        web.fail('Invalid parameter')
        return
    if len(cmt)>200:
        cmt = cmt[:201]
    pc = SuiContent.all().filter('post =',int(pid)).get()
    if pc:
        cnt = '[%s:%s@%s]%s' %(web.user.key().name(),web.user.name,datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H:%M:%S'),cmt)
        setattr(pc,'comment%d'%pc.comments,cnt)
        pc.comments += 1
        pc.put()
        web.succeed()
    else:
        web.fail('Post not found')
        
def pages_unused(web,args=None):
    """ Load all pages of a book. NOTE: use /book/pages/bkid instead of this one
        If user logged in, all pages, otherwise, only first several public pages with last page shown as Login required.
        Pack pages as [{id:,sn:,bk:,sc:,ls:,rq:,rw:},..]
        NOTE: if page has rewards, then check user inventory, if rewarded item and qty exist in inventory, remove rewards from dict so that SuiReader ignore the reward.
    """
    def pack_line(p,res=None):
        """ Format a page info into a dict in JSON format.
            @param p: SuiPage entity
            @param res: If not None, fill sc:res, else sc = p.script
        """
        return '{"id":%d,"bk":%d,"sc":%s,"ls":%s,"rq":%s,"rw":%s,"v":%d}' % (p.key().id(),
            p.book,res or p.script or '{}',p.layers or '[]',p.requires or '{}',p.rewards or '{}',p.version or 0)
    
    if not args:
        web.fail('No book')
        return
    pgs = SuiPage.query_by_book(args[0])
    buf = []
    for p in pgs:
        logging.debug('home.pages: %s'%p)
        if p.requires:
            if not web.logged_in:
                buf.append(pack_line(p,'Login required'))
                break
        if web.logged_in and p.rewards:
            invs = web.user.get_inventory()
            rwds = p.get_rewards()  #{"id":{"id":1,..}}
            nrw = {}
            for vid in rwds:
                if vid not in invs:
                    logging.debug('home.pages: reward vg %s not in inventory') 
                    nrw[vid] = rwds[vid]
            p.put_rewards(nrw)  #for this reader only, do not save
            logging.debug('home.pages: new reward: %s'%p.rewards)
        buf.append(pack_line(p))
    web.succeed('[%s]'%','.join(buf))
    
def feedback(web,args=None):
    """ Forward a message to admin.
    """
    if not web.logged_in:
        web.redirect_with_msg('Login required.')
        return
    msg = web.get_param('msg')
    if not msg:
        web.redirect_with_msg('Empty message.')
        return
    sender = web.user
    msg2 = 'Sender: %s (%s), email: %s, on %s (GMT)\n\n%s' % (sender.name,sender.key().name(),sender.email,datetime.utcnow(),msg)
    import helper
    helper.send_email('User Message via Contact Page',msg2)
    web.redirect('/')
    