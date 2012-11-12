/**
 * Market object
 */
var Market = {
    purchase: function(item, quty, cb) {
//    	if(console)console.log('Market.purchase(',item,',',quty,')');
        $.post('/market/buyitem', {itm:item, qty:quty}, function(resp){
            if (resp.error){
                if (cb) cb(resp); else alert(resp.error);
            } else {
                //{"item":"ibox","pts":290,"quantity":1}
                Viewer.pts = resp.pts;
                $('#mypts').html(resp.pts);
                //alert('Done!');
                //if(console)console.log('Market.purchase returned: ',resp);
                //add item to inventory
                if(typeof myinfo['inv'] == 'undefined')
                	myinfo['inv'] = {};
                var itms = resp.item.split(' ');
                for(var i=0,t; t=itms[i]; i++){
                	if (myinfo.inv[t])
                		myinfo.inv[t] += resp.quantity;
                	else
                		myinfo.inv[t] = resp.quantity;
                }
                Main.menus.gallery.refresh();
                if(cb)cb(resp);
            }
        },'json');
    },
    donate: function(pid_, pts_, cb) {
    	$.post('/market/donate',{pid:pid_,pts:pts_},function(resp){
    		if(resp.error){
    			if(cb)cb(resp);else alert(resp.error);
    		}else{
    			Viewer.pts = resp.pts;
    			$('#mypts').html(resp.pts);
        		if(cb)cb(resp);
    		}
    	},'json');
    }
}

var SuiItemEdit = function(){
    var self=this,_init=null;
    var _div=genAddPanelBox('div_itemedit','middlebox');
    var html='<div><form id="itemform" enctype="multipart/form-data" action="/market/upload" method="post">'+
        '<input type="hidden" id="ie_itemid" name="id"/>'+
        '<table class="tabfull"><caption>Create a new virtual goods item</caption><tbody>'+
        '<tr><td>Item name:</td><td><input type="text" id="ie_name" name="itm" width="40"/></td><td class="note">5 to 16 chars</td></tr>'+
        '<tr><td>Book:</td><td><select id="select_book" name="bkid"></select></td><td class="note"></td></tr>'+
        '<tr><td>Price:</td><td><input type="text" id="ie_price" name="price" width="40"/></td><td class="note">Price for this item</td></tr>'+
        '<tr><td>Display:</td><td><select id="ie_display" name="display"><option value="True">Yes</option><option value="False">No</option></select></td><td class="note">Display in public market or not</td></tr>'+
        '<tr><td>Description:</td><td><textarea id="ie_note" name="note" width="40"></textarea></td><td class="note">What this item is about</td></tr>'+
        '<tr><td>Gallery img:</td><td><input name="imgfile" id="imgfile" type="file"/></td><td><img src="" id="ie_img"/> original item image (png or jpg file)</td></tr>'+
        '<tr><td>Thumbnail:</td><td><input name="logofile" id="logofile" type="file"/></td><td><img id="ie_logo" src=""/> optional thumbnail (50x50) file or resized from original if not given</td></tr>'+
        '<tr><td colspan="3" style="text-align:center"><input name="submit" type="submit" value="Submit" style="width:120px"/></td></tr></table></form></div>';
    //_div.append(html);
    _div.append(genTitledPanel('edit_item','<span class="wsleft">Upload virtual goods</span><button id="Back2Creators" style="float:right">Back</button><div style="clear:both"></div>',html));
    $('#Back2Creators').click(function(){
    	Main.showPage('author');
    });
    self.show=function(){if(_init==null) load();_div.show();}
    self.hide=function(){_div.hide();}
    function load(){
        if(mybooks){
            var buf=[];
            for(var b in mybooks){
                var bk=g_books[b];
                if(bk){
                    buf.push('<option value="'+b+'">'+bk.title+'</option>');
                }
            }
            $('#select_book').html(buf.join(''));
        }
    }
    $('#itemform').submit(function(){
        if($.trim($('#ie_name').val())=='')alert('No item name');else
        if($.trim($('#ie_price').val()).match(/^\d+$/))return true;else {
        	alert('Price "'+$.trim($('#ie_price').val())+'" not proper integer');
        	return false;}
        return false;
    });
    self.setItem=function(itm){
        //[{id,name,type,book,price,display,likes}
        if(itm){
            $('#ie_itemid').val(itm.id);
            $('#ie_name').val(itm.name);
            $('#ie_price').val(itm.price);
            $('#ie_display').val(itm.display);
            $('#ie_note').val(itm.note);
            $('#ie_logo').attr('src','/mm/vg_'+itm.id+'?v='+itm.version);
            $('#ie_img').attr('src','/mm/vgb_'+itm.id+'?v='+itm.version);
        }else{
            $('#ie_itemid').val('');
            $('#ie_name').val('');
            $('#ie_price').val('1');
            $('#ie_display').val('True');
            $('#ie_note').val('');
            $('#ie_logo').attr('src','');
            $('#ie_img').attr('href','');
        }
    }
}

var VGoods = {
	goods: {},
	find: function(vgid){
		return VGoods.goods[vgid] || null;
	},
	name: function(vgid){
		return (VGoods.goods[vgid])?VGoods.goods[vgid].name:'';
	},
	version: function(vgid){
		return (VGoods.goods[vgid])?VGoods.goods[vgid].version:'';
	},
	add: function(lst){
		for(var i=0,g;g=lst[i];i++){
			VGoods.goods[g.id] = g;
		}
	},
	load: function(lst,cb){
		var pms=lst.join(',');
		$.post('/home/goods/ids',{ids:pms},function(resp){
			VGoods.add(resp); //{name,book,note,..}
			if(cb)cb(resp);
		},'json');
	}
}

var SuiMarket = function(){
    var self=this,_bkid=null,_books=null;
    var _pkgs=[[4,60],[8,126],[20,315],[40,630],[100,1575]];

    var html0= '<div id="market_bar"><table><tr><td>Books: <select id="market_select_game"></select></td><td>'+
        '<div id="div_buypts" style="margin-left:10px;display:none"><img src="/img/sb20.png"/> <span id="mypts">0</span> <button id="buypts">Exchange</button></div></td></tr></table></div>';
/*        '<div class="wpanel" id="vgoods"><div class="wtitle">Virtual Goods Store</div><div><table class="tabfull"><caption id="vgoods_caption" style="padding:5px 0">Popular Items</caption>'+
        '<thead><tr><th>Book</th><th>Item</th><th>Price<img title="Sudos" src="/img/sb20.png"/></th><th>Description</th><th>Purchase</th></tr></thead>'+
        '<tbody id="vitemlist"></tbody></table></div>';*/
    var _div = genAddPanelBox('div_market','middlebox');
    _div.append(html0);
    _div.append(genTitledPanel('vitemlist','Virtual Goods Store - <span id="vgoods_caption" style="font-family:Arial"></span>',''));
    if($('#lb1').html().indexOf('Login')<0)$('#div_buypts').show();
    var _pkgsbuf=[];
    for(var i=0,pg;pg=_pkgs[i];i++){
    	var n=i+1;
    	var ss=(i==2)?'checked="checked"':'';
    	_pkgsbuf.push('<tr><td align="right"><input type="radio" name="pkg" id="p_'+n+'" value="sup'+n+'"'+ss+'/></td>');
    	var pres=(myinfo && myinfo.uid && myinfo.uid.indexOf('fb_')==0)? pg[1]+' <img src="http://static.ak.fbcdn.net/rsrc.php/y2/r/XzPDvuhQmm_.png" width="20"/>' : '&pound;'+pg[0];
    	_pkgsbuf.push('<td align="left"><label for="p_'+n+'">'+pres+' for '+pg[1]+' Sudos <img align="absmiddle" src="/img/sb20.png"/></label></td></tr>');
    }
    self.getPackage=function(pid){
    	if(pid.indexOf('p_')==0)pid=pid.substr(2);
    	var id=parseInt(pid)-1;
    	if(id>=0 && id<_pkgs.length)return _pkgs[id];else return null;
    }
    $('body').append('<div id="supkgs" style="display:none;position:absolute;top:150px;left:250px;width:300px;">'+
'<form id="pkg_form" method="post" action="https://suicomics.appspot.com/pay/buypts" target="_blank">'+
'<input type="hidden" name="pm" id="form_pm" value="GC"/>'+
'<table style="margin:2px auto;"><caption>Select a package:</caption><tbody>'+_pkgsbuf.join('')+
'<tr><td colspan="2" style="text-align:center">'+
'<a id="checkout_fc" onclick="placeOrder();return false;"><img src="http://www.facebook.com/connect/button.php?app_id=179008415461930&feature=payments&type=light_l"></a>'+
'<input type="image" alt="Google Checkout" id="checkout_gc" src="https://checkout.google.com/buttons/checkout.gif?merchant_id=843338220023050&w=160&h=43&style=trans&variant=text&loc=en_US" height="43" width="160"/>'+
'<input type="image" onclick="javascript:document.getElementById(\'form_pm\').value=\'PP\';" alt="PayPal Checkout" src="https://www.paypal.com/en_US/i/btn/btn_xpressCheckout.gif" id="checkout_pp"/>'+
'<div><button id="cancel_checkout">Cancel</button></div></td>'+
'</tr></tbody></table></form></div>');
    var _ptsdiv=$('#supkgs');
    if(myinfo && myinfo.uid && myinfo.uid.indexOf('fb_')==0){
    	$('#checkout_gc').hide();$('#checkout_pp').hide();
    }else{
    	$('#checkout_fc').hide();
    }
    setevents();

    self.show=function(){
    	if(_bkid==null){
    		showbooks();
    		if(promoted){
    			_bkid = promoted;
    			self.setBook(promoted);
    		}
    	}
    	_div.show();
    }
    self.setBook=function(g){
    	_bkid = g;
    	if(_books!=null && _books[g]){
    		showitems(g);
    	}else{
    		load(g);
    	}
    }
    self.hide=function(){_div.hide();}
    function load(bkid){
        $('#vgoods_caption').html('Loading items...');
        $('#mypts').html(myinfo.pts);
        $.post('/market/items/'+bkid,function(resp){
            //console.log(resp);
            if(resp.error){
                //$('#vgoods_caption').html(resp.error);
                alert(resp.error);
            }else{
            	if(_books == null)_books = {};
                if(resp.items){
            	    _books[bkid] = resp.items;//[{id:vgid,price:,note:,name:},..]
            	    showbooks();
            	    showitems(bkid);
                }
            }
        },'json');
        //if(myinfo['role'] && myinfo.role=='A') newitem();
    }
    function showbooks(){
        if(g_books){
            var sos=[];
	        for(var b in g_books){
	        	var bk=g_books[b];
	        	if(bk.title){
	        		sos.push('<option value="'+b+'">'+bk.title+'</option>');
	        	}
	        }
	        $('#market_select_game').html(sos.join(''));
        }
    }
    function showitems(bkid){
    	var bk=g_books[bkid];
        if(typeof(bk)=='undefined' || bk==null) {
        	$('#vgoods_caption').html('Book not found');
        	$('#market_select_game').val('');
        	return;
        }
        $('#market_select_game').val(bkid);
        if(_books[bkid].length>0){
        $('#vgoods_caption').html(bk.title);
        var buf=['<table class="tabfull">'];
        for(var i=0,it;it=_books[bkid][i];i++){
            //var gam = '<div><img src="/mm/bk_'+bkid+'?v='+bk.version+'" width="24"/></div><div title="'+bk.title+'">'+bk.title.substr(0,10)+'.. </div>';
            var itm = '<div><img src="/mm/vg_'+it.id+'?v='+it.version+'" width="24"/> '+it.name+'</div>';
            var buy = '<input style="width:60px;text-align:center;" id="qty_'+it.id+'" value="1"/> <button id="buy_'+it.id+'">Buy</button>';
            buf.push('<tr><td>'+itm+'</td><td style="text-align:left;">'+it.note+'</td><td id="price_"'+it.id+' style="text-align:center">'+it.price+'<img src="/img/sb20.png"/></td><td style="width:120px;">'+buy+'</td></tr>');
        }
        buf.push('</table>');
        $('#vitemlist').html(buf.join(''));
        }else{
        	$('#vgoods_caption').html(bk.title+' [has no virtual goods]');
        }
    }
    function newitem(){
        var html='<div><form id="itemform" enctype="multipart/form-data" action="/market/upload" method="post">'+
            '<table style="margin:5px auto;"><caption>Create a new virtual goods item</caption><tbody>'+
            '<tr><td>Item name:</td><td><input type="text" name="itm" width="40"/></td><td class="note">5 to 16 chars</td></tr>'+
            '<tr><td>Book:</td><td><select id="select_book" name="bkid"></select></td><td class="note"></td></tr>'+
            '<tr><td>Price:</td><td><input type="text" name="price" width="40"/></td><td class="note">Price for this item</td></tr>'+
            '<tr><td>Display:</td><td><select name="display"><option value="True">Yes</option><option value="False">No</option></select></td><td class="note">Display in public market or not</td></tr>'+
            '<tr><td>Description:</td><td><textarea name="note" width="40"></textarea></td><td class="note">What this item is about</td></tr>'+
            '<tr><td>Logo image:</td><td><input name="logofile" id="logofile" type="file"/></td><td>a 32x32 pixels png or jpg file</td></tr>'+
            '<tr><td colspan="3" style="text-align:center"><input name="submit" type="submit" value="Submit" style="width:120px"/></td></tr></table></form></div>';
        _div.append(html);
        if(mybooks){
            var buf=[];
            for(var b in mybooks){
                var bk=g_books[b];
                if(bk){
                    buf.push('<option value="'+b+'">'+bk.title+'</option>');
                }
            }
            $('#select_book').html(buf.join(''));
        }
    }
    function setevents(){
        $('#vitemlist').delegate('button','click',function(){
            var id=$(this).attr('id');
            //console.log(id);
            if(id.indexOf('like_')==0){
                $.post('/market/like/'+id.substr(id.indexOf('_')+1),function(rd){
                var sp=$('#likes'+id.substr(id.indexOf('_')));
                sp.html(parseInt(sp.html())+1);
                });
            }else if (id.indexOf('buy_')==0){
                var itm=id.substr(id.indexOf('_')+1);
                var qty=parseInt($('#qty_'+itm).val());
                if (qty <= 0){
                    alert('Invalid amount to buy');
                    return;}
                Market.purchase(itm,qty,function(resp){
                	if(resp.error)alert(resp.error);
                });
            }
        });
       $('#buypts').click(function(){_ptsdiv.css(centercss(_ptsdiv)).css({'top':'150px','margin-top':'0px'}).show();});
       $('#cancel_checkout').click(function(){
            $('#supkgs').hide();return false;
       });
       $('#market_select_game').change(function(){
    	   var bkid=$(this).val();//if(console)console.log('::market_select_game.change,bkid=',bkid);
    	   if(_books[bkid])
    		   showitems(bkid);
    	   else
    		   load(bkid);
       });
    }
}

var _gselectvgcallback=null;
function selectMygoods(callback){
	_gselectvgcallback = callback;
	if(_gmygoods!=null){
		var sd=$('#div_selectvgoods');
		if(sd.length<1){
			$('<div id="div_selectvgoods"><div id="div_mygoods"></div><div><span id="sp_selecteditem"></span><span style="float:right"><button>OK</button> <button>Cancel</button></span></div></div>').appendTo('#content');
			var buf=[];
			for(var i=0,g;g=_gmygoods[i];i++){
				buf.push('<div><img src="/mm/vg_'+g.id+'?v='+g.version+'" title="'+g.id+'"/><br/>'+g.name+'</div>');
			}
			$('#div_mygoods').html(buf.join(''));
			$('#div_mygoods').delegate('img','click',function(){
				var g=$(this).attr('title');
				$('#div_mygoods img').css('border','white');
//				console.log('Selected vg:',g);
				$('#sp_selecteditem').html(g);
				$(this).css('border','1px solid red');
			});
			sd=$('#div_selectvgoods');
			sd.css(centercss(sd)).delegate('button','click',function(){
				if($(this).html()=='OK'){
					var g=$('#sp_selecteditem').html();
//					console.log('apply selected:',g);
					if(_gselectvgcallback!=null) _gselectvgcallback(g);
				}
				$('#div_selectvgoods').hide();
			});
		}else {
			sd.show();
		}
	}else alert('No virtual goods, create first');
}
