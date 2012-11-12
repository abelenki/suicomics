#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging
from google.appengine.ext import db
from google.appengine.api import taskqueue
from models import *
import helper

SHARED_SECRET = '0ab8a58179f94eb29bfd0ffc43165aeb'
SECRET_CODE = 'da8b181e4eb3499e91cba2eba0cd8fc0'

def default(web, args=None):
    """ Default handler to return the home page and call js to switch to author view. """
    import home
    pg = 'home'
    if args:
        if args[0]=='author':
            pg = args[0]
        else:
            pg = 'book.%s'%args[0]
    else:
        bkid = web.get_param('bk')
        if bkid:
            pg = 'book.%s'%bkid
    web.add_var('pageview',pg)
    home.default(web, args)
    
def read(web, args=None):
    """ Reader opened a book to read. If logged in, record users reading list and return env, else ignore.
    """
    if args:
        bkid = args[0]
    else:
        bkid = web.get_param('bk')
    if not bkid:
        web.fail('No book specified')
        return
    book = SuiBook.seek_by_id(bkid)
    if not book:
        web.fail('Book not found')
        return
    if not web.logged_in:
        web.succeed()
        return
    me = web.user
    myreadlist = me.get_reads()
    if not bkid in myreadlist:
        me.set_reads(bkid)
        me.save()
    web.succeed({'lastpage':myreadlist[bkid][1]})
    
def make_sig(d, params, game_secret):
    """ Generate a signature for the user-session parameters with the shared_secret and game_secret. """
    import hashlib
    buf = ''.join(['%s=%s'%(k,d.get(k)) for k in sorted(params)])
    sig = hashlib.md5(buf + SHARED_SECRET + game_secret).hexdigest()
    logging.debug('game.make_sig, buf=[%s],sig=%s'%(buf,sig))
    return sig

def upload(web, args=None):
    """ Upload a new book or update an old book info.
        If it's a new book, all followers are notified by email.
        Note: only first author can modify an existing book (owner).
    """
    web.require_author()
#    if not web.logged_in:
#        raise Exception('Not login')
    paramkeys = ['bkid','title','status','logofile','intro','toc','notes','authors','zine','height','quests']
    bkid,title,status,logo,intro,toc,notes,authors,zine,height,quests = web.get_params(paramkeys)
    newbook = False
    if bkid:
        bk = SuiBook.seek_by_id(bkid)
        if not bk:
            logging.warning('book %s not found'%bkid)
            web.redirect_with_msg('Invalid Book ID','book')
            return
        if web.user.key().name() != bk.authors[0]:
            web.redirect_with_msg('No permission','book')
            return
    else:
        madekey = db.Key.from_path('SuiBook',1)
        bkid = db.allocate_ids(madekey,1)[0]
        bk = SuiBook(key=db.Key.from_path('SuiBook',bkid))
        bk.authors = [web.user.key().name()]
        if zine and zine!='none':
            bk.zine = zine
            bk
        newbook = True
    if title: bk.title = title
    if status: bk.status = status
    genres = web.request.get('genre', allow_multiple=True)
    if genres: bk.genre = list(set(genres))
    if intro: bk.intro = join_lines(intro)
    if toc: bk.toc = join_lines(toc,'ul')
    if notes: bk.notes = join_lines(notes)
    if quests:
        bk.quests = validate_quests(quests)
    if height:
        try:
            bk.height = int(height)
        except:
            pass
#    if authors:
#        import re
#        aus = [s for s in re.split(r'[ ,;]',authors) if s]
#        aus = [s.key().name() for s in SuiAuthor.get_by_key_name(aus) if s]
#        if aus:
#            bk.authors = list(set(bk.authors + aus))
    dbs = [bk]
    if logo:
        logofile = web.request.POST.get('logofile').filename
        #logging.debug('-=------- save logofile %s'%logofile)
        x = logofile.rfind('.')
        if x < 0:
            web.fail('Unknown image file')
            return
        ext = logofile[x+1:].lower()
        if ext in ['jpg','png']:
            from google.appengine.api import images
            m = images.Image(logo)
            w = h = 240
            if m.width > 240 or m.height > 240:
                m.resize(240,240)
                w = m.width
                h = m.height
                if ext == 'png':
                    oenc = images.PNG
                else:
                    oenc = images.JPEG
                m = m.execute_transforms(oenc)
            else:
                m = logo
            if newbook:
                ms = MediaStore(key_name='bk_%s'%bkid)
            else:
                ms = MediaStore.get_by_key_name('bk_%s'%bkid)
                if ms:
                    bk.version += 1
                    ms.decache()
                else:
                    ms = MediaStore(key_name='bk_%s'%bkid)
            ms.book = '%s'%bkid
            ms.width = w
            ms.height = h
            ms.usage = 'BK'
            ms.stream = db.Blob(m)
            ms.format = ext
            dbs.append(ms)
            bk.version += 1
    me = SuiAuthor.get_by_key_name(web.user.key().name())
    if not me:
        logging.warning('Book editor is not in SuiAuthor %s'%web.user.key().name())
        web.redirect_with_msg('You are not a registered author','book')
        return
    me.add_book(bk)
    dbs.append(me)
    try:
        db.put(dbs)
        me.recache()
        bk.decache_for_newbook()
        helper.to_cache('%s'%bkid, bk)
        if newbook:
            SuiLog.log_newbook(me,bkid)
            taskqueue.add(url='/task/genre/add_book',params={'genre':','.join(bk.genre),'bkid':bkid})
            taskqueue.add(url='/task/feed/add_book',params={'uid':me.key().name(),'uname':me.name,'bkid':bkid,'title':bk.title,'intro':intro or ''})
        #bdy='Good news! %s published a new book "%s". Visit <a href="http://suicomics.appspot.com">Suinova Comics</a> to check it out.'%(me.name,bk.title)
        #TODO: notify my fans about the new book
        #helper.notify_followers(me,'New book by %s'%me.name,bdy)
        #logging.info('followers notified if any')
        web.redirect('/book/'+bkid)
    except Exception,e:
        logging.error(e)
        web.redirect_with_msg('Error saving your item, retry later.','book')

def delete(web,args=None):
    """ Delete a book
        /book/delete/bkid
    """
    web.require_author()
    me = web.user
    if args:
        bkid = args[0]
    else:
        bkid = web.get_param('bk')
    if not bkid:
        web.fail('No book given')
        return
    bk = SuiBook.seek_by_id(bkid)
    if bk:
        if bk.pages:
            web.fail('Delete all pages first')
            return
        vgs = SuiGoods.query_by_book(bkid,False)
        if vgs:
            web.fail('Delete all its virtual goods first')
            return
        #npgs = map(lambda id:Key.from_path('SuiPage',id),bk.get_pages_list())
        bk.decache_all()
        bk.delete()
        SuiGenre.remove(bk.genre, bkid)
        a = SuiAuthor.get_by_key_name(me.key().name())
        if a:
            bks = a.get_works()
            if bkid in bks:
                del bks[bkid]
                a.put_works(bks)
                a.save()
        mms = MediaStore.all(keys_only=True).filter('book =',bkid).fetch(1000)
        if mms: 
            db.delete(mms)
            helper.decaches(['MM_%s'%m.name() for m in mms])
        web.succeed()
    else:
        web.fail('Book not found')
    
def validate_quests(qs):
    import re
    p = re.compile(r'\[(\{"qid":\d+,"qname":"[\w ]+","items":\[(\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[[^\]]*\]\},)*\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[[^\]]*\]\}\],"prize":\d+,"intro":"[^"\r\n]*"\},)*\{"qid":\d+,"qname":"[\w ]+","items":\[(\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[\]\},)*\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[\]\}\],"prize":\d+,"intro":"[^"\r\n]*"\}\]')
    m = p.match(qs)
    if m:
        logging.info('Valid: qs=%s'%m.group())
        return m.group()
    return None
        
def join_lines(txt,pattern='p'):
    """ Filter out line breaks and replace with HTML <br>, and UL LI for toc.
        @param txt : original text from HTTP, including line breaks
        @param pattern : format around lines, default as p:'<p>%s</p>', can be ul:<li>%s</li>, or ' ' etc.
    """
    lines = txt.replace('<','&lt;').split('\n')
    if pattern == 'p':
        return ''.join(['<p>%s</p>'%ls.strip() for ls in lines if ls])
    elif pattern == 'ul':
        return '<ul>%s</ul>'%''.join(['<li>%s</li>'%ls.strip() for ls in lines])
    else:
        return ' '.join(lines)
        
def pages(web,args=None):
    """ Load and return all pages info as JSON list.
        If a page is read before (review), no requires, for rewards, check collected items, if not found, set it.
        /book/pages/bkid or ?bk=bkid
        Return list: [{"id":123,"bk":101,"sc":"","ls":[],"rq":{},"rw":{}},..]
    """
    def pack_line(p,res=None):
        """ Format a page info into a dict in JSON format.
            @param p: SuiPage entity
            @param res: If not None, fill sc:res, else sc = p.script
        """
        return '{"id":%d,"bk":%d,"sc":%s,"ls":%s,"rq":%s,"rw":%s,"v":%d}' % (p.key().id(),
            p.book,res or p.script or {},p.layers or '[]',p.requires or '{}',p.rewards or '{}',p.version)
    if args:
        bkid = args[0]
    else:
        bkid = web.get_param('bk')
    if not bkid:
        web.fail('No book id')
        return
    book = SuiBook.seek_by_id(bkid)
    if not book:
        web.fail('Book not found')
        return
    pagelist = SuiPage.query_by_book(book)
    rp = 0
    rd = None
    collected = []
    if web.logged_in:
        me = web.user
        rd = me.get_reads().get(bkid)
        if rd:
            rp = rd[1]
            logging.debug('book.pages, me=%s,reads=%s,rd=%s'%(me.key().name(),me.reads,rd))
            collected = set(rd[2].split(','))
    i = 0
    buf = []
    logging.info('book.pages: collected for bk %s: %s'%(bkid,collected))
    for p in pagelist:
        if p.requires:
            if i < rp:
                p.requires = None
            elif not web.logged_in:
                buf.append(pack_line(p, '"Login required"'))
                break
        if p.rewards and collected:
            if i <= rp:
                rwds = p.get_rewards()
                logging.info('book.pages: page %s, rewards: %s'%(i,p.rewards))
                nwds = dict((r,rwds[r]) for r in rwds.keys() if r not in collected)
                logging.info('book.pages: new rewards: %s'%nwds)
                p.put_rewards(nwds)
        buf.append(pack_line(p))
        i += 1
#    logging.info('book.pages, return=%s'%','.join(buf))
    web.succeed('[%s]'%','.join(buf))
    
def quests(web,args=None):
    """ SuiQuest queries all quests for a book with virtual goods check against reader inventory.
        /book/quests/bkid
        return: {"quests":[{"qid":1,"qname":"xxx","items":[{"vgid":1,"x":1,"y":2,"sc":1.0,"filters":[],"name":"","tip":""},..],"prize":11},..],"filled":[1,2]}
    """
    web.require_login()
    if args:
        bkid = args[0]
    else:
        bkid = web.get_param('bk')
    book = SuiBook.seek_by_id(bkid)
    if not book:
        web.fail('Book not found')
        return
    if not book.quests:
        web.fail('No quests in book')
        return
    qs = book.quests
    #[{"qid":2,"qname":"","items":[{"vgid":101,"x":1,"y":2,"sc":1.2,"filters":["G"]},{"vgid":102}],"prize":200},{"qid":1,"items":[{"vgid":201}]}]
    ITM_PTN = compile(r'"vgid":(\d+)')
    itms = ITM_PTN.findall(qs or '')
    if not itms:
        web.fail('No quests in book')
        return
    inv = web.user.inventory
    rinvs = []
    if inv:
        for itm in list(set(itms)):
            if itm in inv:
                rinvs.append(itm)
    web.succeed('{"quests":%s,"filled":[%s]}'%(qs,','.join(rinvs)))
    