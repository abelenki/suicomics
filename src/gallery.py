#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging
from models import *
import helper

def default(web, args=None):
    """ Default handler to return a page image.
        /gallery/
    """
    import home
    web.add_var('pageview','gallery')
    home.default(web, args)

def collect(web,args=None):
    """ User collect a VG from inventory to SuiGallery room.
        /gallery/collect/vgid
        If no space in all rooms, return out of space and fail, else put in the middle of first available room.
        @return: {'k':new_vg_key_in_gallery, 'id':VG_id,'x':n,'y':n,'z':n} or error msg: No room, Server error.., Not in your inventory,..
    """
    web.require_login()
    vgid = args[0]
    me = web.user
    inv = me.get_inventory()
    if vgid not in inv:
        web.fail('Not in your inventory, please refresh.')
        return
    gd = SuiGoods.load_one(vgid)
    if not gd:
        web.fail('Not valid goods')
        return
    if not gd.gallery:
        web.fail('Not for show')
        return
    g = SuiGallery.get_by_user(me.key().name())
    if not g:
        g = SuiGallery(key_name=me.key().name())
    r = g.add_item(vgid)
    if not r:
        web.fail('No room')
        return
    try:
        me.remove_item(vgid)
        db.put([g,me])
        me.recache()
        g.recache()
        web.succeed({'items':r['items'],'k':r['k'],'id':vgid,'x':r['x'],'y':r['y'],'z':r['z'],'v':'%s'%gd.version,'name':gd.name,'note':gd.note or '','bk':gd.book})
    except Exception,e:
        logging.exception(e)
        web.fail('Server error, retry later')

def all(web,args=None):
    """ Flash get all gallery data for a given user.
        /gallery/all/uid
        web return if successful: {uid:"uid",rooms:n,items:n,content:{vgkey:{},..},vgs:{vg:..}}
    """
    if args:
        uid = args[0]
    else:
        uid = web.get_param('uid')
    u = helper.query_user_by_key(uid)
    if not u:
        web.fail('User not found')
        return
    sg = SuiGallery.get_by_user(uid)
    give = 0
    if not sg:
        sg = SuiGallery(key_name=uid)
        vgids = None
    else:
        if (datetime.utcnow()-sg.lastime).days >= 1:
            give = 1
            sg.save()
        vgids = sg.get_unique_item_ids()
    if vgids:
        vgs = SuiGoods.load_by_ids(vgids)
        ves = ['"%s":{"name":"%s","v":%d,"note":"%s","bk":%s}' % (vk,vg.name,vg.version,vg.note or '',vg.book) for vk,vg in vgs.items()]
    else:
        ves = []
    r = '{"uid":"%s","name":"%s","rooms":%d,"items":%d,"content":%s,"vgs":{%s},"give":%d}' % (uid,u.name,sg.rooms,sg.items,sg.content or {},','.join(ves),give)
    web.succeed(r)
        
def moveto(web,args=None):
    """ Flash moves one item (VG) from one position to another, to a room.
        How to move across rooms on the client side? a large Flash horizontal scrolling canvas? with arrows on left and right edge to scroll.
        With drag and drop the object can be placed anywhere.
        /gallery/moveto/key/x/y[/z]
    """
    web.require_login()
    z = None
    if args:
        itmkey = args[0]
        x = int(args[1])
        y = int(args[2])
        if len(args) > 3: z = int(args[3])
    else:
        itmkey,xs,ys,zs = web.get_params(['itmkey','x','y','z'])
        x = int(xs)
        y = int(ys)
        if zs: z = int(zs)
    myg = SuiGallery.get_by_user(web.user.key().name())
    if myg:
        myg.move_item(itmkey,x,y,z)
        myg.save()
        web.succeed({'id':itmkey,'x':x,'y':y})
    else:
        web.fail('Failed to move %s'%itmkey)
        
def tofront(web,args=None):
    """ Bring an object to front - topmost layer.
        /gallery/tofront/itmkey
    """
    web.require_login()
    itmkey = args[0]
    myg = SuiGallery.get_by_user(web.user.key().name())
    if myg:
        r=myg.bring_to_front(itmkey)
        myg.save()
        web.succeed(r)
    else:
        web.fail('Gallery not available')
        
def toback(web,args=None):
    """ Send to back - bottom-most layer.
        /gallery/toback/itmkey
    """
    web.require_login()
    itmkey = args[0]
    myg = SuiGallery.get_by_user(web.user.key().name())
    if myg:
        r=myg.send_to_back(itmkey)
        myg.save()
        web.succeed(r)
    else:
        web.fail('Gallery not available')

def resize(web,args=None):
    """ Flash resizes an object.
        /gallery/resize/itmkey/sx/sy
    """
    web.require_login()
    if args:
        itmkey = args[0]
        sx = float(args[1])
        sy = float(args[2])
    else:
        itmkey,sxs,sys = web.get_params(['itmkey','sx','sy'])
        sx = float(sxs)
        sy = float(sys)
    myg = SuiGallery.get_by_user(web.user.key().name())
    if myg:
        myg.resize_item(itmkey,sx,sy)
        myg.save()
        web.succeed({'id':itmkey,'sx':sx,'sy':sy})
    else:
        web.fail('Failed to resize %s'%itmkey)
        
def revoke(web,args=None):
    """ Flash call to revoke a VG from gallery back to inventory.
        /gallery/revoke/itmkey
    """
    web.require_login()
    itmkey = args[0]
    me = web.user
    myg = SuiGallery.get_by_user(me.key().name())
    if myg:
        itm = myg.remove_item(itmkey)
        if itm:
            me.add_item(itm)
            #me.save()
            try:
                db.put([myg, me])
                myg.recache()
                me.recache()
                web.succeed({'key':itmkey,'id':itm})
            except Exception,e:
                logging.exception(e)
                web.fail('Server error, retry later')
        else:
            web.fail('Error removing item from gallery, retry later')
    else:
        web.fail('No gallery found')
        
def misc(web,args=None):
    """ Flash update item ms attribute """
    web.fail('Not implemented')

def credits(web,args=None):
    """ After user sent 5 free gallery credits, this is called with five uids, or a user pick it up.
        /gallery/credits/sent?ids=uid1,uid2,..
        /gallery/credits/pick?g=galleryid
    """
    if not args: return
    web.require_login()
    me = web.user
    op = args[0]
    if op == 'sent':
        ids = web.get_param('ids')
        logging.info('gallery.credits.sent: ids=%s'%ids)
        #append ids to SuiGallery.sent
        sg = SuiGallery.get_by_user(me.key().name())
        sg.sent = ','.join(['%s_%s'%(web.sns,id) for id in ids])
        sg.save()
        web.redirect('/')
        return
    elif op == 'pick':
        logging.info('user pick a credit')
        #check if user in SuiGallery.
        g = web.get_param('g')
        if g:
            sg = SuiGallery.get_by_user(g)
            if not sg:
                logging.warning('gallery.credits.pick g=%s not found'%g)
                return
            sents = (sg.sent or '').split(',')
            u = me.key().name()
            if u in sents:
                del sents[sents.index(u)]
                sg.sent = ','.join(sents)
                dbs = [sg]
                usr = SuiGallery.get_by_user(u)
                if usr:
                    usr.credits += 1
                    dbs.append(usr)
                db.put(dbs)
                sg.recache()
                usr.recache()
                web.redirect('/')
                return
            else:
                logging.debug('gallery.credits.pick: user %s not in sents'%u)
        else:
            logging.warning('gallery.credits.pick: g=%s'%g)
    else:
        logging.warning('gallery.credits/%s bad cmd'%op)
    web.fail('failed')
    