/**
 * Home page content holder.
 */
var SuiHome = function() {
    var self=this,_div=$('#div_home'),_books=null,_recommends,_newbooks,_myreads,_mybooks,_promoted;
    //console.log('SuiHome(),_div=',_div);
    self.show = function() {
        if(_books==null)
            loadit();
        _div.show();
    }
    self.hide = function() {
        _div.hide();
    }
    function loadit() {
        if(typeof(g_books)!='undefined'){
            _books = g_books;
            _recommends = recommended;
            _newbooks = newbooks;
            _myreads = myreads;	//{"bkid":["time",pg#,1]
            //_mybooks = mybooks;
            _promoted = promoted;
            if(_myreads){
            	var bks = [];
            	for (var r in _myreads)bks.push(r);
            	if(bks.length>0)
            		BookShelf.showbooks(bks,'myreads');
            }
            //if(_mybooks.length > 0){
            //    BookShelf.showbooks(_mybooks,'mybooks');
            //}
            if(_newbooks.length > 0){
            	BookShelf.showbooks(_newbooks,'newbooks');
            }
            if(_recommends.length > 0){
            	BookShelf.showbooks(_recommends,'recommended');
            }
        }else
            alert('Book data need to be loaded here');
    }
}

function showHeader(yes){
    if(yes){
        $('#header').hide();
        $('#loginbox').hide();
        $('#sheader').show();
        $('#newsbar').prepend($('#hg_news'));
    }else{
        $('#sheader').hide();
        $('#header').show();
        $('#loginbox').show();
        $('#newsbars').prepend($('#hg_news'));
    }
}
/**
 * Main routine with menu button handlers and switcher
 */
var Main = {
    menus:{
        home:new SuiHome(),
        authors:new SuiAuthors(),author:new SuiAuthor(),
        readers:new SuiGalleries(),gallery:new SuiGallery(),
        forums:new SuiForums(),post:new SuiPost(),	//review:new SuiStory(),
        market:new SuiMarket(),itemedit:new SuiItemEdit(),
        book:new SuiBook(),page:new SuiPage(),bookedit:new SuiBookEdit(),
        pagedit:new SuiPageEdit(),quest:new SuiQuest(),
        gift:new SuiGift()
        },
    current:null,
    init:function(){
        Main.current=Main.menus.home;
        NoticeBoard.init();
        $('#logo,#slogo').click(function(){location.href='/';});
        $('#login_go').click(function(){
        	var tgt=$('#login_options').val();
        	location.href='/'+tgt+'/';
        });
        $('.menubar div').click(function(){
            var b=$(this).attr('id');
        	if( $('#intro_page').is(':visible') ) {
        		$('#intro_page').hide();$('#div_main').show();
        	}
            if (b && b.indexOf('_')==3){
            	b = b.substr(4);
                if(b=='authors' && myinfo['role'] && myinfo['role']=='A')
                    Main.showPage('author');
                else if(b=='readers' && myinfo['role']){
                	Main.menus.gallery.setUser(myinfo['uid']);
                    Main.showPage('gallery');
                }else
                    Main.showPage(b);
            }
        });
        //$('#sbtns img').click(function(){Main.showPage($(this).attr('id').substr(4));});
        $('#pgbuttons').delegate('button','click',function(){
            var bkid=$(this).attr('name');
            var func=$(this).attr('id').substr(6);  //pmbtn_stories
            if(bkid=='') return;
            if(func=='open') openBook(bkid);
            else if(func=='market') {Main.menus.market.setBook(bkid);Main.showPage(func);}
        });
        $('.btn img').mouseover(function(){
            $(this).css('margin','1px 6px 1px 4px');
        }).mouseout(function(){
            $(this).css('margin','2px 5px 0px 5px');
        }).mousedown(function(){
            $(this).css('margin','2px 5px 0px 5px');
        });
        if(pageview.indexOf('book')==0){
        	openBook(pageview.substr(5));//book.bkid
        }else
        	Main.showPage(pageview || 'home');
        fillGenres();
        init_selected();
    	$('#intro_box').delegate('div','click',function(){
    		var url='/html/'+$(this).attr('id').replace('_','.');
    		location.href=url;
    	});
        $('#info_switch').click(function(){
        	$('#intro_box').toggle('slow');
        	//setTimeout(function(){$('#intro_box').hide('slow');},1000*10);
        });
        setTimeout(function(){$('#intro_box').hide('slow');},1000*10);
        if(FB && FB.Canvas){
        	$('body').css('overflow','hidden');
        	FB.Canvas.setAutoResize();
        } else {
        	$('#btn_gift').hide();
            if($('#login_go').length<=0){
        	$('#lb1').append('<!--<button id="edit_profile_btn">Edit</button>--> <button id="logout_btn">Logout</button>');
            if(myinfo['uid']){
                //$('#edit_profile_btn').click(editProfile);
                $('#logout_btn').click(function(){
                    $.post('/logout',function(resp){
                    	location.href='/';
                    });
                });
            }}
            $('body').css('background-color','#816998');
        }
        $('#intro_page').delegate('img','click',function(){
            //$(this).hide();$('#div_main').show();
            var id=$(this).attr('id');
            if(id=='tour_btn') {$('#intro_page').hide();$('#div_main').show();Main.menus.book.setBook('36001');Main.menus.page.setBook('36001');Main.showPage('page');}
            else if(id=='enter_btn'){$('#intro_page').hide();$('#div_main').show();}
            //$('#div_main').append($('<div id="read_prompt">Please read the demo books to see how it works.</div>'));
            //setTimeout(function(){$('#read_prompt').remove();},4000);
        });
        //if(myinfo.uid=='fb_669391906' || myinfo.uid=='fb_1464710918')$('#bg_btn').show();
        /*$('#bg_btn').click(function(){
        	if( $('#intro_page').is(':visible') ) {
        		$('#intro_page').hide();$('#div_main').show();
        	}
        	Main.showPage('gift');
        });*/
    },
    showPage:function(mn){
        if(Main.current!=null)Main.current.hide();
        //if(typeof(mn)=='string')mn=Main.menus[mn];
        showHeader(mn=='page');
        Main.current=Main.menus[mn];
        Main.current.show();
    },
    end:null
}

var g_genres = {};
function show_genre(){
	var genre = $(this).html();
	$('#books_by_genre').prev().html('Books by Genre - '+genre);
    if (g_genres[genre]){
        //render_genre(g_genres[genre]);
    	BookShelf.showbooks(g_genres[genre],'books_by_genre');
    }else
    $.post('/home/books/genre/'+genre,function(resp){
        //{'genre':'xxx','books':[123,...]}
        if(resp.error)alert(resp.error);else{
            g_genres[genre] = resp.books;
            //render_genre(resp);
            BookShelf.showbooks(resp.books,'books_by_genre');
        }
    },'json');
}
function fillGenres(){
	if(genres){
		var buf=[];
		var ln=genres.length;
		for(var i=0;i<ln;i++){
			var g=genres[i];//[['fantasy',5,[234,23,4,1,5]],..]
			if(i & 1 == 0) buf.push('<tr>');
			buf.push('<td style="text-align:left;font-size:9pt;"><a href="#bkbygr">'+g[0]+'</a></td><td style="text-align:right;font-size:9pt;">'+g[1]+'</td>');
			if(i & 1 == 1) buf.push('</tr>');
		}
		if(ln & 1 == 1) buf.push('<td></td></tr>');
		$('#div_genres').html('<table class="linedtab tableft">'+buf.join('')+'</table>').delegate('a','click',show_genre);
	}
}

function editProfile(){
	if($('#div_myprofile').length>0) return;
$('<div id="div_myprofile"><div>Name: <input id="mynewname" name="uname" value="'+$('#myuname').html()+'"/> Email: <input id="myemail" name="email"/> <button id="save_uname">Save</button> <button id="cancel_uname">Close</button></div></div>').insertAfter('#loginbox');
$('#save_uname').click(function(){
    var newname=$('#mynewname').val();
    if(newname == '')alert('Name cannot be empty');else
    if(newname.length > 16)alert('Name too long (3-16)');else
    if(newname != $('#myuname').html()){
        $.post('/home/newname',{name:newname,email:$('#myemail').val()},function(resp){
            if(resp.error)alert(resp.error);else{
                $('#myuname').html(newname);
            }
            $('#div_myprofile').remove();
        });
    }
});
$('#cancel_uname').click(function(){
    $('#div_myprofile').remove();
});
}

function init_selected(){
    if (typeof(promoted)!='undefined')
        showPromoted(promoted);
}
function showPromoted(bkid){
    if(g_books[bkid]){
        var bk = g_books[bkid];
        $('#promotetitle').html(bk.title);
        var img='/mm/bk_'+bkid+'?v='+bk.version;
        $('#promotelogo').html('<img style="cursor:pointer" src="'+img+'" width="240"/>').click(function(){openBook(bkid);});
        $('#pgnote').html(bk.intro);
        $('#pgbuttons button').attr('name',bkid);
    }
}
