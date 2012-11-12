/**
 * Readers galleries list including top 10 and random 10 as well login users friends.
 */
var SuiGalleries = function() {
    var self=this,_top=null;
    var _div=genAddPanelBox('div_galleries','middlebox');
    _div.append(genTitledPanel('top_galleries','Top Collectors',''));
    _div.append(genTitledPanel('active_galleries','Recent Active Collectors',''));
    _div.append(genTitledPanel('friends_galleries','<span class="wsleft">My Friends</span><button id="sb_invite" style="float:right">Invite</button><div style="clear:both"></div>','Loading friends galleries'));
    self.show=function(){if(_top==null) load();_div.show();}
    self.hide=function(){_div.hide();}
    $('#div_galleries').delegate('img','click',function(){
    	Main.menus.gallery.setUser($(this).attr('id'));
    	Main.showPage('gallery');
    });
    $('#sb_invite').click(function(){
    	if(typeof(invite_friends)!='undefined')invite_friends();
    });
    function load(){
        $.post('/home/galleries',function(resp){
            if(resp.error)alert(resp.error);else{
            //{'top':{uid:'',name:''},'active':{uid:'',name:''}}
                _top = resp.top;
                showCollectors($('#top_galleries'),_top);
                showCollectors($('#active_galleries'),resp.active);
                if(typeof(get_friends)!='undefined')
                	get_friends(1,function(usrs){
                		if(usrs){
                			var buf=[];
                			var dv=$('#friends_galleries');
                			dv.html('');
                			for(var i=0,u;u=usrs[i];i++){
                				var s=$('<img class="imgcollector" id="'+u.id+'" src="'+u.pic+'" title="'+u.name+'"/>');
                				dv.append(s);
                			}
                		}
                	});
            }
        },'json');
    }
    function showCollectors(dv,clist){
    	//var buf=['<table class="tabfull" style="table-layout:fixed;"><tr>'];
    	var tab=$('<table class="tabfull" style="table-layout:fixed;"></table>');
    	dv.html(tab);
    	var tr=$('<tr></tr>');
    	tab.append(tr);
    	var cols=8;
    	var i=0;
    	for(var c in clist){
    		load_profile(c,function(p){
    			if(i > 0 && i % cols == 0){
    				tr=$('<tr></tr>');
    				tab.append(tr);
    			}
    			i++;
    				//buf.push('</tr><tr>');i++;
    			var buf=[];
    			buf.push('<td align="center">');
    			buf.push('<div style="white-space:nowrap;overflow:hidden;">'+p.name+'</div>');
    			buf.push('<div><img class="imgcollector" id="'+c+'" title="'+p.name+'" src="'+p.picture+'"/></div>');
    			buf.push('<div>'+clist[c]+'</div>');
    			buf.push('</td>');
    			tr.append(buf.join(''));
    		});
    	}
    }
}

var SuiGallery = function(){
    var self=this,_uid=null;
    var _div=genAddPanelBox('div_gallery','middlebox');
    var room='<div id="div_galleryswf"><p><a href="http://www.adobe.com/go/getflashplayer">'+
            '<img src="http://www.adobe.com/images/shared/download_buttons/get_flash_player.gif" alt="Get Adobe Flash player" /></a></p></div>';
    _div.append(genTitledPanel('reader_gallery','<span id="reader_name" class="wsleft">My</span><span class="wsleft">&nbsp; Gallery</span><button id="others_gallery" style="float:right;font-size:9pt;">Others</button><div style="clear:both"></div>',room));
    _div.append(genTitledPanel('my_inventory','My Inventory',''));
    _div.append(genTitledPanel('friends_galleries2','<span class="wsleft">My Friends</span><button id="sb_invite2" style="float:right;">Invite</button><div style="clear:both"></div>','Loading friends...'));
    $('#others_gallery').click(function(){
        Main.showPage('readers');
    });
    self.show=function(){load();_div.show();}
    self.hide=function(){_div.hide();}
    $('#my_inventory').delegate('button','click',function(){
    	//console.log($(this).attr('id'),'>>> send to server and Flash object,change number here');
    	var btn=$(this);
    	var id=btn.attr('id');
    	var gid=id.substr(id.indexOf('_')+1);
    	$.post('/gallery/collect/'+gid,function(resp){
    		if(resp.error)alert(resp.error);else{
    			Suinova.newitem(resp);
    			myinfo.inv[gid]--;
    			if(myinfo.inv[gid] <= 0){
    				btn.parent().remove();
    			}else{
    				showInvGoods(myinfo.inv);
    			}
    		}
    	},'json');
    });
    $('#sb_invite2').click(function(){
    	if(typeof(invite_friends)!='undefined')invite_friends();
    });
    $('#friends_galleries2').delegate('img','click',function(){
    	Main.menus.gallery.setUser($(this).attr('id'));
    	Main.showPage('gallery');
    });
    function load(){
        //load my inventory, some of these items can be added to the rooms in the gallery
    	if(_uid == null)_uid = myinfo['uid'];
    	Suinova.setUser(_uid);
	//	_uid=myinfo.uid;
        var flprms={menu:"false",scale:"noScale",allowFullscreen:"false",allowScriptAccess:"always",bgcolor:"#FFFFFF"};
        swfobject.embedSWF('/js/suigallery.swf?v=1','div_galleryswf',740,500,"9.0.0","/js/expressInstall.swf",{},flprms,{id:"suigallery"});
		if(_uid == myinfo['uid']){
			if(myinfo.inv=='')myinfo.inv={};
			showInventory(myinfo.inv);
		}
        if(typeof(get_friends)!='undefined')
        	get_friends(1,function(usrs){
        		if(usrs){
        			var buf=[];
        			var dv=$('#friends_galleries2');
        			dv.html('');
        			for(var i=0,u;u=usrs[i];i++){
        				var s=$('<img class="imgcollector" id="'+u.id+'" src="'+u.pic+'" title="'+u.name+'"/>');
        				dv.append(s);
        			}
        		}
        	});
    }
    self.reload=function(){
    	load();
    }
    self.refresh=function(){
    	showInventory(myinfo.inv);
    }
    self.setUser=function(uid){
    	_uid = uid;
    	if(_uid != myinfo.uid) {
    		hideInventory();
            $('#reader_name').html('Reader&#39;s');
        }else{
            $('#reader_name').html('My');
        }
    }
    self.addItem=function(item){
    	//add an item from flash: add to myinfo.inv, and show it
    	myinfo.inv[item] = (myinfo.inv[item] || 0) + 1;
    	showInventory(myinfo.inv);
    }
    function showInventory(inv){
    	//{"item":n,..
    	var vbuf=[];
    	for(var it in inv){
    		if(VGoods.find(it)==null)vbuf.push(it);
    	}
    	if(vbuf.length>0){
    		VGoods.load(vbuf, function(resp){
    			showInvGoods(inv);
    		});
    	} else
    		showInvGoods(inv);
    	$('#my_inventory').parent().show();
    }
    function showInvGoods(inv){
    	var buf=['<table class="tabfull"><tr>'];
        var cols=7;
        var i=0;
    	for(var it in inv){
    		var g = VGoods.find(it);
    		if (g==null){alert(it+' not found');return;}
    		if(inv[it]<=0)continue;
    		var bk=g_books[g.book];
    		var bkt=(bk)?'from '+bk.title:'';
            if(i>0 && i % cols==0)buf.push('</tr><tr>');
            i++;
            buf.push('<td align="center">');
    		var btn = (g.gallery=='True')?'<button id="disp_'+it+'" title="Move to the gallery room above">Use</button>':'';
    		buf.push('<div class="gcollector"><div style="margin:2px auto;width:50px;height:50px;background:url(/mm/vg_'+it+'?v='+g.version+') no-repeat center" title="'+g.name+' '+bkt+'"></div>');
    		buf.push('<div style="font-size:9pt;white-space:no-wrap;overflow:hidden" title="'+g.name+'('+inv[it]+') '+bkt+'">'+g.name.substr(0,6)+'('+inv[it]+')</div>'+btn+'</div>');
            buf.push('</td>');
    	}
        buf.push('</tr></table>');
    	$('#my_inventory').html(buf.join(''));
    }
    function hideInventory(){
    	$('#my_inventory').parent().hide();
    }
}
