/**
 * Generate <A list of authors with id and name.
 */
function genAuthorList(authors){
    var aus = [];
    for(var x=0,xa;xa=authors[x];x++){
        var aas=xa.split(':');
        aus.push('<a href="#" class="author_anc" id="aa_'+aas[0]+'">'+aas[1]+'</a>');
    }
    return aus.join(', ');
}
function authorform(params){
	var rs='<form method="POST" action="/authors/profile"><input type="hidden" id="ca_bda" name="bda" value="0"/>'+
	'<table align="center"><tr><td>Title:</td><td><select name="title"><option value="Mr.">Mr.</option><option value="Mrs.">Mrs.</option><option value="Ms.">Ms.</option><option value="Miss">Miss</option></select></td></tr>'+
	'<tr><td>First Name:</td><td><input type="text" name="fname" value="_firstname"/></td></tr>'+
	'<tr><td>Last Name:</td><td><input type="text" name="lname" value="_lastname"/></td></tr>'+
	'<tr><td>Email:</td><td><input type="text" name="email" value="_email"/></td></tr>'+
	'<tr><td>Address:</td><td><textarea name="address">_address</textarea></td></tr>'+
	'<tr><td>Role:</td><td><select name="job"><option value="AW">Artist/Writer</option><option value="A">Artist</option><option value="W">Writer</option></select></td></tr>'+
	'<tr><td colspan="2">Self Introduction:<br><textarea name="intro">_intro</textarea></td></tr>'+
	'<tr><td colspan="2">Web links (your application will be approved based on your links):<br><table>'+
	'<tr><td>Facebook Page:</td><td><input type="text" name="facebook" value="_fbpage"/></td></tr>'+
	'<tr><td>Blog:</td><td><input type="text" name="blog" value="_Blog"/></td></tr>'+
	'<tr><td>Website:</td><td><input type="text" name="web" value="_Web"/></td></tr>'+
	'<tr><td>Twitter:</td><td><input type="text" name="twitter" value="_Twitter"/></td></tr>'+
	'<tr><td>LinkedIn:</td><td><input type="text" name="linkedin" value="_LinkedIn"/></td></tr>'+
	'<tr><td>Other:</td><td><input type="text" name="other" value="_Other"/></td></tr>'+
	'</table></td></tr>'+
	'<tr><td colspan="2"><input type="submit" value="Submit"/></td></tr>'+
	'</table></form>';
	if (params){
		return rs.replace(/([">])_(\w+)(["<])/g,function(a,l,m,r){return l+(params[m] || params.links[m] || '')+r;});
	}else{
		return rs.replace(/([">])_\w+(["<])/g,'$1$2');
	}
}
/**
 * Author list page content holder.
 */
var SuiAuthors = function() {
    var self=this,_allauthors=null;//[{id:'',name:'',pic:'http://..',appuse:true},..]
    var _suiauthors=null;//authors saved who plays what,[{id:'',game:''},..]
    var _div = genAddPanelBox('div_authors','middlebox');
    _div.append(genTitledPanel('authorlist','Our Prestigious Writers and Artists',''));

    self.show=function(){if(_allauthors==null)load();_div.show();}
    self.hide=function(){_div.hide();}
    function load(){
        if (imReader() && ($('#apply_btn').length<=0)){
        	var hs='<button id="apply_btn">Apply</button><br/>If you are a freelance writer/artist, or a studio, and intend to publish your work on Suinova Comics Portal, please apply for a creators account and wait for approval. Please read our <a href="/html/tos2.html" target="_blank">Terms</a> before you apply.';
        	_div.append(genTitledPanel('apply4author','Apply for authorship',hs));
        	$('#apply_btn').click(function(){$('#apply4author').html(authorform());});
        } else if (imApplied() && ($('#apply_btn').length<=0)){
        	_div.append(genTitledPanel('apply4author','Applied for authorship','Please wait for approval, or submit your application again: <button id="apply_btn">Re-apply</button> (Leave the fields blank if no need to change)'));
        	$('#apply_btn').click(function(){$('#apply4author').html(authorform());});
        }
        $('#authorlist').html('Loading authors list...');
        $.post('/home/authors',function(resp){
            //resp:[{"uid":"gg_xx","name":"name","job":"Artist","books":4,"intro":"..."},..]
            if(resp.error){alert(resp.error);}else{
                //if(console)console.log(resp);
                var buf=['<table class="tabfull">'];
                for(var i=0,a;a=resp[i];i++){
                    //console.log(a.uid);
                    var job={A:'Artist',W:'Writer',AW:'Artist/Writer'}[a.job];
                /*buf.push('<div style="overflow:auto;padding:4px;border-bottom:1px solid gray;font-size:9pt"><div style="float:left;text-align:center;width:50px;height:50px;border-right:1px dotted gray"><img id="ai_'+a.uid+'" src="'+profile_pic_url(a.uid,'small')+'" height="50"/></div>'+
                    '<div style="float:left;overflow:auto;padding:4px;"><div><span style="font-weight:bold" id="ab_'+a.uid+'">'+a.name+'</span>, '+job+', '+a.books+' books</div>'+
                    '<div>'+a.intro+'</div></div></div>');*/
                    buf.push('<tr>');
                    buf.push('<td style="width:60px;text-align:center;cursor:pointer;"><img id="ai_'+a.uid+'" src="'+profile_pic_url(a.uid,'small')+'" height="50"/></td>');
                    buf.push('<td style="vertical-align:top"><div style="padding:2px"><span style="font-size:11pt;font-weight:bold;cursor:pointer;" id="ab_'+a.uid+'">'+a.name+'</span> ('+job+', '+a.books+' books)</div>');
                    buf.push('<div style="padding:2px;height:40px;overflow:hidden;">'+a.intro+'</div></td>');
                    buf.push('</tr>');
                }
                buf.push('</table>');
                $('#authorlist').html(buf.join(''));
            }
        },'json');
    }
    $('#authorlist').delegate('img','click',function(){
        var s=$(this).attr('id');
        var uid=s.substring(3);
        toauthor(uid);
    });
    $('#authorlist').delegate('span','click',function(){
        var uid=$(this).attr('id').substr(3);
        toauthor(uid);
    });
    function toauthor(uid){
        //if(console)console.log('toauthor ',uid);
    	Main.menus.author.reload(uid);
    	Main.showPage('author');
    }
}

var SuiAuthor = function() {
    var self=this,_aid=null,_goods=null;
    var _authors = {}; //aid:{aid,name,intro,fbpage,links,works}
    //var profile='<div id="usr_pic_frame"></div><div style="float:left;" id="sauth_info_div"></div>';
    var profile='<table class="tabfull"><tr><td style="width:200px;text-align:center;"><img id="usr_pic_frame" class="frmimg" src=""/></td><td style="vertical-align:top" id="sauth_info_div"></td></tr></table>';
    var _div = genAddPanelBox('div_author','middlebox');
    _div.append(genTitledPanel('author_profile','<span class="author_name wsleft">My</span><span class="wsleft">&nbsp; Profile</span><button id="other_authors" style="float:right;">Others</button><div style="clear:both"></div>',profile));
    _div.append(genTitledPanel('author_books','<span class="author_name wsleft">My</span><span class="wsleft">&nbsp; Books</span><button id="addbook" style="float:right">+ New Book</button><div style="clear:both"></div>',''));
    if(imAuthor()){
    _div.append(genTitledPanel('author_items','<span class="author_name wsleft">My</span><span class="wsleft">&nbsp; Assets</span><button id="additem" style="float:right">+ New Item</button><div style="clear:both"></div>',''));
    _div.append(genTitledPanel('item_stats','Item Statistics','To be available'));
    }
    $('#other_authors').click(function(){
        //console.log($(this).html(),'clicked');
        Main.showPage('authors');
    });
	$('#sauth_info_div').delegate('button','click',function(){
		//edit author profile
//		$.post('/author/profile/'+myinfo.uid,function(resp){
//			if(resp.error)alert(resp.error);else{
				$('#sauth_info_div').html(authorform(_authors[myinfo.uid]));
//			}
//		},'json');
	});
    $('#addbook').click(function(){
        Main.menus.bookedit.setBook(null);
        Main.showPage('bookedit');
    });
    $('#author_books').delegate('button','click',function(){
    	var btn=$(this);
        var id=btn.attr('id');
        if(id.indexOf('edb_')==0){
        	Main.menus.bookedit.setBook(id.substr(4));
        	Main.showPage('bookedit');
        }else if(id.indexOf('deb_')==0){
        	if(confirm('Are you sure to delete this book?')){
        		var bkid = id.substr(4);
        		$.post('/book/delete/'+bkid,function(resp){
        			if(resp.error)alert(resp.error);else{
        				//tr/td/button
        				var tr=btn.parent().parent();
        				tr.remove();
        				location.reload();
        			}
        		},'json');
        	}
        }
    });
    $('#author_books').delegate('span','click',function(){
    	var bid=$(this).attr('id');
    	openBook(bid);
    });
    $('#author_items').delegate('button','click',function(){
    	var itmbtn=$(this);
        var itm=itmbtn.attr('id');
        if(itm.indexOf('edi_')==0){
        	itm = itm.substr(4);
	        for(var i=0,it;it=_goods[i];i++){ //[{id,name,type,book,price,display,likes}
	            if(it.id==itm){
	                Main.menus.itemedit.setItem(it);
	                Main.showPage('itemedit');
	                break;
	            }
	        }
        }else if(itm.indexOf('dei_')==0){
        	itm = itm.substr(4);
        	if(confirm('Are you sure to delete this item?')){
        		$.post('/market/delitem/'+itm,function(resp){
        			if(resp.error)alert(resp.error);else{
        				var tr=itmbtn.parent().parent();
        				tr.remove();
        			}
        		},'json');
        	}
        }
    });
    $('#additem').click(function(){
        Main.menus.itemedit.setItem(null);
        Main.showPage('itemedit');
    });
    self.show=function(){if(_aid==null)load(myinfo.uid);_div.show();}
    self.hide=function(){_div.hide();}
    function load(aid){
    	_aid = aid;
    	if(myinfo.uid && myinfo.uid==aid){
    		$('#addbook').show();$('#additem').show();
    	}else{
    		$('#addbook').hide();$('#additem').hide();
    	}
    	if(_authors[_aid]){
    		display(_authors[_aid]);
    	}else{
    		$.post('/author/profile/'+_aid,function(rs){
    			if(rs.error)alert(rs.error);else{
    				_authors[_aid] = rs;
    				display(rs);
    			}
    		},'json');
    	}
    }
    function formatmb(b){
    	var m = b / 1048576.;
    	return m.toFixed(3);
    }
    function display(au){
    	//$('#usr_pic_frame').html('<img src="'+profile_pic_url(_aid,'large')+'" class="frmimg"/>');
    	$('#usr_pic_frame').attr('src',profile_pic_url(_aid,'large'));
    	var ebtn=(au.spaceused)?' <button id="edt_aprof">Edit</button>':'';
    	var buf=['<div style="font-weight:bold">'+au.name+ebtn+'</div>','<div style="padding:4px 0">'+au.intro+'</div>'];
    	buf.push('<div><b>Facebook Page: </b><a href="'+au.fbpage+'" target="_blank">'+au.fbpage+'</a></div>');
    	if(au.links)
    	for(var k in au.links){
    		var lnk=au.links[k];
    		if (lnk.indexOf('http')!=0) lnk = 'http://'+lnk;
   			buf.push('<div><b>'+k+'</b>: <a href="'+lnk+'" target="_blank">'+lnk+'</a></div>');
    	}
    	if(au.spaceused) buf.push('<div><b>Space Used</b>: '+formatmb(au.spaceused)+' (quota: 5MB)</div>');
    	$('#sauth_info_div').html(buf.join(''));
    	var wrks=[];for(var w in au.works)wrks.push(w);
    	if(wrks.length>0)showMyBooks(wrks,'author_books');else $('#author_books').html('');
        if(imAuthor()){
        	$('.author_name').html('My');
        	$('#author_items').show();
            $.post('/home/goods/author/'+_aid,function(resp){
                if(resp.error)alert(resp.error);else{
                	_gmygoods = _goods = resp; //[{id,name,type,book,price,display,likes}
                	VGoods.add(resp);
                    var buf=[];
                    for(var i=0,it;it=resp[i];i++){
                        var btitle=g_books[it.book].title;
                        var bver=g_books[it.book].version;
                        buf.push('<tr><td><img src="/mm/bk_'+it.book+'?v='+bver+'" height="24" title="'+btitle+'"/></td><td><img src="/mm/vg_'+it.id+'?v='+bver+'" height="24"/><br>'+it.name+' ['+it.id+']</td><td>'+it.price+'</td><td>'+it.display+'</td><td><button id="edi_'+it.id+'">Edit</button> <button id="dei_'+it.id+'">Delete</button> </td></tr>');
                    }
                    $('#author_items').html('<table class="tabfull"><tr><th>Book</th><th>Item</th><th>Price</th><th>Display</th><th></th></tr>'+buf.join('')+'</table>');
                }
            },'json');
        }else{
        	$('#author_items').hide();
        	$('.author_name').html(au.name+"'s");
        }
    }
    function showMyBooks(mbooks,divid){
    	var tab=$('<table class="linedtab tabfull"></table>');
    	$('#'+divid).html(tab);
        for(var i=0,b;b=mbooks[i];i++){
        	if(g_books[b]){
        		showBookLine(b,g_books[b],tab);
        	}else{
        		$.post('/home/book/'+b,function(rs){
        			if(rs.error)alert(rs.error);else {g_books[b]=rs;showBookLine(b,rs,tab);}
        		},'json');
        	}
        }
    }
    function showBookLine(b,bk,tab){
    	var buf=['<tr>'];
    	buf.push('<td style="width:80px;text-align:center"><img src="/mm/bk_'+b+'?v='+bk.version+'" height="32"/></td>');
    	buf.push('<td style="text-align:left;font-weight:bold;"><span style="cursor:pointer" id="'+b+'">'+bk.title+'</span></td>');
    	buf.push('<td style="text-align:right">');
    	if(imAuthorOf(bk)){
    		buf.push('<button id="edb_'+b+'">Edit</button> ');
    		buf.push('<button id="deb_'+b+'">Delete</button> ');
    	}
    	buf.push('</td>');
    	buf.push('</tr>');
    	tab.append(buf.join(''));
    }
    self.reload=function(aid){
        if (aid != _aid){
            load(aid);
        }
    }
}
function showAuthor(aid){
    Main.menus.author.reload(aid);
    Main.showPage('author');
}
