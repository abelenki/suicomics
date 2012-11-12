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
    """ Default handler to return the home page and call js to switch to market view. """
    import home
    web.add_var('pageview','market')
    home.default(web, args)
    
def top(web, args=None):
    """ Load best-selling items for shops. Maximum of 1000 items.
        @return {'shops':{gamekey:{name:,items:[key,key,]},'items':{'itemkey':{name,price,developer,game,display,likes}
    """
    itms = SuiGoods.query_top_buys() #top 20 best buys so far
    if len(itms) < 1:
        web.succeed({'shops':{},'items':{}})
        return
    shops = {}
    items = {}
    logging.info('home.market, query_top_buys returned: %s'%itms)
    for itmid,itm in itms.items():
        if not itm.display: continue
        #itmid = str(itm.key().id())
        bkid = itm.book #str
        ausname = '%s:%s'%(itm.author,SuiAuthor.get_name(itm.author))
        items[itmid] = {'name':itm.name,'price':itm.price,'note':itm.note or '','author':ausname,'book':itm.book,'display':str(itm.display),'likes':itm.likes,'version':itm.version}
        if bkid in shops:
            shops[bkid]['items'].append(itmid)
        else:
            bkname = SuiBook.seek_by_id(bkid).title
            shops[bkid]={'name':bkname,'items':[itmid]}
    itms = {'shops':shops,'items':items}
    web.succeed(itms)
    
def items(web,args=None):
    """ Load all items for a book, max=1000
        /market/items/bkid
        @return: [{"id":vgid,"name":"vg_name","price":1.0,"note":"note"},..]
    """
    if args:
        bkid = args[0]
    else:
        bkid = web.get_param('bk')
    itms = SuiGoods.query_by_book(bkid)
    if not itms:
        web.succeed({'bk':args[0],'items':[]})
        return
    items = []
    for vgid,vg in itms.items():
        if not vg.display: continue
        itm = '{"id":%s,"name":"%s","price":%s,"note":"%s","version":%s}'%(vgid,vg.name,vg.price,vg.note,vg.version)
        items.append(itm)
    web.succeed('{"bk":"%s","items":[%s]}'%(bkid,','.join(items)))
    
def delitem(web,args=None):
    """ Delete a virtual goods. 
        /market/delitem/vgid
    """
    web.require_author()
    me = web.user
    if args:
        vgid = args[0]
    else:
        vgid = web.get_param('vgid') or web.get_param('id')
    if not vgid:
        web.fail('No item specified')
        return
    try:
        vid = int(vgid)
    except:
        web.fail('Not proper item id')
        return
    itm = SuiGoods.get_by_id(vid)
    if itm:
        if itm.author != me.key().name():
            web.fail('Not owner')
            return
        SuiGoods.clearcache([vgid,me.key().name(),itm.book])
        itm.delete()
        web.succeed()
    else:
        web.fail('Item not found')

def upload(web, args=None):
    """ Upload a new virtual goods item.
        A VG has a 50x50 logo image and a large image suitable for display in gallery. 
        Some VGs do not have a big image because they never used in galleries.
    """
    #if not web.logged_in:
    #    raise Exception('Not login')
    web.require_author()
    paramkeys = ['id','itm','bkid','price','note','display','logofile','imgfile']
    itemid,itemname,bkid,price,note,display,logo,img = web.get_params(paramkeys)
    newitem = False
    if itemid:
        itm = from_cache(itemid)
        if not itm:
            itm = SuiGoods.get_by_id(int(itemid))
    else:
        madekey = db.Key.from_path('SuiGoods', 1) #why 1?
        itemid = db.allocate_ids(madekey, 1)[0]
        itmkey = db.Key.from_path('SuiGoods',itemid)
        itm = SuiGoods(key=itmkey)
        newitem = True
    if itemname: itm.name = itemname
    if display == 'True':
        itm.display = True
    else:
        itm.display = False
    if bkid:itm.book = bkid
    itm.author = web.user.key().name()
    if price:itm.price = float(price)
    if itm.price <= 0: 
        itm.display = False
    else:
        itm.returnable = True
    itm.giftable = itm.display
    if note:itm.note = note
    dbs = [itm]
    ver = 0
    au = web.user.get_author()
    if img:
        imgfile = web.request.POST.get('imgfile').filename
        ms = save_img(imgfile,img,740,500,'vgb',itemid,bkid,newitem)
        if ms:
            ver = 1
            dbs.append(ms)
            au.spaceused += len(db.model_to_protobuf(ms).Encode())
        else:
            web.response.out.write('<html>Only .jpg or .png supported. <a href="/market">Go Back</a></html>')
            return
    if logo:
        logofile = web.request.POST.get('logofile').filename
        mst = save_img(logofile,logo,50,50,'vg',itemid,bkid,newitem)
        if mst:
            ver = 1
            dbs.append(mst)
            au.spaceused += len(db.model_to_protobuf(mst).Encode())
        else:
            web.response.out.write('<html>Only .jpg or .png supported. <a href="/market">Go Back</a></html>')
            return
    elif img:
        mst = save_img(imgfile,img,50,50,'vg',itemid,bkid,newitem)
        if mst:
            ver = 1
            dbs.append(mst)
            au.spaceused += len(db.model_to_protobuf(mst).Encode())
    if ver > 0:
        itm.version += ver
        dbs.append(au)
        web.user.recache()
    try:
        db.put(dbs)
        helper.decaches(['VG_%s'%itm.author,'VG_%s'%au.key().name(),'%s'%itm.key().id()])
        web.redirect('/author')
    except Exception,e:
        logging.error(e)
        web.response.out.write('<html>Error saving your item, retry later. <a href="/market">Go Back</a></html>')

def save_img(filename,stream,width,height,prefix,item,bkid,newitem):
    """ Resize image stream and save into MediaStore with proper format from file extension.
    """
    ext = file_extension(filename)
    if ext in ['jpg','png']:
        m,w,h = image_resize(stream,ext,width,height)
        keyname = '%s_%s' % (prefix.lower(),item)
        if newitem:
            ms = MediaStore(key_name=keyname,book=bkid,usage=prefix.upper(),format=ext)
        else:
            ms = MediaStore.get_by_key_name(keyname)
            if ms:
                ms.format = ext
                ms.decache()
            else:
                ms = MediaStore(key_name=keyname,book=bkid,usage=prefix.upper(),format=ext)
        ms.stream = db.Blob(m)
        ms.width = w
        ms.height = h
        return ms
    else:
        logging.debug('Not jpg or png file: %s'%filename)
        return None

def image_resize(img, ext, width, height):
    """ Check image data and resize it into the specified dimension if necessary.
        @param img: image binary data from request
        @param ext: file extension of the image, must be 'jpg' or 'png'
        @param width: max width allowed, if greater, resize the image
        @param height: max height allowed, if greater, resize the image
        @return: original image stream or resized image stream
    """
    from google.appengine.api import images
    m = images.Image(img)
    w = m.width
    h = m.height
    if m.width > width or m.height > height:
        m.resize(width,height)
        w = m.width
        h = m.height
        if ext == 'png':
            oenc = images.PNG
        else:
            oenc = images.JPEG
        m = m.execute_transforms(oenc)
    else:
        m = img
    return (m,w,h)

def file_extension(fname):
    """ Get file extension in lower case such as 'jpg', 'png'.
    """
    x = fname.rfind('.')
    if x < 0:
        return ''
    return fname[x+1:].lower()

#def recache(web,args=None):
#    helper.decache('VirtualGoods')

def donate(web, args=None):
    """ Reader donate some money to a book page. Always a page ID is enough.
        /market/donate?pid=<page_id>&pts=<points>
        Condition: page valid, reader has enough su points.
    """
    web.require_login();
    if args:
        pid = args[0]
        pts = args[1]
    else:
        pid,pts = web.get_params(['pid','pts'])
    me = web.user
    try:
        points = int(pts)
        page_id = int(pid)
    except:
        logging.warning('market.donate: not number: pid=%s,pts=%s'%(pid,pts))
        web.fail('Invalid numbers')
        return
    if me.points >= points:
        web.fail('Not enough Su-Dollars')
        return
    page = SuiPage.get_by_id(page_id)
    if page:
        author = page.author
        book = SuiBook.seek_by_id(page.book)
        if book:
            book.clear_page_list()
            if not author:
                author = book.authors[0]
            #take points from me to author
            a = from_cache(author)
            if not a:
                a = SuiUser.get_by_key_name(author)
                if not a:
                    logging.warning('market.donate: author %s not found'%author)
                    web.fail('Author %s not found'%author)
                    return
            #save transaction first, need to save this in a taskqueue?
            es = [me,a,SuiTransaction(user=me.key().name(),book=str(book.key().id()),goods=pid,amount=0,points=points)]
            me.points -= points
            a.points += points
            db.put(es)
            me.recache()
            a.recache()
            web.succeed({'pts':me.points})
        else:
            web.fail('Book not found for page %s'%pid)
    else:
        web.fail('Page %s not found'%pid)
        
def buyitem(web, args=None):
    """ Player bought a virtual goods from market, and the item will be stored in SuiUser.inventory.
        Only the buyer herself can do this operation, and it's done through https.
        Request parameter:
        /pay/buyitem?itm=xxx+yyy&qty=nnn 
    """
    logging.debug('Enter pay.buyitem, args=%s'%args)
    web.require_login();
#    if not web.logged_in:
#        web.fail('Not login')
#        return
    if args:
        itm_s = args[0]
        qtys = args[1]
    else:
        itm_s,qtys = web.get_params(['itm','qty'])
    logging.debug('itm=%s,qty=%s'%(itm_s,qtys))
    try:
        qty = int(qtys)
        if qty < 1:
            web.fail('Invalid amount')
            return
    except:
        web.fail('Invalid amount')
        return
    import re
    itms = [int(t) for t in set(re.split(r'[ +]',itm_s))]
    me = web.user
    price = 0.0
    gds = [g for g in SuiGoods.get_by_id(itms) if g]
    if not gds:
        web.fail('Items not found')
        return
    es = []
    minv = me.get_inventory()
    nitems = []
    for g in gds:
        gid = str(g.key().id())
        nitems.append(gid)
        price += g.price
        g.likes += 1
        g.recache()
        es.append(g)
        es.append(SuiTransaction(user=me.key().name(),book=g.book,goods=gid,amount=qty,points=int(qty*price)))
        minv[gid] = minv.get(gid, 0) + qty
    total = price * qty #can be zero
    if me.points >= total:
        #enter critical_section
        helper.lock_process('BuyItem_%s'%me.key().name())   #if already locked, then raise Exception to avoid reentry
        #1.insert new SuiTransaction, 2.update inventory,Points and save SuiUser, 3. log SuiLog in taskqueue,
        #step 1. insert item into SuiPosession,if fail revoke me.points, key_name = user_key_name+item_name, when transfer, insert and delete
#        txn = SuiTransaction(user=me.key().name(),book=bkid,goods=itm,amount=qty,points=int(total))
        me.put_inventory(minv)
        me.points -= int(total)
        es.append(me)
        me.recache()
        try:
            db.put(es)
            web.succeed({'pts':me.points,'item':' '.join(nitems),'quantity':qty,'total':total})
            taskqueue.add(url='/task/dau',params={'usr':me.key().name(),'act':'buy','par':nitems,'qty':str(qty)})
        except Exception,e:
            logging.exception(e)
            web.fail('Server error, try later')
            helper.unlock_process('BuyItem_%s'%me.key().name())
            return
        #step 2. add item/qty to inventory,decrease my points,if fail to save, delete the saved sp
#        try:
#            inv = me.get_inventory()
#            #logging.debug('step 2, inv=%s'%inv)
#            inv[itm] = inv.get(itm,0)+qty
#            me.put_inventory(inv)
#            #logging.debug('put back inventory done')
#            me.points -= int(total)
#            me.save()   #even points given back, no harm to save here
#            web.succeed({'pts':me.points,'item':itm,'quantity':qty,'total':inv[itm]})
#            #step 4. log this with taskqueue
#            taskqueue.add(url='/task/dau',params={'usr':me.key().name(),'act':'buy','par':itm,'qty':str(qty)})
#        except:
#            logging.error('Failed to save SuiUser after putting , so remove txn')
#            try:
#                txn.delete()
#            except:
#                pass
#            web.fail('Server error, try later')
        #leave critical_section
        helper.unlock_process('BuyItem_%s'%me.key().name())
    else:
        web.fail('Not enough Su-Dollars')
        return
        
