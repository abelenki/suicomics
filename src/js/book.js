var BookShelf = {   //uses g_books as global array
    loadbook: function(bkid,cb){
        if(g_books[bkid] && g_books[bkid]!=null)
            if(cb) cb(g_books[bkid]);
        else{
            $.post('/home/book/'+bkid,function(resp){
                if(resp.error)alert(resp.error);else{
                    if(resp[bkid]){
                        g_books[bkid] = resp[bkid];
                        if(cb)cb(resp[bkid]);
                    }else alert('Book info not received');
                }
            },'json');
        }
    },
    showbooks: function(bkidlst,dves,cols){ //show all books as table in a div
        var ncols = cols || 2;
        if(typeof(dves)=='string' && dves.indexOf('#')!=0)dves='#'+dves;
        var dv = $(dves),
        	tab=$('<table class="tabright"></table>'),tr;
        dv.html('');dv.append(tab);
        for(var i=0,n=0,bid;bid=bkidlst[i];i++){
        	if(n==0){tr=$('<tr>');tab.append(tr);}
        	var td=$('<td>');tr.append(td);
            BookShelf.showbook(bid,td);
        	if(++n>=ncols) n=0;
        }
        dv.delegate('.sb_','click',function(){
            var bid=$(this).attr('id');
            openBook(bid.substr(4));
        });
        dv.delegate('td a','click',function(){
            var aid=$(this).attr('id');
            showAuthor(aid.substr(3));
        });
    },
    showbook: function(bid,td){
        BookShelf.loadbook(bid,function(bk){
            var html='<table><tr>'+
                '<td class="bkimg" style="border:0;"><img class="sb_" src="/mm/bk_'+bid+'?v='+bk.version+'" width="80" height="80" id="bki_'+bid+'"/></td>'+
                '<td style="vertical-align:top;text-align:left;border:0;"><div class="sb_" style="font-weight:bold;cursor:pointer" id="bkt_'+bid+'">'+bk.title+'</div>'+
                '<div style="margin-top:4px;">By '+genAuthorList(bk.authors)+'</div></td></tr></table>';
            td.html(html);
        });
    }
}

var SuiBookEdit = function(){
    var self=this,_bkid=null,_bk=null,_zines=null;
    var _div = genAddPanelBox('div_bookedit','middlebox');
    var bcontent='<form id="be_form" enctype="multipart/form-data" action="/book/upload" method="post">'+
        '<input type="hidden" id="be_bkid" name="bkid" value=""/><table class="linedtab tabfull"><tr><td>Title:</td><td><input type="text" id="be_title" name="title"/></td><td class="note">Book title</td></tr>'+
        '<tr><td>Author(s):</td><td><span id="be_authors"></span></td><td class="note">Contact admins to add more creators.</td></tr>'+
        '<tr><td>Status:</td><td><select id="be_status" name="status"><option value="Finished">Finished</option><option value="Ongoing">Ongoing</option></select></td><td class="note">Change the status to complete if book finished.</td></tr>'+
        '<tr><td>Genre:</td><td><select id="be_genre" name="genre" multiple size="3">'+genreselect()+'</select></td><td class="note">Use Ctrl to select up to three genres.</td></tr>'+
        '<tr><td>Page height:</td><td><input name="height" value="500"/></td><td>Page height in pixels (500-800)</td></tr>'+
        '<tr id="bfrmtabzins"><td>Picture(thumb):</td><td><input type="file" name="logofile"/></td><td class="note"><img id="be_logo" src=""/>240x240 jpg image file only (thumbnail resized as 80x80)</td></tr>'+
        '<tr><td colspan="3"><div style="text-align:center;font-weight:bold">Introduction</div><textarea id="be_intro" rows="8" name="intro"></textarea></td></tr>'+
        '<tr><td colspan="3"><div style="text-align:center;font-weight:bold">Table of Content</div><textarea id="be_toc" rows="10" name="toc"></textarea></td></tr>'+
        '<tr><td colspan="3"><div style="text-align:center;font-weight:bold">Authors Notes</div><textarea id="be_notes" rows="10" name="notes"></textarea></td></tr>'+
        '<tr><td colspan="3"><div style="text-align:center;font-weight:bold">Quests <a href="/html/howto.html#quests" target="_blank"><img src="/img/help.png" border="0"/></a></div><textarea id="be_quests" rows="10" name="quests"></textarea></td></tr>'+
        '<tr><td colspan="3" style="text-align:center"><input id="bksubtn" type="submit" value="Submit" style="width:120px"/></td></tr>'+
        '</table></form><div><button id="edit_bk_cnt_btn" style="display:none">Edit Pages</button> </div>';
    _div.append(genTitledPanel('edit_book','<span id="be_title1" class="wsleft">New Book</span><button id="BKBack2Creators" style="float:right">Back</button><div style="clear:both"></div>',bcontent));
    $('#BKBack2Creators').click(function(){
    	Main.showPage('author');
    });
    self.show=function(){_div.show();}
    self.hide=function(){_div.hide();}
    $('#edit_bk_cnt_btn').click(function(){
		Main.menus.pagedit.setBook(_bkid,_bk);
		Main.showPage('pagedit');
    });
    self.setBook=function(bid){
    	if(_zines==null){
    		/*$.post('/author/zines/'+myinfo.uid,function(resp){
    			if(resp.error);else{
    				_zines = resp;
    				var buf=[];
    				for(var i=0,z;z=_zines[i];i++) buf.push('<option value="'+z[0]+'">'+z[1]+'</option>');
    				$('#bfrmtabzins').before('<tr><td>Periodical:</td><td><select name="zine"><option value="none">None</option>'+buf.join('')+'</td></tr>');
    			}
    		},'json');*/
    	}
    	_bkid = bid;
        _bk = (bid==null)?null:g_books[bid];
        $('#be_title1').html((_bk==null)?'New Book':_bk.title);
        $('#be_bkid').val((_bk==null)?'':bid);
        $('#be_title').val((_bk==null)?'':_bk.title);
        $('#be_authors').html((_bk==null)?'':genAuthorList(_bk.authors)); //TODO: add name for id
        //console.log('done');
        $('#be_status').val((_bk==null)?'Ongoing':_bk.status);
        if(_bk!=null) {
        	$('#be_genre').val(_bk.genre);
        	$('#edit_bk_cnt_btn').show();
        } else {
        	$('#be_genre').val('');
        	$('#edit_bk_cnt_btn').hide();
        }
        $('#be_logo').attr('src',(_bk==null)?'':'/mm/bk_'+bid+'?v='+_bk.version);
        $('#be_intro').val((_bk==null)?'':formatParagraph(_bk.intro));
        $('#be_toc').val((_bk==null)?'':formatParagraph(_bk.toc));
        $('#be_notes').val((_bk==null)?'':formatParagraph(_bk.notes));
        $('#be_quests').val((_bk==null)?'':formatQuests(_bk.quests));
    };
    var submitcount = 0;
    $('#be_form').submit(function(){
    	submitcount++;
    	if(submitcount > 1){$('#bksubtn').val('Submitting');return;}setTimeout(function(){submitcount=0;$('#bksubtn').val('Submit');},2000);
        if($.trim($('#be_title').val())=='')alert('Empty title');else
        if($.trim($('#be_intro').val())=='')alert('No intro');else
        if($('#be_genre').val()==null)alert('Please select a Genre');else
        if(!validateQuests($('#be_quests').val()))alert('Invalid Quest scripts');else{
        	return true;
        }
        return false;
    });
    function validateQuests(qs){
        var s=qs.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
        if(qs=='')return true;
        var r=/\[(\{"qid":\d+,"qname":"[\w ]+","items":\[(\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[[^\]]*\]\},)*\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[[^\]]*\]\}\],"prize":\d+,"intro":"[^"\r\n]*"\},)*\{"qid":\d+,"qname":"[\w ]+","items":\[(\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[\]\},)*\{"vgid":\d+,"x":\d+,"y":\d+,"sc":[\d.]+,"filters":\[\]\}\],"prize":\d+,"intro":"[^"\r\n]*"\}\]/;
        return r.test(s);
    }
    function formatQuests(q){
    	if(typeof(q)=='undefined' || q==null)return '';
    	if(typeof(q)=='string')return q;
    	var qs=[];
    	for(var i=0,qi;qi=q[i];i++){
    		var qis='"qid":'+qi.qid+',"qname":"'+qi.qname+'","items":';
    		var itms=[];
    		for(var j=0,it;it=qi.items[j];j++){
    			itms.push('{"vgid":'+it.vgid+',"x":'+it.x+',"y":'+it.y+',"sc":'+it.sc+',"filters":['+it.filters+']}');
    		}
    		qis += '['+itms.join(',')+']';
    		qs.push('{'+qis+',"prize":'+qi.prize+',"intro":"'+qi.intro+'"}');
    	}
    	return '['+qs.join(',')+']';
    }
}

/**
 * SuiBook page holder.
 */
var SuiBook = function() {
    var self=this,_book=null,_bkid=null;
    var _div = genAddPanelBox('div_book','middlebox');
    var bookinfo='<table class="tabfull"><tr><td style="width:250px;padding:5px;text-align:center;vertical-align:center;"><img style="cursor:pointer" id="bk_img" src=""/><button id="read_btn">Read</button></td>'+
    	'<td style="vertical-align:top;padding:5px;"><table id="buktab"><tr><td>Title:</td><td><span id="book_title2"/></td></tr>'+
    	'<tr><td>Authors:</td><td><span id="book_authors"/></td></tr><tr><td>Genre:</td><td><span id="book_genre"/></td></tr>'+
    	'<tr><td>Started:</td><td><span id="book_started"></span></td></tr>'+
    	'<tr><td>Pages:</td><td><span id="book_pages">1</span></td></tr><tr><td>Visits:</td><td><span id="book_visits"/>, <span id="book_recs"/></td></tr>'+
    	'<tr><td>Quests:</td><td><span id="book_quests">0</span></td></tr><tr><td>Status:</td><td><span id="book_status"></span></td></tr>'+
    	'</table></td></tr></table>';
//    var bookinfo='<div id="book_logo" style="float:left;width:120px;height:120px;text-align:center;padding-top:20px;"></div>'+
//        '<div style="float:left;width:600px;padding:5px;"><div>Title: <span id="book_title2" style="font-weight:bold"/></div><div>Authors: <span id="book_authors"/>'+
//        ' Genre: <span id="book_genre"/> <span id="book_visits"/> <span id="book_recs"/></div><div style="margin-top:5px;"></div>'+
//        '</div>';
    _div.append(genTitledPanel('book_info','<span id="book_title" class="wsleft">Title</span><button id="SBack2Buks" style="float:right">Back</button><div style="clear:both"></div>',bookinfo));
    $('#SBack2Buks').click(function(){
    	Main.showPage('home');
    });
    $('#buktab td').css('border','0');$('#buktab span').css('font-weight','bold');
    _div.append(genTitledPanel('quests','Quests','There is no quest for this book, see Monkey K for a quest example.'));
    _div.append(genTitledPanel('brief_intro','Introduction',''));
    _div.append(genTitledPanel('toc','Content',''));
    _div.append(genTitledPanel('book_stats','Reading Statistics','To be available'));	//show author or everybody? how many readers, average rate?
    _div.append(genTitledPanel('reviews','Reviews','To be available'));
    $('#book_authors').delegate('a','click',function(){var a=$(this).attr('id').substr(3);showAuthor(a);});
    self.setBook=function(bk){
    	_bkid = bk;
        if(g_books[bk]){
            _book = g_books[bk];
            showBook(bk);
        }else{
            $.post('/home/book/'+bk,function(resp){
                if(resp.error)alert(resp.error);else{
                    g_books[bk] = resp[bk];
                    _book = g_books[bk];
//                    console.log(_book);
                    showBook(bk);
                }
            },'json');
        }
    }
    $('#read_btn').click(function(){
    	Main.menus.page.setBook(_bkid);
    	Main.showPage('page');
    });
    $('#bk_img').click(function(){
    	Main.menus.page.setBook(_bkid);
    	Main.showPage('page');
    });
    function showBook(bk){
        $('#book_title').html(_book.title);
        $('#book_title2').html(_book.title);
        $('#book_authors').html(genAuthorList(_book.authors));
        $('#bk_img').attr('src','/mm/bk_'+bk+'?v='+g_books[bk].version);
//        $('#book_logo').html('<img src="/mm/bk_'+bk+'?v='+g_books[bk].version+'"/><br><button id="read_btn">Read</button>');
        $('#book_genre').html(_book.genre.join(','));
        $('#book_visits').html(_book.visits);
        $('#book_started').html(_book.started.substring(0,_book.started.indexOf(' ')));
        $('#book_pages').html(_book.pages.split(',').length);
        $('#book_recs').html(_book.recommends);
        $('#book_status').html(_book.status);
        $('#book_quests').html((_book.quests || []).length);
        $('#brief_intro').html(_book.intro);
        $('#toc').html(_book.toc);
        if(_book.quests){
        	/*var buf=['<div style="float:left;">Quests:</div>'];
        	for(var i=0,q;q=_book.quests[i];i++){
        		//{qid:2,qname:"",items:[{vgid:,x,y,sc,filters:[]},..],prize:vgid}
        		buf.push('<div style="float:left;width:80px;height:80px;text-align:center;margin:5px;">');
        		buf.push('<img id="'+i+'" src="/mm/vgb_'+q.qid+'" height="50"/>');
        		buf.push('<span>'+q.qname+'</span>');
        	}*/
            var buf=['<table id="tabquests" class="tabfull"><tr>'];
            var cols=7;
            for(var i=0,q;q=_book.quests[i];i++){
            	var found=4;
            	if (myinfo.inv)
            	for(var k=0,v;v=q.items[k];k++){
            		if(myinfo.inv[v])found++;
            	}
            	var complete=(q.items.length>0)?100*found/q.items.length:0;
            	if(complete>100)complete=100;
                if(i>0 && i%cols==0)buf.push('</tr><tr>');
                buf.push('<td><img style="cursor:pointer" id="'+i+'" src="/mm/vgb_'+q.qid+'" height="50" title="'+q.qname+'"/>');
                buf.push('<div style="cursor:pointer;white-space:nowrap;overflow:hidden;" title="'+q.qname+'">'+q.qname+'</div>');
                if(myinfo.inv)
                	buf.push('<div style="text-align:center"><div style="margin:0 auto;width:70px;border:1px solid gray;background-color:white;text-align:left;" title="'+complete+'% complete"><div style="background-color:blue;width:'+complete+'%;">&nbsp;</div></div></div>')
                buf.push('</td>');
            }
            buf.push('</tr></table>');
        	$('#quests').html(buf.join('')).delegate('img','click',function(){
        		//alert('go to quest for book '+_bkid);
        		Main.menus.quest.open(_bkid,$(this).attr('id'));
        		Main.showPage('quest');
        	});
        } else $('#quests').html('');
        //load reviews
        $('#reviews').html('Coming soon...');
    }
    
    self.show=function(){if(_div!=null)_div.show();};
    self.hide=function(){if(_div!=null){_div.hide();}};
    function load(g){
    }
}
function openBook(bkid){
    Main.menus.book.setBook(bkid);
    location.href='#';
    Main.showPage('book');
}

var SuiQuest = function(){
	var self=this,_bkid=null;
	var _div = genAddPanelBox('div_quest','middlebox');
	self.show=function(){if(_div!=null)_div.show();}
	self.hide=function(){if(_div!=null)_div.hide();}
	function load(bkid,q){
		_bkid = bkid;
		Suinova.setBookPage(_bkid,q);
		var bk=g_books[bkid];
		_div.html('');
		var flash='<div id="altContentq"><p><a href="http://www.adobe.com/go/getflashplayer">'+
        	'<img src="http://www.adobe.com/images/shared/download_buttons/get_flash_player.gif" alt="Get Adobe Flash player" /></a></p></div>';
        _div.append(genTitledPanel('div_flashq','<span class="wsleft">Quest in '+bk.title+'</span><button id="QBack2Buk" style="float:right">Back</button><div style="clear:both"></div>',flash));
        $('#QBack2Buk').click(function(){
        	Main.showPage('book');
        });
        var flprms={menu:"false",scale:"noScale",allowFullscreen:"false",allowScriptAccess:"always",bgcolor:"#FFFFFF"};
        swfobject.embedSWF('/js/suiquest.swf?v=1',"altContentq",740,500,"9.0.0","/js/expressInstall.swf",{},flprms,{id:"suiquest"});
	}
	self.open=function(bk,q){load(bk,q);}
}

var SuiPage = function(){
    var self=this,_bkid=null,_lastpage=0;
    var _div = genAddPanelBox('div_bkpg','middlebox');
    //var _div=$('#div_main').append('<div style="overflow:auto"></div>');
    self.show=function(){if(_div!=null){_div.show();}};
    self.hide=function(){if(_div!=null)_div.hide();};
    function unload(){
        //$('#div_flash').remove();
    	//if(_div)_div.html('');
    	_div.html('');
    }
    function load(bk){
        Suinova.setBookPage(bk,_lastpage);
        var bk=g_books[bk];
        var flash='<div id="altContent"><p><a href="http://www.adobe.com/go/getflashplayer">'+
            '<img src="http://www.adobe.com/images/shared/download_buttons/get_flash_player.gif" alt="Get Adobe Flash player" /></a></p></div>';
        _div.append(genTitledPanel('div_flash','<span class="wsleft">'+bk.title+'</span><button id="PBack2Buk" style="float:right">Back</button><div style="clear:both"></div>',flash));
        $('#PBack2Buk').click(function(){
        	Main.showPage('book');
        });
        //$('#div_main').append('<div id="bk_title">'bk.title+'</div>'+flash);
        //_div.html('<div id="bk_title">'+bk.title+'</div>'+flash);
        //run starting js here
        var flprms={menu:"false",scale:"noScale",allowFullscreen:"false",allowScriptAccess:"always",bgcolor:"#FFFFFF"};
        swfobject.embedSWF('/js/suireader.swf?v=1',"altContent",740,(bk==null)?640:bk.height,"9.0.0","/js/expressInstall.swf",{},flprms,{id:"suireader"});
        //_div=$('#div_flash');
    }
    self.setBook=function(bkid){
    	_bkid = bkid;
        unload();
        _bkid = bkid;
        $.post('/book/read/'+bkid,function(resp){
            if(resp.error)alert(resp.error);else{
            	if(resp.lastpage) _lastpage=resp.lastpage; else {
            		_lastpage=0;
            //		if(FB && typeof(read_book)!='undefined'/* && confirm('Post a feed of reading this book?')*/)
            //			Suinova.readBook(bkid,g_books[bkid].title,g_books[bkid].intro);
            	}
            	// TODO: delete the following:
        		if(FB && typeof(read_book)!='undefined' && confirm('Post a feed of reading this book?'))
        			Suinova.readBook(bkid,g_books[bkid].title,g_books[bkid].intro);
            }
            load(bkid);
        },'json');
    }
    self.getBook=function(){ return _bkid; }
    self.getPage=function(){ return _lastpage; }
    self.open=function(bkid){alert('Use setBook');
    }
}

var SuiPageEdit = function(){
	var self=this,_bkid=null,_book=null,_pages=9,_cpage=0,_pagedata=null;
	var _fileId=null,_fileName=null,_uploader=null,_progressBar;
	var _div=genAddPanelBox('div_pagedit','middlebox');
	var html='<div id="div_pagebar">Pages:<span id="sp_pages">0</span> | <img src="/img/first.png"/> <img src="/img/previous.png"/> <input id="cpage_num" type="text" value="0"/> <img src="/img/next.png"/> <img src="/img/last.png"/> | <button id="add_page_btn">Add</button> <button id="del_page_btn">Delete</button></div>'+
		'<div id="div_pageimage" class="page_image"></div>'+
		'<div id="div_uploadbar">Upload Image: '+
		'<div id="uploaderContainer">'+
		'<div id="uploaderOverlay" style="position:absolute;z-index:2"></div>'+
		'<div id="selectFilesLink" style="z-index:1"><a id="selectLink" href="#">Open File</a></div></div>'+
		'<div id="uploadFilesLink"><a id="uploadLink" href="#">Upload File</a></div>'+
		'<input id="progressReport" value="" readonly/></div>';

	_div.append(genTitledPanel('PageEditContent','<span class="wsleft">Page Edit</span><button id="Back2Book" style="float:right">Back</button><div style="clear:both"></div>',html));
	$('#PageEditContent').append(genTitledPanel('PageDemands','<span class="wsleft">Required Items <a href="/html/howto.html#requires" target="_blank"><img src="/img/help.png" border="0"/></a></span><button id="add_paged_btn" style="float:right;">Add Item</button><div style="clear:both"></div>',''));
	$('#PageEditContent').append(genTitledPanel('PageRewards','<span class="wsleft">Rewards <a href="/html/howto.html#rewards" target="_blank"><img src="/img/help.png" border="0"/></a></span><button id="add_pager_btn" style="float:right;">Add Item</button><div style="clear:both"></div>',''));
	$('#PageEditContent').append(genTitledPanel('PageScript','Dynamic Controls <a href="/html/howto.html#controls" target="_blank"><img src="/img/help.png" border="0"/></a>','<textarea id="script_txt" style="width:99%;height:120px;"></textarea><br><button id="script_btn">Submit</button>'));
	$('#PageEditContent').append(genTitledPanel('PageNote','Script and notes (authors only)','<textarea id="PageNoteText" style="width:99%;height:120px;"></textarea><br><button id="pnote_btn">Submit</button>'));
	$('#add_paged_btn').click(function(){
		if(_pagedata==null)return;
		selectMygoods(function(vgid){
			$.post('/author/addrequired',{bk:_bkid,pg:_pagedata[_cpage].id,vg:vgid},function(resp){
				if(resp.error)alert(resp.error);else{
				_pagedata[_cpage].rq[vgid]=1;
				showItems($('#PageDemands'),_pagedata[_cpage].rq);}
			},'json');
		});
	});
	$('#add_pager_btn').click(function(){
		if(_pagedata==null)return;
		selectMygoods(function(vgid){
			$.post('/author/addreward',{bk:_bkid,pg:_pagedata[_cpage].id,vg:vgid},function(resp){
				if(resp.error)alert(resp.error);else{
				_pagedata[_cpage].rw[vgid]={};
				showItems($('#PageRewards'),_pagedata[_cpage].rw);}
			},'json');
		});
	});
	$('#div_pagebar').delegate('img','click',function(){
		var s=$(this).attr('src');
		if(console)console.log(s.substring(s.lastIndexOf('/')+1,s.indexOf('.')));
		if(s.indexOf('first')>0){
			_cpage = 0;
		}else if(s.indexOf('last')>0){
			_cpage = _pages-1;
		}else if(s.indexOf('previous')>0){
			if(_cpage > 0) _cpage --;
		}else{
			if(_cpage < _pages-1) _cpage ++;
		}
		//$('#cpage_num').val(_cpage+1);
		//if(console)console.log('show page ',_cpage);
		showPage();
	});
	$('#cpage_num').change(function(){
		try{
			var pg=parseInt($(this).val());
			if (pg>0 && pg<=_pages){
				_cpage=pg-1;
				//console.log('show page ',_cpage);
				showPage();
			} else {
				$('#cpage_num').val(_cpage+1);
			}
		}catch(err){$('#cpage_num').val(_cpage+1);}
	});
	$('#Back2Book').click(function(){
		Main.showPage('bookedit');
	});
    $('#add_page_btn').click(function(){
        //add one page
    	$.post('/author/addpage',{bk:_bkid},function(resp){
    		if(resp.error)alert(resp.error);else{
    			if(_pagedata)_pagedata.push(resp);else _pagedata=[resp];
    			addPages(1);
    		}
    	},'json');
    });
    $('#del_page_btn').click(function(){
        //delete last page
    	if(confirm('Are you sure to delete this page?'))
    	$.post('/author/delpage',{bk:_bkid,pg:_pagedata[_cpage].id},function(resp){
    		if(resp.error)alert(resp.error);else{
    			delete _pagedata[_cpage];
    			addPages(-1);
    		}
    	},'json');
    });
    $('#PageScript').delegate('button','click',function(){
    	var st=$('#script_txt').val().replace(/^\s\s*/, '').replace(/\s\s*$/, '').replace(/\r/g,'').replace(/\n/g,' ');
    	if(st != ''){
    		if(/^{"version":"1.0","controls":\[.+}\s*$/.test(st)){
    		$.post('/author/addscript',{bk:_bkid,pg:_pagedata[_cpage].id,sc:st},function(resp){
    			if(resp.error)alert(resp.error);else alert('Done');
    		},'json');}else alert('Invalid dynamic control.')
    	}
    });
    $('#pnote_btn').click(function(){
    	var s=$('#PageNoteText').val();//.replace(/^\s\s*/, '').replace(/\s\s*$/, '').replace(/\r/g,'').replace(/\n/g,' ');
    	if(s != ''){
    		$.post('/author/pagenote',{bk:_bkid,pg:_pagedata[_cpage].id,notes:s},function(resp){
    			if(resp.error)alert(resp.error);else alert('Done');
    		},'json');
    	}
    });
    function addPages(n){
    	_pages += n;
    	$('#sp_pages').html(_pages);
    	if(_pages>0){
    		_cpage=_pages-1;
    	}else {_cpage=0;$('#cpage_num').val('0');}
		showPage();
    }
	function showPage(){
		//if(console)console.log('show page: ',_cpage);
		if(_pages>0)
			$('#cpage_num').val(_cpage+1);
		if(_pages<=0 || _pagedata==null){
			//clear page data
			$('#div_pageimage').html('');
			$('#PageDemands').html('');
			$('#PageRewards').html('');
			$('#PageNoteText').val('');
			$('#script_txt').val('');
		}else{
			var bimg='<img src="/page/image/'+_pagedata[_cpage].id+'"/>';
			$('#div_pageimage').html(bimg);
			showItems($('#PageDemands'),_pagedata[_cpage].rq);
			showItems($('#PageRewards'),_pagedata[_cpage].rw);
			if(_pagedata[_cpage].sc){
				//TODO: render script data here
				if(console)console.log(_pagedata[_cpage].sc);
				var sct=formatObject(_pagedata[_cpage].sc);
				$('#script_txt').val(sct);
			} else $('#script_txt').val('');
			if(_pagedata[_cpage].notes){
				$('#PageNoteText').val(_pagedata[_cpage].notes);
			}else $('#PageNoteText').val('');
		}
	}
	function formatObject(o){
	    if(o)
	    switch(o.constructor){
	    case Array:
	        var buf=[];
	        for(var i=0,a;a=o[i];i++) buf.push(formatObject(a));
	        return '['+buf.join(',')+']';
	    case String: return '"'+o+'"';
	    case Number: return isFinite(o)?o.toString():null;
	    default:
	        if(typeof(o)=="object"){
	            var ar=[];
	            for(var k in o) ar.push('"'+k+'":'+formatObject(o[k]));
	            return '{'+ar.join(',')+'}';
	        } else return o.toString();
	    } else return '';
	}
	function showItems(dv,vgdata){
		var buf=[];
		for(var r in vgdata){
			buf.push('<div><img src="/mm/vg_'+r+'?v='+VGoods.version(r)+'"/><br/>'+VGoods.name(r)+'<br/><button id="rm_'+r+'">Remove</button></div>');
		}
		dv.html(buf.join(''));
	}
	$('#PageDemands').delegate('button','click',function(){
		var vgid=$(this).attr('id').substr(3);
		$.post('/author/delrequired',{bk:_bkid,pg:_pagedata[_cpage].id,vg:vgid},function(resp){
			delete _pagedata[_cpage].rq[vgid];
			showItems($('#PageDemands'),_pagedata[_cpage].rq);
		},'json');
	});
	$('#PageRewards').delegate('button','click',function(){
		var vgid=$(this).attr('id').substr(3);
		$.post('/author/delreward',{bk:_bkid,pg:_pagedata[_cpage].id,vg:vgid},function(resp){
			delete _pagedata[_cpage].rw[vgid];
			showItems($('#PageRewards'),_pagedata[_cpage].rw);
		},'json');
	});
    self.show=function(){if(_div!=null)_div.show();if(_uploader==null)initLoader();}
    self.hide=function(){if(_div!=null)_div.hide();}
    self.setBook=function(bkid,bk){
    	_bkid = bkid;
    	if(bk)_book = bk;else _book=g_books[bkid];
        $.post('/book/pages/'+bkid,function(resp){
        	if(resp.error)alert(resp.error);else{
        		//[{id:,bk:,sc:,ls:,rq:,rw:},..]
        		_pages = 0;
        		addPages(resp.length);
        		_pagedata = resp;
        		_cpage=0;
        		showPage();
        	}
        },'json');
    }
    function initLoader(){
    YAHOO.util.Event.onDOMReady(function(){
    	var uiLayer=YAHOO.util.Dom.getRegion('selectLink');
    	var overlay=YAHOO.util.Dom.get('uploaderOverlay');
    	YAHOO.util.Dom.setStyle(overlay,'width',uiLayer.right-uiLayer.left+'px');
    	YAHOO.util.Dom.setStyle(overlay,'height',uiLayer.bottom-uiLayer.top+'px');

    	YAHOO.widget.Uploader.SWFURL="http://yui.yahooapis.com/2.8.2r1/build/uploader/assets/uploader.swf";
    	_uploader=new YAHOO.widget.Uploader("uploaderOverlay");
    	_uploader.addListener('contentReady',function(){
    	    _uploader.setAllowLogging(true);
    	    _uploader.setAllowMultipleFiles(false);
    	    var ff=new Array({description:"Images",extensions:"*.jpg;*.png;*.gif"});
    	    _uploader.setFileFilters(ff); 
    	});
    	_uploader.addListener('fileSelect',function(event){
    		if(_pages < 1){
    			alert('Please add a page first');
    			return;
    		}
    	    for(var f in event.fileList){
    	        if(YAHOO.lang.hasOwnProperty(event.fileList,f)){
    	        	var sz=event.fileList[f].size;
    	        	if(sz>512*1024){alert('File too large!');return;}
    	            _fileId=event.fileList[f].id;
    	            _fileName=event.fileList[f].name;
    	        }
    	    }
    	    _progressBar=document.getElementById('progressReport');
    	    _progressBar.value='Selected '+event.fileList[_fileId].name;
    	});
    	_uploader.addListener('uploadStart',function(event){
    	    _progressBar.value='Starting upload...';
    	});
    	_uploader.addListener('uploadProgress',function(event){
    	    var prog=Math.round(100*(event['bytesLoaded']/event['bytesTotal']));
    	    _progressBar.value=prog+'% uploaded...';
    	});
    	_uploader.addListener('uploadCancel',function(){
    		if(console)console.log('upload canceled');
    	});
    	_uploader.addListener('uploadComplete',function(event){
    	    _progressBar.value='Upload complete.';
    	});
    	_uploader.addListener('uploadCompleteData',function(event){
    	    //sever_data = event.data;
    	    //console.log(event.data);
    		showPage();
    	});
    	_uploader.addListener('uploadError',function(event){
    		if(console)console.log(event);
    	    _progressBar.value='Error:'+event;
    	});
    	_uploader.addListener('rollOver',function(){
    	    YAHOO.util.Dom.setStyle(YAHOO.util.Dom.get('selectLink'),'color','#FFFFFF');
    	    YAHOO.util.Dom.setStyle(YAHOO.util.Dom.get('selectLink'),'background-color','#000000');
    	});
    	_uploader.addListener('rollOut',function(){
    	    YAHOO.util.Dom.setStyle(YAHOO.util.Dom.get('selectLink'),'color','#0000CC');
    	    YAHOO.util.Dom.setStyle(YAHOO.util.Dom.get('selectLink'),'background-color','#FFFFFF');
    	});
    	_uploader.addListener('click',function(){});
    });}
    $('#uploadLink').click(function(){upload();return false;});
   	function upload(){
   		//if(console)console.log('Uploading ',_fileId,_fileName,'cookie=',document.cookie);
   		if(_fileId == null)alert('File not selected');else
   		if(_pagedata == null)alert('No pages');else
   		if(_cpage >= _pagedata.length)alert('Not enough page, try add a page');else{
    	//if(_fileId != null && _pagedata != null && _pagedata[_cpage]){
    	    _uploader.upload(_fileId,'http://'+location.host+'/upload','POST',{bk:_bkid,pg:_pagedata[_cpage].id,ck:document.cookie});
    	}
   	}
}
function readBook(bkid){
    Main.menus.page.open(bkid);
    Main.showPage('page');
}
