#
#   Copyright 2010 Suinova Designs Ltd.
#

__author__ = "Ted Wen"
__version__ = "0.1"

import logging,random,time
from datetime import datetime,timedelta
from re import compile
from google.appengine.ext import db
from google.appengine.ext.db import Expando
from google.appengine.api import taskqueue
from google.appengine.api import images
from google.appengine.api.memcache import get as from_cache, set as to_cache, delete as decache,get_multi as from_caches,set_multi as to_caches,delete_multi as decaches

"""
    New design of suicomics.appspot.com
    
"""
PLAYER_CACHE_SECS = 7200
MAX_ITEMS_PER_ROOM = 50

READ_PTN = compile(r'"(\d+)":\["([\d T:\-Z]+)",(\d+),"([\d,]*)"\]')
INV_PTN = compile(r'"(\w+)":(\d+)')

class SuiUser(db.Model):
    name = db.StringProperty() #a nickname the user can specify later
    email = db.EmailProperty(indexed=False)
    gender = db.StringProperty(default='M',indexed=False)
    points = db.IntegerProperty(default=0,indexed=False)  #Su points to be bought or sudos/sucash
    supeas = db.IntegerProperty(default=0,indexed=False)   #alternative to points no exchange with real money
    stars = db.IntegerProperty(default=10,indexed=False)    #number of stars every month
    role = db.StringProperty(default='R',indexed=False) #Reader or Author (or a for applied for Authorship)
    regtime = db.DateTimeProperty(auto_now_add=True)
    lastime = db.DateTimeProperty(auto_now=True)
    reads = db.TextProperty()   #bookshelf, {bid:['datetime',page#,'collecteds,..',..}
    inventory = db.TextProperty()   #{'item':qty,..
    recommends = db.TextProperty()  #{bid,...}
    friends = db.TextProperty() #{uid:name,..}
    permit = db.IntegerProperty(indexed=False)    #0=monitored,1=free comment,2=free post,3=can delete others,4=can edit others
    version = db.IntegerProperty(indexed=False)   #kept for logo/avatar image update, increment upon update
    #portrait = db.StringProperty(indexed=False)  #user key_name who painted the portrait, None for not available
    active = db.BooleanProperty(default=True,indexed=False) #set to False if removed
    access_token = db.StringProperty(indexed=False)
    
    def isAuthor(self):
        return self.role.upper() == 'A'
    def canComment(self):
        return self.role == 'A' or self.permit > 0
    def canPost(self):
        return self.role == 'A' or self.permit > 1
    def canDelete(self):
        return self.role == 'A' or self.permit > 2
    def canEdit(self):
        return self.role == 'A' or self.permit > 3
    @property
    def token(self):
        """ Token contains user keyname_timeNumber_randomNumber """
        if not hasattr(self,'_tokens'):
            ts = str(time.time())
            rs = str(random.randint(1234,65535))
            self._tokens = '%s_%s_%s' % (self.key().name(),ts,rs)
        return self._tokens
        
    def recache(self):
        to_cache(self.key().name(), self, PLAYER_CACHE_SECS)
        
    def save(self):
#        logging.debug('!!!lastTime before put(): %s'%self.lastTime)
        self.lastime = self._cache_time = datetime.utcnow()
        self.put()
        to_cache(self.key().name(), self, PLAYER_CACHE_SECS)
        
    def get_reads(self):
        """ Return dict for reads {"bkid":["datetime",page#,"id1,id2,.."],..} """
        if not hasattr(self,'_reads_dict'):
            #READ_PTN = compile(r'"(\d+)":\["([\d T:\-Z]+)",(\d+),"([\d,]*)"\]')
            self._reads_dict = dict((d[0],[d[1],int(d[2]),d[3]]) for d in READ_PTN.findall(self.reads or ''))
#        logging.info('>>> get_reads returns: %s'%self._reads_dict)
        return self._reads_dict
    def put_reads(self,d=None):
        if not d:
            if not hasattr(self,'_reads_dict'):
                logging.error('put_reads(None), but _reads_dict not set')
                raise Exception('_reads_dict not found')
            d = self._reads_dict
        self.reads = '{%s}'%','.join(['"%s":["%s",%s,"%s"]'%(k,v[0],v[1],v[2]) for k,v in d.items()])
    def set_reads(self,bkid,pgs=0,vgs=None):
        """ Add a book to the reading list. """
#        logging.debug('models.set_reads(%s,%s)'%(bkid,pg))
        myreads = self.get_reads()
        try:
            pg = int(pgs)
        except:
            pg = 0
        if bkid not in myreads:
            myreads[bkid] = [datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H:%M:%S'),pg,vgs or '']
        else:
            if myreads[bkid][1] <= pg:
                myreads[bkid][1] = pg
            if vgs:
                if isinstance(vgs,list):
                    myreads[bkid][2] = ','.join(filter(None,vgs))
                elif myreads[bkid][2]:
                    mrs = myreads[bkid][2].split(',')
                    if vgs in mrs: mrs.remove(vgs)
                    mrs.append(vgs)
                    myreads[bkid][2] = ','.join(filter(None,mrs))
                else:
                    myreads[bkid][2] = str(vgs)
        self.put_reads(myreads)
        return True
        
    def get_inventory(self):
        """ {"item":qty, """
        if not hasattr(self,'_inventory_dict'):
            #INV_PTN = compile(r'"(\w+)":(\d+)')
            self._inventory_dict = dict((d[0],int(d[1])) for d in INV_PTN.findall(self.inventory or ''))
        #logging.debug('_inventory_dict = %s'%self._inventory_dict)
        return self._inventory_dict
    def put_inventory(self,dic=None):
        if not dic:
            if not hasattr(self,'_inventory_dict'):
                logging.error('put_inventory, _inventory_dict not set')
                raise Exception('_inventory_dict not found')
            dic = self._inventory_dict
        self.inventory = '{%s}'%','.join(['"%s":%d'%(k,v) for k,v in dic.items()])
    def add_item(self,itm,qty=1):
        """ add item to inventory """
        inv = self.get_inventory()
        s = str(itm)
        inv[s] = inv.get(s, 0) + qty
        self.put_inventory(inv)
    def remove_item(self,itm):
        """ remove itm from inventory """
        inv = self.get_inventory()
        s = str(itm)
        if s in inv:
            if inv[s] > 1:
                inv[s] -= 1
            else:
                del inv[s]
            self.put_inventory(inv)
        
    def get_author(self):
        if not hasattr(self,'_author_e'):
            self._author_e = SuiAuthor.get_by_key_name(self.key().name())
        return self._author_e
    def detach_author(self):
        if hasattr(self,'_author_e'):
            delattr(self,'_author_e')
        
class SuiAuthor(db.Model):
    """ Additional data for authors. key_name == SuiUser.key_name """
    name = db.StringProperty()  #repeated nickname
    title = db.StringProperty() #Mr, Ms, Miss, etc
    firstname = db.StringProperty(indexed=False)
    lastname = db.StringProperty(indexed=False)  #real name if any
    email = db.EmailProperty(indexed=False) #special for author
    address = db.TextProperty()
    job = db.StringProperty(default="AW")  #Artist,Writer,Artist/Writer,etc
    works = db.TextProperty()   #works as author, {bid:['start_time',pages,0|1],..}
    intro = db.TextProperty()   #self-intro
    fbpage = db.LinkProperty(indexed=False)  #facebook fan page
    links = db.TextProperty()   #["web: http:..","twitter:",..] authors self-promotion area
    #followers = db.TextProperty()   #{"uid":"email",..}, use SuiFollower instead
    confirmed = db.BooleanProperty(default=False,indexed=False)
    spaceused = db.IntegerProperty(default=0,indexed=False) #page images + VG images
    
    @classmethod
    def query_authors(cls):
        """ Assume not many authors, so get all at once. Authors must apply and get approved with works.
            TODO: may need paging later when more than 400 authors.
        """
        authors = from_cache('AuthorsList')
        if not authors:
            authors = SuiAuthor.all().order('name').fetch(400)
            to_cache('AuthorsList', authors)
        return authors
        
    def recache(self):
        decaches(['AuthorsList','AuthorNames'])
        
    def save(self):
        self.put()
        #self.recache()
    def get_links(self):
        LNK_PTN=compile(r'"(\w+): ([^"]*)"')
        return dict((d[0],d[1]) for d in LNK_PTN.findall(self.links or ''))
    
    @classmethod
    def get_names(cls):
        aus = from_cache('AuthorNames')
        if not aus:
            authors = SuiAuthor.query_authors()
            aus = dict((a.key().name(),a.name) for a in authors)
            to_cache('AuthorNames',aus)
        return aus
        
    @classmethod
    def get_name(cls,keyname):
        aus = SuiAuthor.get_names()
        if keyname in aus:
            return aus[keyname]
        return ''
        
    def get_works(self):
        """ Return dict for works {bid:['start_time',pages,0|1],..} """
        if not hasattr(self,'_works_dict'):
            READ_PTN = compile(r'"?(\d+)"?:\["([\d T:\-Z]+)",(\d+),(\d)\]')
            self._works_dict = dict((d[0],[d[1],d[2],d[3]]) for d in READ_PTN.findall(self.works or ''))
        return self._works_dict
    def put_works(self,d=None):
        if not d:
            if not hasattr(self,'_works_dict'):
                logging.error('put_works(None), but _works_dict not set')
                raise Exception('_works_dict not found')
            d = self._works_dict
        self.works = '{%s}'%','.join(['"%s":["%s",%s,%s]'%(k,v[0],v[1],v[2]) for k,v in d.items()])
    def add_book(self,bk):
        wrks = self.get_works()
        st = 0
        if bk.status == 'Finished': st = 1
        wrks[str(bk.key().id())] = [datetime.strftime(bk.started,'%Y-%m-%dT%H:%M:%S'),0,st]
        self.put_works(wrks)

class SuiFollower(db.Model):
    """ Followers of both book and author.
        Each author or book has a number of entities of SuiFollower.
        The entity is created with the first follower, and then added to the fans field until over 500 followers,
        then another entity is created, and so on.
        TODO: not implement now
    """
    id = db.StringProperty()    #bk_id or uid
    fans = db.TextProperty()    #{"uid":"email",..}
    count = db.IntegerProperty(default=1,indexed=False) #number of fans
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
    def get_fans(self):
        if not hasattr(self,'_fans_dict'):
            FO_PTN = compile(r'"([\w_.]+)":"([^"]+)"')
            self._fans_dict = dict((e[0],e[1]) for e in FO_PTN.findall(self.fans or ''))
        return self._fans_dict
    
    def put_fans(self,dic=None):
        if not dic:
            if not hasattr(self,'_fans_dict'):
                logging.error('put_fans, _fans_dict not set')
                raise Exception('_fans_dict not found')
            dic = self._fans_dict
        self.fans = '{%s}'%','.join(['"%s":"%s"'%(k,v) for k,v in dic.items()])
    
    @classmethod
    def add_fans(cls,id,uid,email):
        """ Add a follower to book or author by id, if entity exists and fans more than 499 then create a new entity. """
        sfs = SuiFollower.all().filter('id =', id).fetch(100)
        if sfs:
            usf = None
            for sf in sfs:
                fs = sf.get_fans()
                if uid in fs:
                    return
                if sf.count < 500:
                    usf = sf
            if usf:
                fs = usf.get_fans()
                fs[uid] = email
                usf.put_fans(fs)
                usf.count += 1
                usf.put()
            else:
                sf = SuiFollower(id=id,fans='{"%s":"%s"}'%(uid,email))
                sf.put()
        else:
            sf = SuiFollower(id=id)
            sf.fans = '{"%s":"%s"}'%(uid,email)
            sf.put()
            
class SuiGallery(db.Model):
    """ Reader's collage rooms, one room free and more can be bought. key_name = SuiUser.key_name
        Currently we use only content as storage of all items.
        If later the size is not enough, exceeding 1MB sized entity, then add blob0,blob1 up to blob9 and modify content to be {"id_0":{id:0,...,ms:"blob0"},...
        One blob can have 1MB and there can be 10 blobs in an entity, and each blob contains items for one room, and blob data compressed with zlib.
    """
    #uid = db.StringProperty()   #key_name equals that of SuiUser
    #name = db.StringProperty(indexed=False) #user name repeated to save ds call
    lastime = db.DateTimeProperty(auto_now=True)    #updated last time, show off latest updated
    items = db.IntegerProperty(default=1)   #number of items collected in all rooms, as rank
    rooms = db.IntegerProperty(default=1,indexed=False) #how many rooms, can be bought or no less than credits allow
    content = db.TextProperty()   #contents: {"id_0":{id:141,x:-2,y:3,z:0,sx:0.9,sy:1,ms:""},..}
    credits = db.IntegerProperty(default=0)  #determine how many rooms
    sent = db.TextProperty()    #uid-1,..uid-5
    
    @classmethod
    def get_by_user(cls,ukey):
        sg = from_cache('SG_%s'%ukey)
        if not sg:
            sg = SuiGallery.get_by_key_name(ukey)
            if sg:
                to_cache('SG_%s'%ukey, sg, 7200)
        return sg
    
    @classmethod
    def query_latest_actives(cls,N=10):
        usrs = from_cache('LatestActiveCollectors')
        if not usrs:
            usrs = SuiGallery.all().order('-lastime').fetch(N)
            to_cache('LatestActiveCollectors', usrs, 24*3600)
        return usrs
    @classmethod
    def query_top_collectors(cls,N=10):
        usrs = from_cache('TopCollectors')
        if not usrs:
            usrs = SuiGallery.all().order('-items').fetch(N)
            to_cache('TopCollectors',usrs,24*3600)
        return usrs
    
    def get_items_list(self):
        if not hasattr(self,'_items_list'):
            #{"id_0":{id:141,x:-2,y:3,z:0,sx:0.9,sy:1,ms:""},..}
            #RM_PTN = compile(r'\{"id":(\d+),"x":(-?\d+),"y":(-?\d+),"z":(\d+),"sx":([\d.]+),"sy":([\d.]+),"ms":"([^"]*)"}')
            RM_PTN = compile(r'"([\d_]+)":\{"id":(\d+),"x":(-?\d+),"y":(-?\d+),"z":(\d+),"sx":([\d.]+),"sy":([\d.]+),"ms":"([^"]*)"}')
            #self._items_list = [{'id':int(id),'x':int(x),'y':int(y),'z':int(z),'sx':float(sx),'sy':float(sy),'ms':ms} for id,x,y,z,sx,sy,ms in RM_PTN.findall(self.content or '')]
            self._items_list = dict((k,{'id':int(id),'x':int(x),'y':int(y),'z':int(z),'sx':float(sx),'sy':float(sy),'ms':ms}) for k,id,x,y,z,sx,sy,ms in RM_PTN.findall(self.content or ''))
        return self._items_list
    def put_items_list(self,lst=None):
        if not lst:
            if not hasattr(self,'_items_list'):
                raise Exception('put_items_list _items_list not set')
            lst = self._items_list
        self.content = '{%s}'%','.join('"%s":{"id":%d,"x":%d,"y":%d,"z":%d,"sx":%0.1f,"sy":%0.1f,"ms":"%s"}'%(k,c['id'],c['x'],c['y'],c['z'],c['sx'],c['sy'],c['ms']) for k,c in lst.items()) #c['id'],c['x'],c['y'],c['z'],c['sx'],c['sy'],c['ms']) for c in lst)
    @classmethod
    def make_item_record(cls,itm,x=350,y=200,z=1,sx=1,sy=1,ms=''):
        """ Build a item dict with default values """
        return {'id':int(itm),'x':x,'y':y,'z':z,'sx':sx,'sy':sy,'ms':ms}
    
    def add_item(self,itm):
        """ Add an item into the rooms and return a dict {id,itm,x,y,z} or None for not enough room """
        itms = self.get_items_list()
        if len(itms) != self.items: self.items = len(itms)
        if self.items >= self.rooms * MAX_ITEMS_PER_ROOM:
            return None
        k = itm
        x = 0
        while k in itms:
            x += 1
            k = '%s_%d'%(itm,x)
        itm_rec = SuiGallery.make_item_record(itm)
        itm_rec['z'] = self.items;
        itms[k] = itm_rec
        self.put_items_list(itms)
        self.items += 1
        return {'items':self.items,'k':k,'id':itm,'x':itm_rec['x'],'y':itm_rec['y'],'z':itm_rec['z']}
    
    def remove_item(self,itmkey):
        """ Remove item by unique key and return it or None if not found. """
        itms = self.get_items_list()
        if itmkey in itms:
            itm = itms[itmkey]
            z = itm['z']
            del itms[itmkey]
            for k,t in itms.items():
                if t['z'] > z:
                    t['z'] -= 1
            self.put_items_list(itms)
            self.items -= 1
            return itm['id']
        return None

    def get_unique_item_ids(self):
        ks = [s.split('_')[0] for s in self.get_items_list().keys()]
        return list(set(ks)) 
    
    def find_item(self,itmkey):
        itms = self.get_items_list()
        if itmkey in itms:
            itm_rec = itms[itmkey]
            return itm_rec
        return None
    
    def resize_item(self,itmkey,sx,sy):
        itm_rec = self.find_item(itmkey)
        if itm_rec:
            itm_rec['sx'] = float(sx)
            itm_rec['sy'] = float(sy)
            self.put_items_list()
            return True
        return False
    
    def update_item_misc(self,itmkey,ms):
        """ Change ms string for effect, etc. """
        itm_rec = self.find_item(itmkey)
        if itm_rec:
            itm_rec['ms'] = ms
            self.put_items_list()
            return True
        return False
    
    def move_item(self,itmkey,x,y,z=None):
        """ Move item to x,y,z """
        itm_rec = self.find_item(itmkey)
        if itm_rec:
            itm_rec['x'] = int(x)
            itm_rec['y'] = int(y)
            if z: itm_rec['z'] = int(z)
            self.put_items_list()
            return True
        return False
    
    def bring_to_front(self,itmkey):
        """ Move itm to topmost layer with max z and all rest above minus one """
        itms = self.get_items_list()
        if itmkey in itms:
            itm = itms[itmkey]
            z = itm['z']
            for k,it in itms.items():
                if it['z'] > z:
                    it['z'] -= 1
            itm['z'] = len(itms)
            self.put_items_list(itms)
            return {'k':itmkey,'z':itm['z']}
        return None
    def send_to_back(self,itmkey):
        """ Send itm to bottom-most (0) with all items under it add by one """
        itms = self.get_items_list()
        if itmkey in itms:
            itm = itms[itmkey]
            z = itm['z']
            for k,it in itms.items():
                if it['z'] < z:
                    it['z'] += 1
            itm['z'] = 0
            self.put_items_list(itms)
            return {'k':itmkey,'z':itm['z']}
        return None
    
    def recache(self):
        to_cache('SG_%s'%self.key().name(),self)
    def save(self):
        self.put()
        self.recache()

class SuiBook(db.Model):
    title = db.StringProperty()
    initial = db.StringProperty()   #first letter (of pinyin if chinese) of title
    authors = db.StringListProperty()   #authors where first is the owner/creator
    started = db.DateTimeProperty(auto_now_add=True)
    published = db.DateTimeProperty()
    updated = db.DateTimeProperty() #when pages added or modified
    status = db.StringProperty(indexed=False)   #ongoing,finished,cancelled
    intro = db.TextProperty()
    genre = db.StringListProperty()    #romance,satire,horror,adventure,scifi,fantasy,drama,history,mystery,military
    rating = db.StringProperty(indexed=False)
    stars = db.IntegerProperty(default=0)   #total number stars received so far
    visits = db.IntegerProperty(default=0)  #number of views total
    width = db.IntegerProperty(default=740,indexed=False)   #default size of Flash for the pages
    height = db.IntegerProperty(default=640,indexed=False)
    toc = db.TextProperty() #table of content, [{'title':'','p':3},..]
    #pages = db.IntegerProperty(indexed=False)   #number of pages in all
    pages = db.TextProperty()  #a list of SuiPage.key().id() separated by commas
    recommends = db.IntegerProperty(default=0)  #how many recommendations so far
    #followers = db.TextProperty()   #{"uid":"email",..}
    zine = db.StringProperty()  #zine id if any
    notes = db.TextProperty()   #authors take notes or comments about this book
    requires = db.TextProperty()    #{"item":1,"item_2":1,..} required by all pages, may not be used here
    version = db.IntegerProperty(default=0,indexed=False)   #increment upon image update
    quests = db.TextProperty()  #[{qid:2,qname:"",items:[{vgid:,x,y,sc,filters:[],name:'',tip:''},..],prize:vgid,intro:''},..]
    #pages = db.BlobProperty()   #page contents gzipped, for reading only, more efficient than reading from SuiPage
    #characters = db.TextProperty()  #chars in book [
    #maps = db.TextProperty()    #maps if available [
    #promoted = db.TextProperty() #['id:title',..] added by the author, to be displayed on right with the cover page
    
    def recache(self):
        to_cache('%s'%self.key().id(), self)
        
    def save(self):
        self.put()
        to_cache('%s'%self.key().id(), self)
        
    def clear_page_list(self):
        if hasattr(self,'_pages_list'):
            delattr(self,'_pages_list')
    def find_page_index(self,pgid):
        pgs = self.get_pages_list()
        try:
            return pgs.index(str(pgid))
        except:
            return -1
    def get_pages_list(self):
        if not hasattr(self,'_pages_list'):
            self._pages_list = (self.pages or '').split(',')
        return self._pages_list
    def put_pages_list(self,pgs=None):
        if not pgs:
            if not hasattr(self,'_pages_list'):
                raise Exception('put_pages_list, _pages_list not set')
            pgs = self._pages_list
        self.pages = ','.join(pgs)
    @property
    def pagecount(self):
        pgs = self.get_pages_list()
        return len(pgs)
    def add_page(self,pid):
        """ Add pid to the page list """
        pgs = self.get_pages_list()
        if len(pgs) == 1 and pgs[0] == '':
            pgs[0] = str(pid)
        else:
            pgs.append(str(pid))
        self.put_pages_list(pgs)
    def remove_page(self,pid):
        pgs = self.get_pages_list()
        x = self.find_page_index(pid)
        if x >= 0:
            del pgs[x]
            self.put_pages_list(pgs)

    def load_pages(self):
        """ Load SuiPage entities and sort by pages list, and store in _pages_entities. """
        if not hasattr(self,'_pages_entities'):
            pids = self.get_pages_list()
#            logging.info('SuiBook.load_pages: pids = %s'%pids)
            self._pages_entities = SuiPage.get_by_id([int(pid) for pid in pids if pid])
        return self._pages_entities
    
    def update_page_entity(self,pid,pge):
        """ Update a page entity in the pages_entities list.
            @param : pid - int as SuiPage.key().id()
            @param : pge - SuiPage entity
        """
        if not hasattr(self,'_pages_entities'):
            self.load_pages()
        else:
            pgs = self.get_pages_list()
            for i in xrange(len(pgs)):
                pe = pgs[i]
                if pe.key().id() == pid:
                    pgs[i] = pge
                    break

    @classmethod
    def load_by_ids(cls,ids):
        """ Load SuiBook entities by ids, first from memcache, then from datastore for those not in memcache.
            @return : {'book_id':SuiBook,..}
        """
        if not ids or ids[0] == '':
            return None
        es = from_caches(ids)   #(ids,'SuiBook') as prefixed
        notfounds = filter(lambda e:e not in es, ids)
        if len(notfounds)>0:
            es2 = dict((str(e.key().id()),e) for e in SuiBook.get_by_id(map(lambda e:int(e),notfounds)) if e)
            to_caches(es2)  #to_caches(dict(),time,key_prefix='SuiBook')
            es.update(es2)
        return es
        
    @classmethod
    def seek_by_id(cls,id):
        """ find one book by id. """
        bk = from_caches('%s'%id)
        if not bk:
            bk = SuiBook.get_by_id(int(id))
            if bk:
                to_cache('%s'%id, bk)
        return bk
        
    @classmethod
    def query_by_title(cls,initial=None):
        """ books sorted by title starting from a initial, only 100 returned.
            db.GqlQuery('select * from SuiBook where title >= :1 and title < :2',initial,initial+1)
            TODO: modify to use paging when more than 100 books added.
            @return [SuiBook.key(),..] keys_only
        """
        if initial:
            btkey = 'BookByTitle_%s'%initial
            bks = from_cache(btkey)
            if not bks:
                bks = map(lambda e:str(e.id()),SuiBook.all(keys_only=True).filter('initial =',initial).fetch(100))
                to_cache(btkey, bks) #save only SuiBook.key().id()
        else:
            btkey = 'BookByTitle'
            bks = from_cache(btkey)
            if not bks:
                bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).order('title').fetch(100))
                to_cache(btkey,bks)
        return bks
        
    @classmethod
    def query_by_author(cls,author):
        """ books sorted by author name
            select * from SuiBook where authors = author
        """
        bakey = 'BookByAuthor_%s'%author
        bks = from_cache(bakey)
        if not bks:
            bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).filter('authors =',author).fetch(100))
            to_cache(bakey,bks)
        return bks
        
    @classmethod
    def query_by_genre(cls,genre):
        """ This routine returns SuiBook keys_only.
        """
        bgkey = 'BookByGenre_%s'%genre
        bks = from_cache(bgkey)
        if not bks:
            bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).filter('genre =',genre).fetch(100))
            to_cache(bgkey,bks)
        return bks
        
    @classmethod
    def query_latest_updated(cls,N=10):
        """ top N latest updated books.
            select book from SuiBook order by updated desc
        """
        bukey = 'BooksUpdated'
        bks = from_cache(bukey)
        if not bks:
            bks = SuiBook.all().order('-updated').fetch(N)
            to_cache(bukey, bks)
        return bks
    
    @classmethod
    def query_top_recommended(cls,N=10):
        """ top N recommended books. """
        brkey = 'BooksMostRecommended'
        bks = from_cache(brkey)
        if not bks:
            bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).order('-recommends').fetch(N))
            to_cache(brkey,bks)
        return bks
        
    @classmethod
    def query_weekly_hits(cls,N=10):
        """ books with top N most starred in the late 7 days. Memcache this as long as no new books
            db.GqlQuery('select book from SuiDau where date >= today-7 order by visits desc')
        """
        bwkey = 'BookWeeklyHits'
        bks = from_cache(bwkey)
        if not bks:
            dt = datetime.utcnow() - timedelta(days=7)
            daus = SuiDau.all().filter('date >=',dt).order('-visits').fetch(N)
            bids = [d.book for d in daus]
            bks = map(lambda e:str(e.key().id()),SuiBook.get_by_id(bids))
            to_cache(bwkey,bks)
        return bks
        
    @classmethod
    def query_monthly_hits(cls,N=10):
        """ books with top N most starred in the late 30 days.
            db.GqlQuery('select book from SuiDau where date >= today-30 order by visits desc')
        """
        bmkey = 'BookMonthlyHits'
        bks = from_cache(bmkey)
        if not bks:
            dt = datetime.utcnow() - timedelta(days=30)
            daus = SuiDau.all().filter('date >=',dt).order('-visits').fetch(N)
            bids = [d.book for d in daus]
            bks = map(lambda e:str(e.key().id()),SuiBook.get_by_id(bids))
            to_cache(bmkey,bks)
        return bks
        
    @classmethod
    def query_all_hits(cls,N=10):
        """ books of total starred top N.
            select * from SuiBook order by visits desc
        """
        bakey = 'BookHits'
        bks = from_cache(bakey)
        if not bks:
            bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).order('-visits').fetch(N))
            to_cache(bakey,bks)
        return bks
        
    @classmethod
    def query_new_books(cls,N=10):
        """ latest N books.
            select * from SuiBook order by published desc
        """
        bnkey = 'BookNew'
        bks = from_cache(bnkey)
        if not bks:
            bks = map(lambda e:str(e.id()), SuiBook.all(keys_only=True).order('-started').fetch(N))
            to_cache(bnkey,bks)
        return bks
        
    def decache_for_newbook(self):
        """ Clear BookNew, BookByGenre_xxx, BookByAuthor_xxx for this book. """
        ks = ['BookNew','%s'%self.key().id()] + ['BookByAuthor_%s'%s for s in self.authors] + ['BookByGenre_%s'%s for s in (self.genre or [])]
        decaches(ks)
        
    def recache_updates(self):
        """ Clear BooksUpdated and this """
        ks = ['BooksUpdated', '%s'%self.key().id()]
        decaches(ks)
        
    def decache_all(self):
        ks = ['BookNew','BooksUpdated','BookByTitle','BookHits','PromotedBook','BooksMostRecommended',str(self.key().id())]
        ks.extend(['BookByAuthor_%s'%a for a in self.authors])
        ks.extend(['BookByGenre_%s'%g for g in self.genre])
        decaches(ks)
        
    @classmethod
    def get_promoted(cls):
        pg = from_cache('PromotedBook')
        if pg is None:
            pg = '36001'    #use this at the moment, add memcache from admin
            to_cache('PromotedBook',pg,24*3600) #new book every day
            return pg
            allgms = SuiBook.all(keys_only=True).fetch(1000)
            if allgms:
                n = len(allgms)
                if n < 1:
                    return '';
                x = random.randint(0,n-1)
                pg = str(allgms[x].id())
                to_cache('PromotedBook',pg,24*3600) #new book every day
        return pg

class SuiZine(db.Model):
    """ Periodicals, is this necessary? All comic books are periodicals and pages can just be added on and on.
        Use of SuiZine can separate a periodical into separate books which are smaller.
    """
    title = db.StringProperty(indexed=False)
    owner = db.StringProperty() #Author.key_name
    startime = db.DateTimeProperty(auto_now_add=True)
    issues = db.TextProperty()  #[{id:book_id,title:'',date:''},..]
    authors = db.StringListProperty() #[uid,uid,..]
    period = db.StringProperty(indexed=False)   #monthly,bimonthly,free
    note = db.TextProperty()
    
    @classmethod
    def load_by_author(cls,aid):
        return SuiZine.all().filter('authors =',aid).fetch(100)
    
class SuiPage(db.Model):
    """ A page in the book, to be used for editing only. Once saved, all pages will be packed and saved in SuiBook.pages property.
    """
    book = db.IntegerProperty() #which book
    author = db.StringProperty(indexed=False)   #None if same as SuiBook, else author of this page usually an artist
    script = db.TextProperty()    #word baloons, dialogs, {"version":"1.0","controls":[{"type":..}..} see script spec.
    layers = db.TextProperty()  #layers [{layer:0,dim:[x,y,w,h],var1:0,transform:'',effect:''},..]
    requires = db.TextProperty()   #{'ticket':1,'item':1,..}
    rewards = db.TextProperty() #{'item_id':{'item-1':2,'item_2':1,..},..}
    notes = db.TextProperty()   #authors take notes or comments about this page, can be original script text
    version = db.IntegerProperty(default=0,indexed=False)   #increment upon every modification, img link ?v=0
    #serial = db.FloatProperty() #not used any more,for sorting purpose (inserting, deleting pages, etc)
    
    @classmethod
    def query_by_book(cls,book):
        """ Query all pages of a book. NOTE: this method calls the SuiBook.load_pages()
            Assume that comic pages are not too big, for example, a 500 pages book will use 500K far less than 1MB limit in memcache.
            The pages collection will be attached to the book entity to save a separate memcache API call.
            Limitation: a book should not have more than 1000 pages.
            @param book : SuiBook entity, key or id.
        """
        if not isinstance(book, SuiBook):
            book = SuiBook.seek_by_id(book)
            if not book:
                return []
        return book.load_pages()
#        if hasattr(book, '_pages_list'):
#            return book._pages_list
#        pgs = SuiPage.all().filter('book =',book.key().id()).fetch(1000)
#        book._pages_list = pgs
#        book.recache()
#        return pgs
    
    def get_requires(self):
        if not hasattr(self,'_requires_dict'):
            self._requires_dict = dict((d[0],int(d[1])) for d in INV_PTN.findall(self.requires or ''))
        return self._requires_dict
    
    def put_requires(self,dic=None):
        if dic is None:
            if not hasattr(self,'_requires_dict'):
                logging.error('put_requires, _requires_dict not set')
                raise Exception('_requires_dict not found')
            dic = self._requires_dict
        self.requires = '{%s}'%','.join(['"%s":%d'%(k,v) for k,v in dic.items()])
        
    def get_rewards(self):
        if not hasattr(self,'_rewards_dict'):
            RW_PTN = compile(r'"(\w+)":\{([^}]*)\}')
            self._rewards_dict = dict((k,dict((i,int(d)) for i,d in INV_PTN.findall(cs))) for k,cs in RW_PTN.findall(self.rewards or ''))
        return self._rewards_dict
    
    def put_rewards(self,dic=None):
        if dic is None:
            if not hasattr(self,'_rewards_dict'):
                raise Exception('put_rewards, _rewards_dict not set')
            dic = self._rewards_dict
        self.rewards = '{%s}'%','.join(['"%s":%s'%(k,'{%s}'%','.join(['"%s":%d'%(i,d) for i,d in v.items()])) for k,v in dic.items()])
        
    def save_page(self,bk=None):
        """ save this page to store and update book page entity list """
        self.put()
        if not bk:
            bk = SuiBook.seek_by_id(self.book)
        bk.update_page_entity(self.key().id(),self)
        
    def add_requires(self,vgid,save=True):
        if not vgid:raise Exception('Null vgoods')
        reqs = self.get_requires()
        if len(reqs) > 2:
            return False
        reqs[vgid]=1
        self.put_requires(reqs)
        if save: self.save_page()
        return True
        
    def del_requires(self,vgid,save=True):
        if not vgid:raise Exception('Null vgoods')
        reqs = self.get_requires()
        if vgid in reqs:
            del reqs[vgid]
            self.put_requires(reqs)
            if save: self.save_page()
            
    def add_reward(self,vgid,save=True):
        if not vgid:raise Exception('Null vgoods')
        rws = self.get_rewards()
        rws[vgid]={}
        self.put_rewards(rws)
        if save: self.save_page()
        
    def del_reward(self,vgid,save=True):
        if not vgid:raise Exception('Null vgoods')
        rws = self.get_rewards()
        logging.info('vgid=%s,rws=%s'%(vgid,rws))
        if vgid in rws:
            del rws[vgid]
            self.put_rewards(rws)
            if save: self.save_page()
        
class SuiGenre(db.Model):
    """ Genre and number of books. Added when new book is created or genre is changed. """
    genre = db.StringProperty()
    books = db.StringListProperty(indexed=False)  #book IDs
    
    @classmethod
    def init_data(cls):
        gs=['Fantasy','Historical','Humour','Kung-Fu','Mystery','Romance','Sci-Fi','Spy','Superhero','Thriller','War','Adventure','Educational','Crime','Drama','School','Sports','Games','Political']
        gs.sort()
        ges = [SuiGenre(key_name=s,genre=s) for s in gs]
        db.put(ges)
        
    @classmethod
    def query(cls):
        genres = from_cache('Genres')
        if not genres:
            genres = SuiGenre.all().fetch(100)
            to_cache('Genres',genres)
        return genres
    
    @classmethod
    def clear_cache(cls):
        decache('Genres')
        
    @classmethod
    def add(cls,genre,book):
        if not genre:
            logging.error('SuiGenre.add(None)')
            return
        if genre.find(',')>0:
            genres = genre.split(',')
        else:
            genres = [genre]
        dbs = []
        for gr in genres:
            g = SuiGenre.get_by_key_name(gr)
            if g:
                g.books.append(book)
            else:
                g = SuiGenre(key_name=gr,genre=gr,books=[book])
            dbs.append(g)
        if dbs:
            db.put(dbs)
            decache('Genres')

    @classmethod
    def remove(cls,genre,book):
        genres = genre.split(',')
        if genres:
            dbs = []
            gs = SuiGenre.get_by_key_name(genres)
            for g in gs:
                if g.books and book in g.books:
                    g.books.remove(book)
                    dbs.append(g)
            if dbs:
                db.put(dbs)
                decache('Genres')
            
    @classmethod
    def recalc(cls):
        bks = SuiBook.all().fetch(1000)
        grs = {}
        for bk in bks:
          k = bk.key().id()
          g = bk.genre
          if g in grs:
            grs[g].append(k)
          else:
            grs[g] = [k]
        for g,bks in grs.items():
          gen = SuiGenre(genre=g,books=bks)
          gen.put()

class SuiGoods(db.Model):
    """ Items on sale in the market, placed by book authors """
    name = db.StringProperty(indexed=False)
    type = db.StringProperty(indexed=False) #ticket,tool,BDG,etc
    book = db.StringProperty()  #in which book(id) it is used
    author = db.StringProperty()    #first author of the book, for quick query by author
    price = db.FloatProperty(indexed=False)
    display = db.BooleanProperty(default=True,indexed=False)
    note = db.TextProperty()
    issued = db.DateTimeProperty(auto_now_add=True)
    version = db.IntegerProperty(default=0,indexed=False)   #increment upon every modification
    likes = db.IntegerProperty(default=0)   #including buys and tried buys
    gallery = db.BooleanProperty(default=False,indexed=False)   #if True, it has a big image to show in gallery
    giftable = db.BooleanProperty(default=False,indexed=False)  #if True, it can be sent to others as gift
    returnable = db.BooleanProperty(default=False,indexed=False)  #
    
    def is_used(self):
        return not self.giftable and not self.returnable
    
    def set_used(self,save=True):
        self.giftable = False
        self.returnable = False
        if save: self.save()
        
    @classmethod
    def load_by_ids(cls,ids):
        """ Load a list of SuiGoods from memcache or datastore.
            Technically, it tries all IDs from memcache, and load those not in memcache from datastore and fill memcache with them.
            @ids - ['144','245',..] a list of SuiGoods.key().id() numbers as strings
            @return merged results as [ SuiGoods,..]
        """
        es = from_caches(ids)  #some are loaded from memcache, others are ignored.
        notfounds = filter(lambda e:e not in es, ids)
        if len(notfounds)>0:
            es2 = dict((str(e.key().id()),e) for e in SuiGoods.get_by_id(map(lambda e:int(e),notfounds)))
            to_caches(es2)
            es.update(es2)
        return es
    @classmethod
    def load_one(cls,id):
        gd = from_cache('%s'%id)
        if not gd:
            gd = SuiGoods.get_by_id(int(id))
            if gd:
                to_cache('%s'%id, gd)
        return gd
    @classmethod
    def query_by_book(cls,bid,loade=True):
        """ Load all items for a book. Query memcache for a list of IDs first, load from datastore if not.
            Then push the list of IDs onto memcache and return list of entities by calling load_by_ids.
        """ 
        gds = from_cache('VG_%s'%bid)
        if not gds:
            gds = [str(g.id()) for g in SuiGoods.all(keys_only=True).filter('book =',bid).fetch(1000)]
            to_cache('VG_%s'%bid, gds)
        if loade:
            return SuiGoods.load_by_ids(gds)
        return gds
    
    @classmethod
    def query_by_author(cls,aid):
        """ Load all items for an author. Query memcache for a list of IDs only first, if not there, query datastore.
            And then cache these IDs in a list by key name 'VG_uid', and return list of entities via load_by_ids.
        """
        gds = from_cache('VG_%s'%aid)
        if not gds:
            gds = [str(g.id()) for g in SuiGoods.all(keys_only=True).filter('author =',aid).fetch(1000)]
            to_cache('VG_%s'%aid, gds)
        return SuiGoods.load_by_ids(gds)
    
    @classmethod
    def query_top_buys(cls,N=20):
        """ Query top N (20 by default) best buys and changes daily.
            The query result is a list of IDs as strings in a list, and then call load_by_ids to get entities.
            The IDs are saved in memcache for 24 hours.
            @param N: number of entities to query, default 20
            @return: [SuiGoods,SuiGoods,..] a list of SuiGoods entities obtained by calling load_by_ids 
        """
        # NOTE: this is not used currently
        gds = from_cache('VG_TOP_%d'%N)
        if not gds:
            gds = [str(g.id()) for g in SuiGoods.all(keys_only=True).order('-likes').fetch(N)]
            to_cache('VG_TOP_%d'%N,gds,3600*24)
        return SuiGoods.load_by_ids(gds)
    
    @classmethod
    def clearcache(cls,ids):
        if isinstance(ids, basestring):
            decache('VG_%s'%ids)
        elif isinstance(ids, list):
            ks = ['VG_%s'%id for id in ids]
            decaches(ks)
        
    def recache(self):
        to_cache('%s'%self.key().id(),self)
        
    def save(self):
        self.put()
        self.recache()

class SuiGift(db.Model):
    """ Gift system for readers asking and giving each other required vgs in the books.
        This is used to keep who asked what and who replied.
        key_name = uid_vgid
    """
    gift = db.IntegerProperty() #SuiGoods.key().id()
    demander = db.StringProperty()  #SuiUser.key().name()
    doners = db.TextProperty()  #who gives {'uid':1,'uid':1,...}
    
class SuiReview(db.Model):
    """ Book reviews and comments. 
        A book can have 100 reviews, and each review have 100 comments.
        A review can have 2000 characters, and a comment 200 characters.
        TODO: remove this kind and use SuiPost in SuiForum.Book Reviews
    """
    book = db.IntegerProperty()
    review = db.TextProperty()
    author = db.StringProperty(indexed=False)   #reviewer
    comments = db.StringListProperty(indexed=False) #comments: [commenter:name@time]comment_text
    
class SuiDau(db.Model):
    """ Statistics about daily actives. """
    date = db.DateTimeProperty(auto_now_add=True)   #index 1
    action = db.StringProperty()    #index 2, register,login,open,buy
    object = db.StringProperty()    #book_id, item_id as string
    user = db.StringProperty()  #user_key_name
    quantity = db.IntegerProperty(indexed=False) #only if object is item

    @classmethod
    def add(cls,usr,act,par=None,qty=None):
        if isinstance(usr, SuiUser):
            usr = usr.key().name()
        d = SuiDau(action=act,user=usr)
        if par: d.object = par
        if qty: d.quantity = int(qty)
        d.put()

    @classmethod
    def count(cls,action='login',days=1,param=None):
        """ Count number of records during last days for action.
            default arguments for daily logins DAU for the last 24 hours.
            monthly registed: action='register',days=30.
            monthly users read a book: action='open',days=30,param=book_id.
            Note that Query.count() returns all matches and may cause timeout if too many.
        """
        dt = datetime.utcnow() - timedelta(days=days)
        q = SuiDau.all(keys_only=True).filter('action =',action).filter('date >=',dt)
        if param: q.filter('object =',param)
        return q.count()
        
class MediaStore(db.Model):
    """ pictures, flash swf etc. """
    book = db.StringProperty()  # SuiBook.id
    page = db.IntegerProperty(indexed=False)    #which page, None for whole book
    usage = db.StringProperty(indexed=False) #what type of use case such as logo
    format = db.StringProperty(indexed=False) #PNG,GIF,JPEG,etc
    width = db.IntegerProperty(indexed=False)
    height = db.IntegerProperty(indexed=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    stream = db.BlobProperty()
    
    @classmethod
    def load_by_key(cls,keyname):
        """ Load MediaStore by key_name. """
        cachekey = 'MM_%s' % keyname
        m = from_cache(cachekey)
        if not m:
            m = MediaStore.get_by_key_name(keyname)
            if m:
                to_cache(cachekey, m)   #one week
        return m
    
    def decache(self):
        decache('MM_%s'%self.key().name())

class SuiLog(db.Model):
    """ Logs important activities of users for admin purpose. These activities include:
        A user read a page, bought, redeemed, sold, sent, or returned a virtual goods;
    """
    user = db.StringProperty()  # SuiUser.key_name, searchable
    action = db.StringProperty(indexed=False)   #what is done, define some syntax for actions and parameters
    donetime = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def log_read(cls,usr,bkid,pgseq):
        taskqueue.add(url='/task/log',params={'usr':usr.key().name(),'act':'read %s %s'%(bkid,pgseq),'dt':str(datetime.utcnow())})
        
    @classmethod
    def log_newbook(cls,usr,bkid):
        taskqueue.add(url='/task/log',params={'usr':usr.key().name(),'act':'new book %s'%bkid,'dt':str(datetime.utcnow())})
        
class SuiTransaction(db.Model):
    """ Redeem or consume Transaction of goods by users, to be used to pay the creators.
        For donations, goods refer to SuiPage ID instead of SuiGoods ID. The difference is amount will be zero for donations.
    """
    user = db.StringProperty()
    xtime = db.DateTimeProperty(auto_now_add=True)
    book = db.StringProperty()
    goods = db.StringProperty()
    amount = db.IntegerProperty(default=1,indexed=False)  #how many pieces
    points = db.IntegerProperty(indexed=False)   #how much actually paid, price may vary from time to time
    
    @classmethod
    def count(cls,itm,period='month'):
        """ Count the number of transactions/buys of an item for the latest period such as a week, month or year. 
            This may be an expensive operation, and should be replaced with a counter somewhere or cached.
        """
        today = datetime.utcnow()
        if period == 'month':
            fromdate = today - timedelta(days=30)
        elif period == 'week':
            fromdate = today - timedelta(days=7)
        elif period == 'year':
            fromdate = today - timedelta(days=365)
        else:
            fromdate = today - timedelta(days=30)
        txn = SuiTransaction.all(keys_only=True).filter('goods =',itm).filter('xtime >',fromdate).fetch(1000)
        return len(txn)
        
class SuiExchange(db.Model):
    """ Users exchange Facebook credits or other currency for Su points.
    """
    user = db.StringProperty()    #buyer
    xtime = db.DateTimeProperty(auto_now_add=True)  #utc when this record saved or timestamp from payment server
    points = db.IntegerProperty(indexed=False) #=quantity
    method = db.StringProperty(indexed=False)   #FC,PayPal,GoogleCheckout, etc.
    price = db.FloatProperty(indexed=False)   #unit-price
    quantity = db.IntegerProperty(indexed=False)    #how many
    orderef = db.StringProperty()   #order reference number
    currency = db.StringProperty()  #GBP,USD,FC, or other real or virtual currency
    fee = db.FloatProperty()    #total transaction cost, Google Checkout fee is 3.4% + 0.2 (<1500)
    package = db.StringProperty() #which package selected, packages change, but good for marketing decision
    buyerid = db.StringProperty(indexed=False) #buyer id from payment side, can be email

class SuiNews(db.Model):
    """ Records dynamic news etc.
        News can be used to store some system variables such as company announcement, etc.
    """
    headline = db.StringProperty(indexed=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    body = db.TextProperty()
    
class SuiForum(db.Model):
    """ Forums.
        Predefined forums: 
            General Discussion, Frequently Asked Questions, Rules and Policies
            News and Announcements, Feedback and Suggestions, Bug Reports
            Book Reviews, Artists Corner, Writers Corner
    """
    forum = db.StringProperty(indexed=False)    #display name of this forum
    note = db.TextProperty()    #what this forum is about
    posts = db.IntegerProperty(default=0,indexed=False) #number of posts in this forum
    group = db.IntegerProperty(default=0,indexed=False) #forums group together, different groups are separated by a line
    order = db.IntegerProperty(default=0)   #which is first, which is second in a group
    parentForum = db.IntegerProperty()   #parent forum if available, None for root
    moderators = db.StringListProperty(indexed=False)   #a list of moderators uid:name
    
    @classmethod
    def load_all(cls):
        forums = from_cache('SuiForums')
        if not forums:
            forums = SuiForum.all().fetch(100)
            to_cache('SuiForums', forums)
        return forums
    
    @classmethod
    def init_data(cls):
        """ called by admin only """
        data=[{'forum':'General Discussion','group':0,'order':0,'note':''},
              {'forum':'Frequently Asked Questions','group':0,'order':1,'note':''},
              {'forum':'Rules and Policies','group':0,'order':2,'note':''},
              {'forum':'News and Announcements','group':1,'order':10,'note':''},
              {'forum':'Feedback and Suggestions','group':1,'order':11,'note':'Suggest ideas of improvement and new features'},
              {'forum':'Bug Reports','group':1,'order':12,'note':'Report problems of the web services'},
              {'forum':'Book Reviews','group':2,'order':20,'note':''},
              {'forum':'Artists Corner','group':2,'order':21,'note':'Discuss topics about art and artists'},
              {'forum':'Writers Corner','group':2,'order':22,'note':'Discuss topics about stories and writers'}
              ]
        for d in data:
            f = SuiForum(forum=d['forum'],note=d['note'],group=d['group'],order=d['order'])
            f.put()
    
class SuiPost(db.Model):
    """ Forum post. 
    """
    forum = db.IntegerProperty()    #SuiForm.key().id()
    subject = db.StringProperty(indexed=False)
    postime = db.DateTimeProperty(auto_now_add=True)    #order
    author = db.StringProperty(indexed=False)   #uid:name
    
    @classmethod
    def load_by_forum(cls,fid):
        """ Return first 200 posts of a forum. TODO: use cursor to get pagination later.
        """
        pst = from_cache('SuiPost_%s'%fid)
        if not pst:
            pst = SuiPost.all().filter('forum =',int(fid)).order('-postime').fetch(200)
            to_cache('SuiPost_%s'%fid, pst, 1800)
        return pst
    @classmethod
    def decache_by_forum(cls,fid):
        decache('SuiPost_%s'%fid)
        
class SuiContent(Expando):
    """ Forum post content and comments.
    """
    post = db.IntegerProperty() #SuiPost.key().id()
    author = db.StringProperty(indexed=False)   #=SuiPost.author
    content = db.TextProperty() #post body
    comments = db.IntegerProperty(default=0,indexed=False)  #number of comments
    #comment0 .. commentN    #uid:name@time.text
    
class SuiBirthdayUser(db.Model):
    """ Birthday Agent users
    """
    name = db.StringProperty(indexed=False)
    creator = db.BooleanProperty(default=False,indexed=False)
    started = db.DateTimeProperty(auto_now_add=True,indexed=False)
    updated = db.DateTimeProperty(indexed=False)
    excludes = db.TextProperty()    #[uid,uid,..]
    choices = db.TextProperty() #gift ids to use
    access_token = db.StringProperty(indexed=False)
    birthdays = db.TextProperty() #{'mm-dd':[M|Fuid,uid,..],'mm-dd:[uid,uid,..]}
    usemyown = db.BooleanProperty(default=False,indexed=False)
    mygifts = db.TextProperty() #[gid,gid,..]
    mywrapper = db.StringProperty(indexed=False)
    included = db.IntegerProperty(default=0,indexed=False)
    useframe = db.StringProperty(indexed=False) #what frame to use or no frame
    
    def get_birthdays(self):
        ptn = compile(r'"(\d\d-\d\d)":\[([MF\d,]+)\]')
        return dict((k,us) for k,us in ptn.findall(self.birthdays or ''))
    def put_birthdays(self,bds,save=False):
        self.birthdays = '{%s}'%','.join(['"%s":[%s]'%(k,us) for k,us in bds.items()])
        if save:
            self.put()
    def get_excludes(self):
        ptn = compile(r'(\d+)')
        return ptn.findall(self.excludes or '')
    def get_mygifts(self):
        ptn = compile(r'"(\w+)"')
        return ptn.findall(self.mygifts or '')
    def put_mygifts(self,mgifts):
        self.mygifts = '[%s]'%','.join(['"%s"'%d for d in mgifts])
    def add_mygift(self,gid):
        mygifts = self.get_mygifts()
        if gid not in mygifts:
            mygifts.append(gid)
            self.put_mygifts(mygifts)
    def del_mygift(self,gid):
        mygifts = self.get_mygifts()
        if gid in mygifts:
            mygifts.remove(gid)
            self.put_mygifts(mygifts)

class SuiBirthdayGift(db.Model):
    """ Birthday gifts. all public and free.
    """
    name = db.StringProperty(indexed=False)
    creator = db.StringProperty()   #submitter
    category = db.StringProperty(default='M',indexed=False)
    gender = db.StringProperty(default='B',indexed=False)
    created = db.DateTimeProperty(auto_now_add=True,indexed=False)
    
def pack_entity(e,excludes=None):
    """ Pack properties in an entity into a dict.
        For TextProperty that contains {} or [], return it as dict or list.
        Fields in excludes are ignored.
    """
    if not e or not hasattr(e,'properties'):
        logging.warning('models.pack_entity(%s), bad entity'%e)
        return {}
    rs = {'id':'%s'%e.key().id_or_name()}
    for pname,ptype in e.properties().items():
        if pname not in excludes:
            pvalue = getattr(e,pname)
            if pvalue is None:
                rs[pname] = ''
            elif isinstance(ptype,db.BooleanProperty):
                rs[pname] = str(pvalue).lower()
            elif isinstance(ptype,db.DateTimeProperty):
                rs[pname] = '%s'%datetime.strftime(pvalue,'%Y-%m-%d %H:%M:%S')
            elif isinstance(ptype,db.TextProperty):
                if pvalue.startswith('{') or pvalue.startswith('['):
                    rs[pname] = eval(pvalue)
                else:
                    rs[pname] = pvalue
            else:
                rs[pname] = pvalue
    return rs
