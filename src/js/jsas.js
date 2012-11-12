/**
 * AS3 external interface routines
 */
var gFlashObject = null;
function setFlashObject(app) {
	gFlashObject = document.getElementById(app);
	//if(console)console.log('Set flash object to ',app, gFlashObject);
}
/**
 * This function will be called by AS3 via ExternalInterface.
 * e.g.: ExternalInterface.call("callFromFlash", "inviteFriend", {"uid":"1234","msg":"Come to play Petigems with me!"});
 * After inviteFriend is done, a callback should be issued to pass any data back to AS3, and that is jsCallFlash:
 *  ExternalInterface.addCallback("jsCallFlash", this, onJsCallFlash);
 *  function onJsCallFlash(mthd: String, parms: Object): void {}
 */
function callFromFlash(mthd, parms) {
    if(console)console.log('callFromFlash(',mthd,',',parms,')');
    //if (gFlashObject == null)
    //	gFlashObject = document.getElementById('_readerswf');
    //if(console)console.log('gFlashObject=',gFlashObject);
    if (typeof Suinova[mthd] != 'undefined')
        Suinova[mthd](parms);
    else{
        //if(console)console.log('Undefined method: ',mthd);//
    	alert('Undefined method: '+mthd);
    }
}
/**
 * Function to pass a method with parameters back to Flash object.
 *  ExternalInterface.addCallback("jsCallFlash", this, onJsCallFlash);
 *  function onJsCallFlash(mthd: String, parms: Object): void {}
 */
function callBackFlash(cmd, param){
//    if(console)console.log('callBackFlash(',cmd,',',param,')');
    if (gFlashObject == null)
    	gFlashObject = document.getElementById('_readerswf');
    gFlashObject.jsCallFlash(cmd, param);
}
function ftostr(flst){
    //[{id:'uid',name:'display name',pic:'thumbnail picture url'},...]
    var buf=[];
    for(var i=0,f;f=flst[i];i++){
        buf.push('['+f.id+','+f.name+','+f.pic+']');
    }
    return '['+buf.join(',')+']';
}
/**
 * Suinova namespace to wrap external interface public methods.
 */
var Suinova = {
    _currentBook: 0,
    _currentPage: 0,
    _currentOwner: '',
    setBookPage: function(bkid,pgnum){
		Suinova._currentBook = bkid;
		Suinova._currentPage = pgnum;
	},
	setUser: function(uid){
		Suinova._currentOwner = uid;
	},
    /**
     * Call a SNS-aware routine to send invitation to authors.
     * @param uid - user id with sns prefix
     * @param msg - optional message to send to this friend
     */
    inviteFriends: function (params) {
        var uid=params['uid'], url=params['url'], msg = params['msg'];
        if(uid[2]=='_') uid=uid.substr(3);
        invite_friends(uid, url, msg);
    },
    /**
     * List viewers friends on SNS.
     * @param scope : 1 = app-user, 2=non-app user, 3=all
     * @return [{id:'uid',name:'display name',pic:'thumbnail picture url'},...]
     */
    listFriends: function (scope) {
        //if(console)console.log('listFriends, scope=',scope);
        get_friends(scope, function(flst){
            //if(console)console.log(flst);
            callBackFlash('listFriends',flst);
        });
    },
    /**
     * Market purchase routine.
     * @param params - {'itm':'',qty:n,'request':purchase}
     */
    purchase: function (params) {
        Market.purchase(params.itm, params.qty, function(resp){
        	callBackFlash('purchase',resp);
        });
    },
    /**
     * Market donate routine.
     * @param params - {'pid':page_id, 'pts':points_to_donate}
     */
    donate: function (params) {
    	Market.donate(params.pid, params.pts, function(resp){
    		callBackFlash('donate',resp);
    	});
    },
    /**
     * Get portal environment.
     * @return {cookie:"",host:"",book:n,page:n}
     */
    getenv: function (params) {
            //setTimeout('callBackFlash("getenv",Environment.env)',100);
    	if (params.app) setFlashObject(params.app); 
    	var env={cookie:document.cookie,
    			host:location.protocol+"//"+location.host,
    			//book:Main.menus.page.getBook(),page:Main.menus.page.getPage()
    			book:Suinova._currentBook,
    			page:Suinova._currentPage,
    			user:Suinova._currentOwner
    			};
    	setTimeout(function(){callBackFlash("getenv",env);},200);
    },
    getBook: function() {
        var bkid = Main.menus.page.getBook();
        var lastp = Main.menus.page.getPage();
        setTimeout(function(){callBackFlash("getBook",{book:bkid,page:lastp});},20);    //this will be the first call, so wait for some connection time
    },
    gethost: function() {
        setTimeout(function(){callBackFlash("gethost",location.protocol+"//"+location.host);},200);    //this will be the first call, so wait for some connection time
    },
    newitem: function(param) {
    	//if param is null, called from flash, do nothing here, if param has k then from SuiGallery collect, call flash.
    	if(param.id){
    		callBackFlash("newitem",param);
    	}else {
            if(console)console.log('newitem from Flash, param=',param);
        }
    },
    revoke: function(params) {
    	//revoke an item from flash to add back into SuiGallery.inventory table, params = {'key':key,'id':id}, only one
    	Main.menus.gallery.addItem(params.id);
    },
    collected: function(params) {
    	//from SuiReader, params.vid, .qty
    	myinfo.inv[params.vid] = (myinfo.inv[params.vid] || 0)+params.qty;
    },
    readBook: function(bkid,bk_title,bkintro) {
    	if(read_book)
    		read_book(bkid,bk_title,bkintro); //publish on wall
    	else
    		alert('read_book function not available');
    },
    sendCredits: function(params) {
    	//send one free gallery credit to 5 friends, params empty
    	if(typeof(send_free_credits)!='undefined')
    		send_free_credits();
    	else
    		alert('send_free_credits not available');
    },
    bookNames: function(params) {
    	//params:{ids:[bkid,..]}
//    	if(console)console.log('bookNames:',params);
    	var bkids = params.ids.split(',');
    	var titles={};
    	var reqs=[];
    	for(var i=0,b;b=bkids[i];i++){
    		if(g_books[b])
    			titles[b] = g_books[b].title;
    		else
    			reqs.push(b);
    	}
//    	if(console)console.log('reqs: ',reqs,reqs.length);
    	if(reqs.length<=0)
    		callBackFlash('bookNames',titles);
    	else {
    		var ps=reqs.join(',');
//    		if(console)console.log('call /home/books/ids/',ps);
    		if (ps.length>0)
    		$.post('/home/books/ids/'+ps,function(resp){
    			if(resp.error)alert(resp.error);else{
    				for(var b in resp){
    					g_books[b] = resp[b];
    					titles[b] = resp[b].title;
    				}
    				callBackFlash('bookNames',titles);
    			}
    		},'json');
    	}
    },
    getUserPic: function (uid) {
        //call SNS-routine to get user picture
        var s = "http://graph.facebook.com/"+uid+"/picture?type=square";
        //setTimeout('callBackFlash("sg_PassUserPicUrl","'+s+'")',100);
        callBackFlash('getUserPic',s);
    },
    addnews: function(msg){
        NoticeBoard.add(msg);
    },
    publish: function(params){
    	if(params.msg)params['message']=params.msg;
        post_message(params.uid,params,function(resp){});
    }
};
