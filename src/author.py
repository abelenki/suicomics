#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging
from datetime import datetime
from google.appengine.ext import db
from google.appengine.api import taskqueue
from models import *
import helper

def default(web, args=None):
    """ Default handler to return the home page and call js to switch to author view. """
    import home
    web.add_var('pageview','author')
    home.default(web, args)
    
def check_get_book_page(web,bkid,pgid=None):
    """ Check user is author, book, page exists, and return (book,page) entities """
    web.require_author()
    book = SuiBook.seek_by_id(bkid)
    if not book:
        raise Exception('Book not found')
    if web.user.key().name() not in book.authors:
        raise Exception('Book author only')
    if not pgid:
        return (book,None)
    p = SuiPage.get_by_id(int(pgid))
    if not p:
        raise Exception('Page not found')
    return (book,p)

def addpage(web,args=None):
    """ Add a page to the book, at the end. """
    bk = web.get_param('bk')
    book, p = check_get_book_page(web,bk)
    if book.pagecount >= 500:
        web.fail('Sorry, but you reached maximum number of pages allowed for a book.')
        return
    madekey = db.Key.from_path('SuiPage',1)
    pid = db.allocate_ids(madekey,1)[0]
    p = SuiPage(key=db.Key.from_path('SuiPage',pid),book=int(bk))
    if web.user.key().name() != book.authors[0]:
        p.author = web.user.key().name()
    book.add_page(pid)
    try:
        db.put([p, book])
        book.recache_updates()
        web.succeed({'id':pid,'bk':bk,'sc':'','ls':[],'rq':{},'rw':{},'v':p.version})
        taskqueue.add(url='/task/feed/add_page',params={'uname':web.user.name,'bkid':bk,'title':book.title})
    except Exception,e:
        logging.exception(e)
        web.fail('Failed to add page, try later')
    
def delpage(web,args=None):
    """ Delete a page by page id.
        TODO: delete images as well and other layers if available
    """
    bk,pg = web.get_params(['bk','pg'])
    book, p = check_get_book_page(web,bk,pg)
    p.delete()
    book.remove_page(pg)
    imgkey = 'bp%s_%s' % (bk,pg)
    img = MediaStore.get_by_key_name(imgkey)
    if img:
        img.delete()
    book.save()
    web.succeed({'bk':bk,'pages':book.pagecount})
    
def addrequired(web,args=None):
    """ Add a vgoods to the page.requires.
    """
    bkid,pgid,vgid=web.get_params(['bk','pg','vg'])
    book, p = check_get_book_page(web, bkid, pgid)
    rs = p.add_requires(vgid)
    if not rs:
        web.fail('No more than three allowed')
    if hasattr(book, '_pages_list'):
        delattr(book, '_pages_list')
    web.succeed()
    
def delrequired(web,args=None):
    bkid,pgid,vgid = web.get_params(['bk','pg','vg'])
    book,p = check_get_book_page(web,bkid,pgid)
    p.del_requires(vgid)
    if hasattr(book, '_pages_list'):
        delattr(book, '_pages_list')
    web.succeed()
    
def addreward(web,args=None):
    bkid,pgid,vgid=web.get_params(['bk','pg','vg'])
    book,p = check_get_book_page(web,bkid,pgid)
    p.add_reward(vgid)
    if hasattr(book, '_pages_list'):
        delattr(book, '_pages_list')
    web.succeed()
    
def delreward(web,args=None):
    bkid,pgid,vgid = web.get_params(['bk','pg','vg'])
    book,p = check_get_book_page(web,bkid,pgid)
    p.del_reward(vgid)
    if hasattr(book, '_pages_list'):
        delattr(book, '_pages_list')
    web.succeed()

def addscript(web,args=None):
    bkid,pgid,sc = web.get_params(['bk','pg','sc'])
    if not sc:
        web.fail('Empty code')
        return
    book,p = check_get_book_page(web,bkid,pgid)
    # TODO: add script validation here
    logging.info('author/addscript TODO: add script validation here')
    if p:
        p.script = sc
        p.save_page(book)
        web.succeed()
    else:
        web.fail('Book page note found')
    
def pagenote(web,args=None):
    """ Add a page note """
    bkid,pgid,notes = web.get_params(['bk','pg','notes'])
    if not notes:
        web.fail('Empty notes')
        return
    logging.info('author/pagenote,bk=%s,pgid=%s,notes=%s'%(bkid,pgid,notes))
    book,p = check_get_book_page(web,bkid,pgid)
    if p:
        p.notes = notes.replace('"','&quot;').replace('\r','').replace('\n','<br/>')
        p.save_page(book)
        web.succeed()
    else:
        web.fail('Book page not found')
        
def zines(web,args=None):
    """ load a list of zines by author keyname """
    szs = SuiZine.load_by_author(args[0])
    buf = []
    for sz in szs:
        buf.append('["%s","%s"]'%(sz.key().id(),sz.title))
    web.succeed('[%s]'%','.join(buf))
    
def profile(web,args=None):
    """ get author's profile
        /author/profile
        if logged by one self, return spaceused,address and email, otherwise only public data
        links are formated as JSON: {'Web':'http://...','Twitter':'','LinkedIn':'','Blog':'','Other':''}
    """
    aid=args[0]
    au = SuiAuthor.get_by_key_name(aid)
    if not au or not au.confirmed:
        web.fail('Author not found')
        return
    myself = web.logged_in and web.user.key().name()==aid
    rs = {'uid':aid}
    for pname,typ in au.properties().items():
        pvalue = getattr(au,pname)
        if pname in ['spaceused','address','email']:
            if myself:
#                logging.info('author.profile: myself=%s,pname=%s,pvalue=%s'%(myself,pname,pvalue))
                rs[pname] = pvalue or ''
        elif pname == 'links':
            rs[pname] = au.get_links()
        elif pname == 'works':
            rs[pname] = au.get_works()
        elif pname != 'confirmed':
            rs[pname] = pvalue or ''
    if myself and 'email' not in rs:
        rs['email'] = web.user.email or ''
#    logging.info('author.profile: au.works=%s'%rs['works'])
    web.succeed(rs)
