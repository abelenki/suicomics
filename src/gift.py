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
from re import compile
import helper

def default(web, args=None):
    """ Default handler to return the home page and call js to switch to gift view. """
    import home
    web.add_var('pageview','gift')
    home.default(web, args)
    
def account(web, args=None):
    """ Get SuiBirthdayUser entity or notavail. """
    if args:
        uid = args[0]
    else:
        uid = web.get_param('uid')
    u = SuiBirthdayUser.get_by_key_name(uid)
    if u:
        rs = pack_entity(u,['access_token','birthdays'])
        #if want birthdays, need to convert here: rs['birthdays']=u.birthdays #return as a string [M1234566,F232343]
        web.succeed(rs)
    else:
        web.succeed({'notavail':'false'})

def birthdays(web, args=None):
    """ Set or return the SuiBirthdayUser.birthdays as string NOT JSON.
        /gift/birthdays[?bds={"01-01":[F123,M34],..}&n=20
        If no bds is given, returns the birthdays
    """
    web.require_login()
    me = web.user
    bds = web.get_param('bds','')
    try:
        counts = int(web.get_param('n','0'))
    except:
        counts = 0
    u = SuiBirthdayUser.get_by_key_name(me.key().name())
    if u:
        if bds and len(bds)>0:
            ptn = compile(r'"(\d\d-\d\d)":\[([MF\d,]+)\]')
            dct = dict((k,us) for k,us in ptn.findall(bds))
            if len(dct)>0:
                u.birthdays = bds
                u.included = counts
                u.put()
                web.succeed()
            else:
                web.fail('Invalid data')
        else:
            web.succeed(u.birthdays or '')
    else:
        web.succeed('{"error":"no such user"}')
        
def permit(web, args=None):
    """ After user permitted for offline_access, friends_birthday 
        TODO: Call this again when user changes friends (can use FB realtime subscription api)
    """
    web.require_login()
    me = web.user
    u = SuiBirthdayUser.get_by_key_name(me.key().name())
    if not u:
        u = SuiBirthdayUser(key_name=me.key().name(),name=me.name,access_token=me.access_token) #update access_token when user change password
    u.creator = me.isAuthor()
    #get user's friends
    fetch_friends(u)
    web.redirect('/gift')
    
def fetch_friends(u):
    rs = helper.get_friends(u,'birthday,gender')
    #logging.debug('gift.permit: helper.get_friends return %s'%rs)
    if rs.find('data') > 0:
        import re
        ptn = re.compile(r'\{"birthday":"(\d\d)[/\\]*(\d\d)[\d/\\]*","gender":"(\w+)","id":"(\d+)"\}')
        mdu = {}
        count = 0
        for mm,dd,gender,uid in ptn.findall(rs):
            k = '%s-%s' % (mm,dd)
            if not gender: gender = 'M'
            suid = '%s%s' % (gender[0].upper(),uid)
            if k not in mdu:
                mdu[k] = [suid]
                count += 1
            else:
                mdu[k].append(suid)
                count += 1
                if len(mdu[k])>15:
                    logging.warning('gift.permit: user %s(%s) has %d friends on birthday on %s' % (me.key().name(),me.name,len(mdu[k]),k))
        u.birthdays = '{%s}'%','.join(['"%s":[%s]'%(k,','.join(uids)) for k,uids in mdu.items()])
        u.included = count
        u.put()
    
def refresh_friends(web, args=None):
    """ Reload friends. """
    web.require_login()
    me = web.user
    u = SuiBirthdayUser.get_by_key_name(me.key().name())
    if not u:
        web.fail('Not registered user')
        return
    fetch_friends(u)
    web.succeed()
    
def upload(web, args=None):
    """ Upload a gift image, or flash movie swf.
        Space used not counted into SuiUser.spaceused.
    """
    web.require_author()
    me = web.user
    gname,gcat,gsex,gpic,myown = web.get_params(['gname','gcat','gsex','gpic','myown'])
    if not gpic:
        web.redirect_with_msg('No picture uploaded')
        return
    if not gname:
        gname = gcat
    imgfile = web.request.POST.get('gpic').filename
    x = imgfile.rfind('.')
    if x < 0:
        web.redirect_with_msg('Unknown image file')
        return
    ext = imgfile[x+1:].lower()
    if ext not in ['jpg','png','gif','swf']:
        web.redirect_with_msg('Image format not supported, only .jpg,.gif,.png','gift')
        return
    if not gsex: gsex = 'B'
    gsex = gsex[0].upper()
    if not gsex in ['M','F','B']: gsex = 'B'
    akey = db.Key.from_path('SuiBirthdayGift',1)
    gid = db.allocate_ids(akey,1)[0]
    gkey = '%s%s'%(gsex,gid)
    g = SuiBirthdayGift(key_name=gkey,creator=me.key().name(),name=gname,category=gcat,gender=gsex)
    u = SuiBirthdayUser.get_by_key_name(me.key().name())
    u.usemyown = (myown == 'myown')
    ms = MediaStore(key_name='bdg_%s'%gkey)
    ms.stream = db.Blob(gpic)
    ms.format = ext
    ms.usage = 'BDG'
    u.add_mygift(gkey)
    db.put([ms,u,g])
#    ms.put()
    helper.update_gift_cache('add',gkey, me.key().name())
    web.redirect('/gift')

def delete(web, args=None):
    """ Delete a gift.
        /gift/delete/gkey
    """
    web.require_author()
    if args:
        gkey = args[0]
    else:
        gkey = web.get_param('gkey')
    me = web.user
    logging.debug('gift.delete: gkey=%s'%gkey)
    u = SuiBirthdayUser.get_by_key_name(me.key().name())
    g = SuiBirthdayGift.get_by_key_name(gkey)
    if u and g:
        if g.creator != me.key().name():
            web.fail('No permission')
            return
        ms = MediaStore.get_by_key_name('bdg_%s'%gkey)
        try:
            db.delete([ms,g])
            u.del_mygift(gkey)
            helper.update_gift_cache('del',gkey,me.key().name())
            u.put()
            web.succeed()
        except:
            logging.exception('Failed to delete my gift (%s)'%me.key().name())
            web.fail('Cannot delete, retry later')
    else:
        web.fail('Not valid birthday user or gift')
        
def exclude(web, args=None):
    web.require_login()
    me = web.user
    uids = web.get_param('ids')
    logging.debug('gift.exclude: ids=%s'%uids)
    if uids:
        u = SuiBirthdayUser.get_by_key_name(me.key().name())
        if not u:
            logging.warning('gift.exclude: user not registered')
            web.fail('Not registered to use Gift Agent')
            return
        u.excludes = uids
        u.put()
        web.succeed()
    else:
        web.fail('Bad parameters')
        
def include(web, args=None):
    web.require_login()
    me = web.user
    if args:
        uid = args[0]
    else:
        uid = web.get_param('uid')
    logging.debug('gift.include: uid=%s'%uid)
    if uid:
        u = SuiBirthdayUser.get_by_key_name(me.key().name())
        if not u:
            logging.warning('gift.include: user not registered')
            web.fail('Not registered to use Gift Agent')
            return
        uids = u.get_excludes()
        if uid in uids:
            uids.remove(uid)
            u.excludes = ','.join(uids)
            u.put()
            web.succeed()
        else:
            web.fail('Not in the list, please refresh your browser')
    else:
        web.fail('Bad parameter')
        
def add_friend(web, args=None):
    """ Add a friend with birth month and day. 
        /gift/add_friend/uid/mm/dd/M|F or
        /gift/add_friend?u=<uid>&m=mm&d=dd&g=M|F
        Add a friend to giftuser with birthday (manually):
        http://suicomics.appspot.com/gift/add_friend/100000477046877/02/10/F
    """
    web.require_login()
    me = web.user
    if args and len(args)>2:
        uid = args[0]
        m = args[1]
        d = args[2]
        gender = args[3].upper()
    else:
        uid,m,d,gender = web.get_params(['u','m','d','g'])
        gender = gender.upper()
    if uid and m and d and gender:
        try:
            dk = '%02d-%02d'%(int(m),int(d))
            gu = SuiBirthdayUser.get_by_key_name(me.key().name())
            if not gu:
                logging.error('gift.add_friend: user not registered for gift')
                web.fail('Not registered to use Gift Agent')
                return
            bds = gu.get_birthdays()
            if not dk in bds:
                bds[dk] = '%s%s'%(gender,uid)
                gu.put_birthdays(bds,True)
            else:
                ubs = bds[dk].split(',')
                if uid not in ubs:
                    ubs.append('%s%s'%(gender,uid))
                    bds[dk] = ','.join([s for s in ubs if s])
                    gu.put_birthdays(bds,True)
        except:
            logging.error('gift.add_friend: m=%s,d=%s'%(m,d))
            web.fail('Invalid m or d')
            return
    else:
        logging.error('gift.add_friend: bad params:uid=%s,month=%s,day=%s,gender=%s'%(uid,m,d,gender))
        web.fail('Invalid params')
        