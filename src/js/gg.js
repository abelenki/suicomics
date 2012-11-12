/**
 * TODO: OpenSocial interface.
 * Get friends and return [{id:person.id,name:person.displayname},..]
 */
function get_friends(uid, callback){
    if(typeof(opensocial)=='undefined') return;
    var req = opensocial.newDateRequest();
    req.add(req.newFetchPersonRequest(opensocial.IdSpec.PersonId.VIEWER),'viewer');
    var viewerFriends = opensocial.newIdSpec({"userId":"VIEWER","groupId":"FRIENDS"});
    var opt_params = {};
    opt_params[opensocial.DataRequest.PeopleRequestFields.MAX] = 100;
    req.add(req.newFetchPeopleRequest(viewerFriends,opt_params),'viewerFriends');
    req.send(function(data){
        var viewer = data.get('viewer').getData();
        var viewerFriends = data.get('viewerFriends').getData();
        var r = [];
        viewerFriends.each(function(person){
            r.push({id:person.getId(),name:person.getDisplayName(),thumbnail:person.getThumbnailUrl()});
        });
        if(callback)
            callback(r);
    });
}
function profile_pic_url(uid,size){
	if(uid.indexOf('fb_')==0)
		uid = uid.substr(3);
	if(uid.indexOf('gg_')==0) uid='1842536962';
	var type='square';
	if(size && (size=='large')) type='large';
	return 'http://graph.facebook.com/'+uid+'/picture?type='+type;
}
function load_profile(uid,cb){
	if(uid.indexOf('gg_')==0)uid='1842536962';
	if(uid.indexOf('fb_')==0)uid = uid.substr(3);
	if(cb)cb({name:uid,picture:'http://graph.facebook.com/'+uid+'/picture'});
}
function placeOrder(){
	var id = $("input[@name='pkg']:checked").attr('id');
	var pkg = Main.menus.market.getPackage(id);
	if(pkg!=null){
		if(console)console.log(pkg);
		return;
	}return;
	var credits = pkg[0];
	var sudos = pkg[1];
    var order_info = {title:sudos+'Sudos package',description:'Buy '+sudos+' Sudos for '+credits+' Facebook Credits',price:credits,image_url:'http://suicomics.appspot.com/img/sb20.png',product_url:'http://suicomics.appspot.com/img/sb20.png'};
    var obj = {method:'pay',order_info:order_info,purchase_type:'item'};
    alert('not implemented here')
//    FB.ui(obj,function(resp){
//        if (resp['order_id']) return true;else {alert(resp.error_message);return false;}
//    });
}