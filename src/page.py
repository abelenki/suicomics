#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging
from models import *
import helper

def default(web, args=None):
    """ Default handler to return a page image. This is called by SuiReader.
        /page/<book_id>/<page_seq> or /page?bk=<book_id>&p=<page_seq>
        First get a pagelist from the specified book, from first to <page_seq>, if all public, then return image, otherwise
        Check logged in user, if logged in, and read record is on or after <page_seq>, then check page requirements against user inventory.
        If one of the required items in previous pages exist in the inventory, then return, else return a list of required items, and prompt to buy first.
    """
    #logging.info('page.default, args=%s'%args[0])
    if not args:
        bkid, pseq = web.get_params(['bk','p'])
    elif len(args) > 1:
        bkid = args[0]
        pseq = args[1]
    else:
        logging.warning('page.default, not enough arguments')
        web.fail('Invalid call')
        return
    try:
        bid = int(bkid)
        pn = int(pseq)
    except:
        logging.warning('page.default, bk=%s,p=%s'%(bkid,pseq))
        web.fail('Bad numbers')
        return
    book = SuiBook.seek_by_id(bkid)
    if not book:
        logging.warning('page.default, book not found for %s'%bkid)
        web.fail('Book not found')
        return
    pagelist = SuiPage.query_by_book(book)
    if pn >= len(pagelist):
        logging.warning('page.default, p=%s,len(pagelist)=%d'%(pseq,len(pagelist)))
        web.fail('Out of pages')
        return
    me = None
    rd = None
    rp = 0
    inv = {}
    if web.logged_in:
        me = web.user
        rd = me.get_reads().get(bkid)
        if rd:
            rp = rd[1]  #last page i read
            if pn < rp:
                return_page(web,'bp%s_%s'%(bkid,pagelist[pn].key().id()))
                return
        inv = me.get_inventory()
    i = rp
    while i <= pn:
        pg = pagelist[i]
        i += 1
        if pg.requires:
            if me:
                reqs = pg.get_requires()    #{"item_id":qty,..}
                #logging.info('page.default: page %s, requires=%s'%(i,reqs))
                if len(reqs) > 0 and not [x for x in reqs.keys() if x in inv and inv[x]>=reqs[x]]:
                    gds = SuiGoods.load_by_ids(reqs.keys())
                    buf = []
                    for gk,g in gds.items():
                        buf.append({"id":g.key().id(),"name":g.name,"price":g.price,"note":g.note or ''})
                    web.fail({'error':'require','vgs':buf,'page':i-1})
                    return
            else:
                web.require_login()
                return
    if me and me.set_reads(bkid,pn):
        SuiLog.log_read(me,bkid,pn)
        me.save()
    return_page(web,'bp%s_%s'%(bkid,pagelist[pn].key().id()))

def default_old(web, args=None):
    """ Default handler to return a page image. This is called by SuiReader.
        /page/<book_id>/<page_seq> or /page?bk=<book_id>&p=<page_seq>
        First get a pagelist from the specified book, from first to <page_seq>, if all public, then return image, otherwise
        Check logged in user, if logged in, and read record is on or after <page_seq>, then check page requirements against user inventory.
        If one of the required items in previous pages exist in the inventory, then return, else return a list of required items, and prompt to buy first.
    """
    #logging.info('page.default, args=%s'%args[0])
    if not args:
        bkid, pseq = web.get_params(['bk','p'])
    elif len(args) > 1:
        bkid = args[0]
        pseq = args[1]
    else:
        logging.warning('page.default, not enough arguments')
        web.fail('Invalid call')
        return
    try:
        bid = int(bkid)
        pn = int(pseq)
    except:
        logging.warning('page.default, bk=%s,p=%s'%(bkid,pseq))
        web.fail('Bad numbers')
        return
    book = SuiBook.seek_by_id(bkid)
    if not book:
        logging.warning('page.default, book not found for %s'%bkid)
        web.fail('Book not found')
        return
    pagelist = SuiPage.query_by_book(book)
    if pn >= len(pagelist):
        logging.warning('page.default, p=%s,len(pagelist)=%d'%(pseq,len(pagelist)))
        web.fail('Out of pages')
        return
    #New: sort pagelist by SuiBook.pages, but currently assuming the order is always correct, (append and delete always be done at the end)
    me = None
    if web.logged_in:
        me = web.user
        inv = me.get_inventory()
#        logging.info('--------inventory: %s'%inv)
    i = 0
    while i <= pn:
        pg = pagelist[i]
        i += 1
        if pg.requires:
            if me:
                reqs = pg.get_requires()    #{"item_id":qty,..}
                found = (len(reqs) <= 0)
                for rk,rq in reqs.items():
                    if rk in inv:
#                        logging.info('----------required: %s:%s, in inv? %s, inv.qty > required? %s >= %s'%(rk,rq,rk in inv, inv[rk], rq))
                        if inv[rk] >= rq:
                            found = True    #one is found, then pass
                            break
                if not found:
                    buf = []
                    gds = SuiGoods.query_by_book(bkid)
                    for gk,g in gds.items():
                        if gk in reqs:
                            buf.append({"id":g.key().id(),"name":g.name,"price":g.price,"note":g.note or ''})
                    web.fail({'error':'require','vgs':buf,'page':i-1})
                    return
            else:
                web.require_login()
                return
    if me and me.set_reads(bkid,pn):
        SuiLog.log_read(me,bkid,pn)
        me.save()
    return_page(web,'bp%s_%s'%(bkid,pagelist[pn].key().id()))

MIME = {'png':'image/png','jpg':'image/jpeg','gif':'image/gif','swf':'application/x-shockwave-flash','mid':'audio/mid','mp3':'audio/mpeg','jpeg':'image/jpeg'}
def return_page(web,kname):
    """ Simply return SuiPage with key_name=kname as an image. 
    """
#    logging.info('page.return_page, kname=%s'%kname)
    img = MediaStore.get_by_key_name(kname)
    if img:
        web.response.headers['Content-Type'] = MIME[img.format]
        web.response.out.write(img.stream)
    else:
        web.fail('Image not found')

MIME = {'png':'image/png','jpg':'image/jpeg','gif':'image/gif','swf':'application/x-shockwave-flash','mid':'audio/mid','mp3':'audio/mpeg','jpeg':'image/jpeg'}
def image(web,args=None):
    """ This returns a bp[bkid]_[pgid] image to the owner only.
        /page/image/pgid
    """
    web.require_author()
    if not args:
        pgid = web.get_param('pg')
    else:
        pgid = args[0]
    if not pgid:
        logging.warning('page.image: pg id not given')
        web.fail('Page not given')
        return
    try:
        pg = int(pgid)
    except:
        logging.warning('page.image:, pg=%s'%pgid)
        web.fail('Bad page number')
        return
    p = SuiPage.get_by_id(pg)
    if not p:
        logging.warning('page.image: page %s not found'%pgid)
        web.fail('Page not found')
        return
    me = web.user
    if not p.author or p.author != me.key().name():
        book = SuiBook.seek_by_id(p.book)
        if not book:
            logging.warning('page.image: book not found for %s'%book)
            web.fail('Book not found')
            return
        if me.key().name() not in book.authors:
            web.fail('No permission')
            return
    mm = MediaStore.get_by_key_name('bp%s_%s'%(p.book,pg))
    if not mm:
        logging.warning('page.image: media not found for bp%s_%s'%(p.book,pg))
        web.fail('Image not found')
        return
    web.response.headers['Content-Type'] = MIME[mm.format]
    web.response.out.write(mm.stream)
    
def get_valid_page(bkids, pgids, me):
    """ Get SuiPage entity by pgids and SuiBook entity by SuiPage.book, and get index of page in book.
        @param bkids : SuiBook.key().id() as string
        @param pgids : SuiPage.key().id() as string
        @param me : SuiUser entity
        @return : (SuiBook, SuiPage, pagex)
        @exception : "bk is null","pg is null","book x not read","pg # not int","page # not found in book","page.book != bk","page out of index"
    """
    if not bkids:
        raise Exception('bk is null')
    if not pgids:
        raise Exception('pg is null')
    myreads = me.get_reads()
    if bkids not in myreads:
        raise Exception('book %s not read'%bkids)
    try:
        pgid = int(pgids)
    except:
        raise Exception('pg %s is not int'%pgids)
    page = SuiPage.get_by_id(pgid)
    if not page:
        raise Exception('page %s not found in book %s'%(pgids,bkids))
    if str(page.book) != bkids:
        raise Exception('page.book != bk')
    book = SuiBook.seek_by_id(page.book)
    pagex = book.find_page_index(pgid)
    if pagex < 0:
        raise Exception('page %s out of index'%pgids)
    return (book, page, pagex, myreads)
    
def collect(web,args=None):
    """ SuiReader calls to collect a free item on the page.
        The item can be already collected before, so check to make sure it's done.
        if old page, check myreads[bk][2], if exist ignore, else add;
        if this page is last page, check last item in myreads[bk][2] list, if equal, then got already, else add;
        problem: if last item on an earlier page is the same, then this one is also ignored! tell authors to avoid using same items consecutively
        /page/collect?bk=bkid&pg=pgid&vg=vgid&qty=1 (pgid is unique.
    """
    web.require_login()
    me = web.user
    bk,pgid,vgid,qtys = web.get_params(['bk','pg','vg','qty'])
    book,page,pagex,myreads = get_valid_page(bk, pgid, me)
    myreadpagex = myreads[bk][1]
#    if myreadpagex > pagex:
#        #i have read this page before, so no more reward
#        web.fail('Reward received before')
#        return
    if myreadpagex < pagex:
        logging.error('page.reward: my read page %d < page %d'%(myreadpagex,pagex))
        raise Exception('Page out of index')
#    logging.info('collect.1. myreads[bk][2]=%s,bk=%s,pg=%s'%(myreads,bk,pgid))
    #if myreads[bk][2] > 0:
    #    web.fail('Collected already.')
    #    return
    #check vg is really a free item in the page, it's in rewards table
    rwds = page.get_rewards()
    if not vgid in rwds:
        raise Exception('vg %s not a reward'%vgid)
    qty = 1
    if qtys:
        try:
            qty = int(qtys)
            if qty < 1: qty = 1
        except:
            pass
    item = SuiGoods.load_one(vgid)
    if not item:
        raise Exception('%s not a vg'%vgid)
    collected = myreads[bk][2].split(',')
    #if old page, check myreads[bk][2], if exist ignore, else add;
    #if this page is last page, check last item in myreads[bk][2] list, if equal, then got already, else add
    #problem: if last 2 pages have the same items, then the latest one is ignored!
    if myreadpagex > pagex:
        if vgid in collected:
            raise Exception('Collected recently')
    else:
        if len(collected)>0 and collected[-1]==vgid:
            raise Exception('Collected recenty')
    me.add_item(vgid,qty)
    if vgid in collected:
        collected.remove(vgid)
    collected.append(vgid)
    logging.info('page.collect: collected=%s'%collected)
    me.set_reads(bk,pagex,collected)
#    logging.info('collect.2. myreads[bk][2]=%s,bk=%s,pg=%s'%(myreads,bk,pgid))
    me.save()
    web.succeed({"item":vgid,"qty":qty,"name":item.name})   #{item:id,qty:1,name:item_name}
    
def reward(web,args=None):
    """ SuiReader calls to check and dispatch the rewards on a page.
        /page/reward?bk=bkid&pg=pgid&vg=id
        If page has this vg in rewards, and this page is not read before, add it to SuiUser.inventory.
        Page is marked as read when calling /page/bk/pgid, but done is set to 1 after script is executed.
        @return: {'item':{'id':VG_id,'ver':0,'name':'','note':''} or {'error':msg}
    """
    web.require_login()
    me = web.user
    bk,pgs,vg = web.get_params(['bk','pg','vg'])
    book,page,pagex,myreads = get_valid_page(bk, pgs, me)
    myreadpagex = myreads[bk][1]
#    if myreadpagex > pagex:
#        #i have read this page before, so no more reward
#        web.fail('Reward received before')
#        return
    if myreadpagex < pagex:
        logging.error('page.reward: my read page %d < page %d'%(myreadpagex,pagex))
        raise Exception('Page out of index')
    #if myreads[bk][2] > 0:
    #    web.fail('Rewarded')
    #    return
#    logging.info('1. myreads[bk][2]=%s,bk=%s,pg=%s'%(myreads,bk,pgs))
    rwds = page.get_rewards()   #{'vgid':{'vgid':qty,..},..}
    if vg in rwds:
        inv = me.get_inventory()    #{"item":qty,
        for rqvgid,qty in rwds[vg].items():
            if rqvgid not in inv:
                logging.debug('page.reward: no required item %s, bk=%s,pg=%s,vg=%s'%(rqvgid,bk,pgs,vg))
                raise Exception('No required item')
            if inv[rqvgid] < qty:
                logging.debug('page.reward: not enough required item %s, bk=%s,pg=%s,vg=%s'%(rqvgid,bk,pgs,vg))
                web.fail('Not enough required items for this reward')
                return
        v = SuiGoods.load_one(vg)
        if not v:
            logging.warning('page.reward: bk=%s,pg=%s,vg=%s'%(bk,pgs,vg))
            raise Exception('Item not found')
        collected = myreads[bk][2].split(',')
        if myreadpagex > pagex:
            if vg in collected:
                raise Exception('Collected already')
        else:
            if len(collected)>0 and collected[-1]==vg:
                raise Exception('Collected already')
        me.add_item(vg)
        if vg in collected:
            collected.remove(vg)
        collected.append(vg)
        me.set_reads(bk,pagex,collected)
#        logging.info('2. myreads[bk][2]=%s,bk=%s,pg=%s'%(myreads,bk,pgs))
        me.save()
        res = {'item':{'id':v.key().id(),'ver':v.version,'name':v.name,'note':v.note}}  #{item.id, ver, name, note}
        web.succeed(res)
    else:
        logging.warning('page.reward: vg not in rewards: bk=%s,pg=%s,vg=%s'%(bk,pgs,vg))
        web.fail('item not found')
