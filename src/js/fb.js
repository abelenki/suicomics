/**
 * Facebook Graph API routines
 */
/**
 * Login to FB.
 */
function login(){
    FB.login(function(response){
        if (response.session) {
            if (response.perms) {
                //logged in and granted some permissions.
                if(console)console.log('FB.login callback, logged in:',response);
            } else {
                //logged in, but not grant any permissions
                if(console)console.log('FB.login callback, logged in but no permission:',response);
            }
        } else {
            //not logged in
            if(console)console.log('FB.login callback, not logged in');
        }
    }, {perms:'email,publish_stream,offline_access'});
}
function loginui(){
    FB.ui({'method':'auth.login'},function(response){
        if (response.session){
            if (response.perms){
                if(console)console.log('loginui callback, logged in with permission',response);
            } else {
                if(console)console.log('loginui callback, logged in but no permission',response);
            }
        } else {
            if(console)console.log('FB.ui auth.login callback, not logged in')
        }
    }, {perms:'email,publish_stream,offline_access'});
}
/**
 * Get friends
 * @param scope: 1 = users, 2 = non users, 3 = all
 * App users: select uid,name from user where is_app_user=1 and uid in (select uid2 from friend where uid1=UID)
 */
function get_friends(scope, callback){
    if(scope == 3){
    var url='/me/friends';
    if(console)console.log('getting ',url);
    FB.api(url, function(resp){
        if(console)console.log(resp);
        if (callback) {
            dataset = [];
            if(resp.data){
            for(var i=0,d; d = resp.data[i]; i++){
                dataset.push({id:d.id,name:d.name,pic:'http://graph.facebook.com/'+d.id+'/picture'});
            }
            callback(dataset);
            }else{
                _alert('Cannot get friend list');
            }
        }
    });
    } else {
        //if(console)console.log('getting /me');
        FB.api('/me',function(resp){
            var uid = resp.id;
            var a = scope & 1;
            var q='select uid,name from user where is_app_user='+a+' and uid in (select uid2 from friend where uid1={0})';
//            if(console)console.log('then, getting friends by query ',q);
            var query = FB.Data.query(q, uid);
            query.wait(function(rows){
                if(console)console.log(rows);
                var dataset = [];
                for(var i=0,f;f=rows[i];i++){
                    dataset.push({id:'fb_'+f.uid,name:f.name,pic:'http://graph.facebook.com/'+f.uid+'/picture'});
                }
                callback(dataset);
            });
        });
    }
}
function invite_friends_old(){
	//get appUsers first for exclusion
	FB.api('/me',function(resp){
		FB.Data.query('select uid from user where is_app_user=1 and uid in (select uid2 from friend where uid1={0})',resp.id).wait(function(rows){
			var usrs=[];
			for(var i=0,r;r=rows[i];i++)usrs.push(r.uid);
			do_invite(usrs);
		});
	});
}
function do_invite_old(excludes){
	//if(console)console.log('do_invite, ex=',excludes);
	var fbmls='<fb:fbml><fb:request-form action="http://apps.facebook.com/suicomics/" '+
	'method="POST" invite="true" target="_top" type="Invitation to Suinova Comics" '+
	'content="Suinova Comics is a portal of comics and graphic novels with game mechanics. Join me to read, collect and share!"'+
	'<fb:req-choice url="http://apps.facebook.com/suicomics/" label="Accept"/> >'+
	'<fb:multi-friend-selector condensed="true" email_invite="false" import_external_friends="false" bypass="cancel" showborder="true" actiontext="Select your friends to invite" exclude_ids="'+excludes.join(',')+
	'"/><fb:request-form-submit import_external_friends="false" label="Send Invitation"/></fb:request-form></fb:fbml>';
	FB.ui({method:'fbml.dialog',fbml:fbmls,width:'640px',height:'320px'},function(resp){
		if(console)console.log(resp);
	});
}
function do_invite(filter){
	FB.ui({ method: 'apprequests', message: 'Suinova Comics is good, join me to read, collect and share!', filters: filter});
}
function invite_friends(){
	do_invite(['app_non_users']);
}
/**
 * Post to a user's feed.
 * post_feed('me',{'link':'http:','name':'name'},function(resp){});
 */
function post_message(uid,params,callback){
    if(typeof(uid)=='undefined' || uid==null) uid = 'me';
    //if(console)console.log(params);
    FB.api('/'+uid+'/feed','post',params,function(resp){
        if(callback) callback(resp);
    });
}
function post_message_ui(params,prompt,callback){
	//params['method']='feed';
	//FB.ui(params,callback);
    FB.ui({
     method: 'stream.publish',
     message: params.message,
     attachment: {
       name: params.name,
       href: params.link,
       caption: params.caption,
       description: params.description,
       media:[{ type: 'image',href: params.link,src: params.picture }]
     },
     action_links: [{ text: params.actions.name, href: params.actions.link }],
     user_message_prompt: prompt
     },
     function(response) {
     //if (response && response.post_id) {alert('Post was published.');} else {alert('Post was not published.');}
    });
}
function read_book(bkid,bktitle,bkintro){
	var params={
			message:'started reading a new book.',
			picture:'http://suicomics.appspot.com/mm/bk_'+bkid+'.jpg',
			link:'http://apps.facebook.com/suicomics/book/'+bkid,
			name:bktitle,caption:'',
			description:bkintro,
			actions:{"name": "Read", "link": "http://apps.facebook.com/suicomics/book/"+bkid}
			};
	//if(console)console.log(params);
	//post_message('me',params);
	post_message_ui(params,'Tell your friends about your reading:');
}

/* Facebook utility functions */
function stream_publish(op,msg){
	if(op=='levelup'){
		FB.ui({method: 'stream.publish', message: msg}, function(response) {});
	} else if (op=='demand'){
		FB.ui({method:'stream.publish',message:msg},function(rs){});
	} else {
		if(window.console)console.log('Error: stream_publish op=',op);else alert('stream_publish invalid op='+op);
	}
}
//function add_bookmark(){
//    FB.ui({ method: 'bookmark.add' });
//}
function share_me(){
    FB.ui({method:'stream.share',display:'popup',u:'http://apps.facebook.com/suinova'},function(response){});
}
//function invite_friends(){
//	window.location.href='http://suinova-games.appspot.com/invite';
//}
function profile_pic_url(uid,size){
	if(uid.indexOf('fb_')==0)
		uid = uid.substr(3);
	var type='square';
	if(size && (size=='large')) type='large';
	return 'http://graph.facebook.com/'+uid+'/picture?type='+type;
}
function load_profile(uid,cb){
	if(uid.indexOf('fb_')==0)uid=uid.substr(3);//if(window.console)console.log('load_profile, uid=',uid);
	FB.api('/'+uid+'?fields=name,picture',function(resp){
		//if(console)console.log('loaded for ',uid,'data:',resp);
		if(cb) cb(resp);
	});
}
//select 5 friends for gallery credits to send as requests
function send_free_credits(){
	var fbmls='<fb:fbml><fb:request-form action="http://apps.facebook.com/suicomics/gallery/credits/sent" '+
		'method="POST" invite="false" type="SuiComics: Free Gallery Credit" '+
		'content="I put a credit for you in my gallery, come and pick it up. Thanks!"'+
		'<fb:req-choice url="http://apps.facebook.com/suicomics/gallery/credits/pick?g='+myinfo.uid+'" label="Get It"/> >'+
		'<fb:multi-friend-selector condensed="true" max="5" email_invite="false" import_external_friends="false" bypass="cancel" showborder="true" actiontext="Select 5 friends to send your free gallery credits to" />'+
		'<fb:request-form-submit import_external_friends="false" label="Send Gallery Credit"/></fb:request-form></fb:fbml>';
	FB.ui({method:'fbml.dialog',fbml:fbmls,width:'640px',height:'320px'},function(resp){
		if(console)console.log(resp);
	});
}
function placeOrder(){
	var id = $("input[@name='pkg']:checked").attr('id');
	var pkg = Main.menus.market.getPackage(id);
	if(pkg!=null){
		if(console)console.log(pkg);
		var credits = pkg[1];
		var sudos = pkg[1];
	    var order_info = {
	    		item_id:'sup'+id.substr(2),
	    		title:sudos+' Sudos Package',
	    		description:'Buy '+sudos+' Sudos for '+credits+' Facebook Credits',
	    		price:credits,
	    		image_url:'http://suicomics.appspot.com/img/sb20.png',
	    		product_url:'http://suicomics.appspot.com/img/sb20.png'};
	    var obj = {method:'pay',order_info:order_info,purchase_type:'item'};
	    FB.ui(obj,function(resp){
	        if (resp['order_id']) {window.top.location='http://apps.facebook.com/suicomics/';}else {alert(resp.error_message);return false;}
	    });
	}
}

