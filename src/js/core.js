if( typeof window.console == 'undefined'){
    window.console = {
        log:function(){}
    };
}
/**
 * Rollover banner text to display news.
 */
var NoticeBoard = {
	news: ['Suinova Comics is a platform for comic fans and creators',
		'<span style="color:#0E009C;">Please read the demo books to see how this works</span>',
		'Suicomics is short for Suinova Comics',
		'Not a comics fan? why not use our birthday gift agent?',
		'No download, no subscription fee, like free games',
		'Serious readers: buy virtual goods, not the book',
		'Buy items either on market page or inside the book',
		'Send unused items to a friend as gifts',
		'Sudos <img src="/img/sb20.png"> is the virtual currency of Suicomics',
		'Exchange more Sudos using PayPal, Google Check, etc',
		'Are you a writer/artist? Apply for an authorship',
		'Self-publish your comic book, manga and graphic novels',
		'Artists/writers are welcome to join Suinova Comics'
        ],
	which: -1,
	mgtop: 18,
	dvn: null,
	init: function(){
		NoticeBoard.dvn = $('#hg_news')[0];
		if (typeof(gnews)!='undefined' && gnews.length > 0) NoticeBoard.news = NoticeBoard.news.concat(gnews);
		/*NoticeBoard.shuffle();*/
		setTimeout('NoticeBoard.start()',1000);
	},
    add: function(msg){
        NoticeBoard.news.push(msg);
    },
	start: function(){
		NoticeBoard.mgtop = 18;
		NoticeBoard.which ++;
		if (NoticeBoard.which >= NoticeBoard.news.length) NoticeBoard.which = 0;
		$(NoticeBoard.dvn).html(NoticeBoard.news[NoticeBoard.which]);
		NoticeBoard.dvn.style.marginTop = NoticeBoard.mgtop + 'px';
		setTimeout('NoticeBoard.mup()',10);
	},
	mup: function(){
		NoticeBoard.mgtop --;
		if (NoticeBoard.mgtop <= 0){
			NoticeBoard.mgtop = 0;
			setTimeout('NoticeBoard.mout()',5000);
		}else
			setTimeout('NoticeBoard.mup()',100);
		NoticeBoard.dvn.style.marginTop = NoticeBoard.mgtop + 'px';
	},
	mout: function(){
		NoticeBoard.mgtop --;
		if (NoticeBoard.mgtop > -18)
			setTimeout('NoticeBoard.mout()',100);
		else
			setTimeout('NoticeBoard.start()',10);
		NoticeBoard.dvn.style.marginTop = NoticeBoard.mgtop + 'px';
	},
	shuffle: function(){
		//var o = NoticeBoard.news;
		//for(var j, x, i = o.length; i; j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
        NoticeBoard.news.sort(function(){return 0.5-Math.random()});
	}
}
function centercss(me){
    return {top:'50%',left:'50%',
    'margin':'-'+(me.height()/2)+'px 0 0 -'+(me.width()/2)+'px',
    background:'#FDFFEC url(/img/ybar.gif) repeat-x',border:'1px solid #FF7200',padding:'10px'};
}
/**
 * Profile object - current logged in user
 */
Profile = function(){
    var self = this,uid = "",name = "",pts = 0,role='R';
    attributes = {};
    properties = {};
    
    self.reload = function(uid){
        if(console)console.log('>>TODO: reload a user by uid');
    }
    self.setProperty = function(itm,qty){
        if(qty <= 0){
            if(properties[itm])
                delete properties[itm];
        } else {
            properties[itm] = qty;
        }
        //TODO: update View here
        if(console)console.log('>>TODO: Update property view here');
    }
}
Viewer = new Profile(); //me
//Owner = new Profile();  //owner of page seen by Viewer
/**
 * Contacts or Friends of viewer.
 */
Friends = {
    list: [/*{"uid":"","name":"","picture":""}*/],
    reload: function(uid){
        if(console)console.log('>>TODO: reload viewers friends');
    }
}


function genAddPanelBox(id,cls){
    return $('<DIV id="'+id+'" class="'+cls+'" style="display:none"></div>').appendTo('#div_main');
}
function genTitledPanel(id,titl,cnt){
    return $('<div class="wpanel"><div class="wtitle">'+titl+'</div><div style="overflow:hidden;padding:5px;clear:both;" id="'+id+'">'+cnt+'</div></div>');
}
function imReader(){
	return (myinfo['role'] && myinfo.role=='R');
}
function imAuthor(){
	return (myinfo['role'] && myinfo['role']=='A');
}
function imApplied(){
	return (myinfo['role'] && myinfo.role=='a');
}
function imAuthorOf(bk){
	if(myinfo.uid){
		for(var i=0,a;a=bk.authors[i];i++)
			if(a.indexOf(myinfo.uid)>=0) return true;
	}
	return false;
}

function genreselect(){
    if(genres){
        var buf=[];
        for(var i=0,g;g=genres[i];i++){
            buf.push('<option value="'+g[0]+'">'+g[0]+'</option>');
        }
        return buf.join('');
    }
    return '';
}
function formatParagraph(txt){
    if(txt.indexOf('<li>')>=0){
        txt = txt.replace(/<\/li>/g,'\n').replace(/<\/?[uli]+>/g,'');
    }
    if(txt.indexOf('<p>')>=0){
        txt = txt.replace(/<\/p>/g,'\n').replace(/<p>/g,'');
    }
    return txt;
}

/*function loadall(){
	var mds=['author','market','gallery','gift','forum'];
	for(var i=0,m;m=mds[i];i++) $.getScript('/js/'+m+'.js',function(){
		//if(console)console.log($(this)+' loaded');
	});
	$.getScript("/js/book.js",function(){
//		if(console)console.log('book loaded');
		$.getScript('/js/home.js',function(){
//			if(console)console.log('home loaded');
			if(Main)Main.init();else setTimeout(function(){Main.init();},500);
		});
	});
}*/
//loadall();	//getScript not stable on all browsers 
