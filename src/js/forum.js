/**
 * Forums list and posts of one of the forums.
 */
var SuiForums = function(){
    var self=this,_forums=null,_cforum=0;

    var _div=genAddPanelBox('div_forums','middlebox');
    _div.append(genTitledPanel('forum_list','<span class="wsleft">Forums</span><span id="forum_showhide" style="font-size:10pt;float:right;cursor:pointer">[-]</span><div style="clear:both"></div>',''));
    _div.append(genTitledPanel('post_list','<span id="forum_title"></span><button id="new_post" style="float:right">New Post</button>',''));
    $('#forum_list').delegate('a','click',function(){
    	$('#forum_list').hide();$('#forum_showhide').html('[+]');
    	loadPosts($(this).attr('id'));
    });
    $('#new_post').click(function(){
    	//console.log('new post');
    	Main.menus.post.newPost(_cforum);
    	Main.showPage('post');
    });
    $('#post_list').delegate('a','click',function(){
    	//console.log('click post,',$(this).attr('id'));
    	var pid=$(this).attr('id');
    	var f=_forums[0];
    	for(var i=0,f;f=_forums[i];i++)if(f.id==_cforum)break;
    	for(var i=0,p;p=f.postlist[i];i++){
    		if(p.id == pid){
    			Main.menus.post.loadPost(p.id,p.subject,p.author,p.time);
    			Main.showPage('post');
    			break;
    		}
    	}
    });
    $('#forum_showhide').click(function(){
    	if($(this).html()=='[-]'){
    		$(this).html('[+]');
    		$('#forum_list').hide();
    	}else{
    		$(this).html('[-]');
    		$('#forum_list').show();
    	}
    });
    self.show=function(){if(_forums==null)load();_div.show();}
    self.hide=function(){_div.hide();}
    function load(){
        $('#forum_list').html('Loading forums ...');
        //console.log('about to call server');
        $.post('/home/forums',function(resp){
            //{'forums':[{id:2,forum:'',note:'',group:2,order:2,posts:0,moderators:''},..],'posts':[{id:1,author:'',time:'',subject:''},..]}
            if(resp.error){
                alert(resp.error);
            }else if (resp.forums){
                _forums=resp.forums;
            	_forums.sort(function(a,b){return (a.group==b.group)?(a.order-b.order):(a.group-b.group);});
                var fms=[],grp=0;
                for(var i=0,f;f=_forums[i];i++){
                    if(grp!=f.group){
                    	grp=f.group;
                    	fms.push('<tr><td class="sep_line" colspan="4"></td></tr>');
                    }
                    fms.push('<tr><td></td><td><a id="'+f.id+'" href="#">'+f.forum+'</a></td><td>'+f.note+'</td><td>'+f.posts+'</td></tr>');
                }
                $('#forum_list').html('<table class="forum_tab tabfull"><thead><tr><th></th><th>Forum</th><th>Description</th><th>Posts</th></tr></thead><tbody>'+fms.join('')+'</tbody></table>');
                _cforum = _forums[0].id;
                _forums[0]['postlist'] = resp.posts;
                showPosts(_forums[0]);
            }
        },'json');
    }
    function loadPosts(fid,posts){
    	for(var i=0,f;f=_forums[i];i++)if(f.id==fid){
    		_cforum = fid;
    		if(posts){
    			f['postlist'] = posts;
    			showPosts(f);
    		}else if (f.postlist){
    			showPosts(f);
    		}else{
    			$.post('/home/posts/'+fid,function(resp){
    				if(resp.error)alert(resp.error);else {
    					f['postlist'] = resp;
    					showPosts(f);
    				}
    			},'json');
    		}
    		break;
    	}
    }
    self.addPost=function(fid,post){ //post={id:'',author:':',time:'',subject:''}
    	for(var i=0,f;f=_forums[i];i++)if(f.id==fid){
    		if(f['postlist'])f['postlist'].push(post);else f['postlist']=[post];
    		showPosts(f);
    		break;
    	}
    }
    function showPosts(f){
    	$('#forum_title').html(f.forum);
    	var ps=[];
    	for(var i=0,p;p=f.postlist[i];i++){
    		ps.push('<tr><td><a href="#" id="'+p.id+'">'+p.subject+'</a></td><td>'+genAuthorList([p.author])+'</td><td>'+p.time+'</td></tr>')
    	}
    	$('#post_list').html('<table class="post_tab tabfull">'+ps.join('')+'</table>'); //TODO: pagination here
    }
}
/**
 * SuiPost page holder.
 */
var SuiPost = function(){
    var self=this,_forum=null;
    var _div=genAddPanelBox('div_post','middlebox');
    _div.append('<div style="padding:1px 5px;font-size:10pt;" id="back_to_forums"><a href="#">Forums</a> - <a href="#" id="SuiPost_forum">General Discussion</a></div>');
    $('#back_to_forums').delegate('a','click',function(){
    	//console.log('Back to SuiForums page');
    	Main.showPage('forums');
    });
    _div.append(genTitledPanel('SuiPost_post','<span id="SuiPost_title"></span>',''));
    _div.append(genTitledPanel('SuiPost_cmt','Comments',''));
    $('#SuiPost_post').delegate('button','click',function(){
    	//console.log('Post_submit button clicked, TODO: submit post for _forum');
    	var tit=$.trim($('#post_title_input').val());
    	if(tit==''){alert('Empty title');return;}
    	if(tit.length>128){alert('Title too long(>128)');return;}
    	var txt=$.trim($('#post_cnt_input').val());
    	if(txt==''){alert('Empty content');return;}
    	if(txt.length>1024){alert('Content too long(>1024)');return;}
    	$.post('/home/newpost',{frm:_forum,sub:tit,cnt:txt},function(resp){
    		if(resp.error)alert(resp.error);else{
    			Main.menus.forums.addPost(_forum,resp);
    			Main.showPage('forums');
    		}
    	},'json');
    });
    self.show=function(){_div.show();};
    self.hide=function(){_div.hide();};
    self.newPost=function(fid){
    	_forum = fid;
    	$('#SuiPost_title').html('New Post');
    	$('#SuiPost_post').html('<div><input type="text" id="post_title_input"/></div><textarea id="post_cnt_input"></textarea></div><div><button id="post_submit">Submit</button></div>');
   		$('#SuiPost_cmt').parent().hide();
    }
    self.loadPost=function(pid,subject,author,time){
        $('#SuiPost_post').html('Loading story...');
        $.post('/home/post/'+pid,function(resp){
            var st = resp.replace(/[\r\n]/g,' ');
            resp = $.parseJSON(st);
            $('#SuiPost_cmt').html('');
            if(resp.error){
                alert(resp.error);
            }else{
                //{post,author,content,comments:[comment0,..commentN]
                var cnt = resp.cnt;
                var cmts = resp.cmts;
                //_more=resp.more;
                $('#SuiPost_title').html(subject);
                var st='<div style="color:gray;font-size:10pt;margin:3px ;"><span>By: '+genAuthorList([author])+'</span><span style="float:right;">'+time+'</span></div><div>'+cnt+'</div>';
                //console.log(st);
                $('#SuiPost_post').html(st);
                var buf=[];
                for(var i=0,cs;cs=cmts[i];i++){
                    var n1 = cs.indexOf(':'),n2=cs.indexOf('@'),n3=cs.indexOf(']');	//[uid:uname@time]comment..
                    var c = {aname:cs.substring(n1+1,n2),comment:cs.substr(n3+1),time:cs.substring(n2+1,n3)};
                    buf.push('<div><span style="color:gray;">By: '+c.aname+'</span><p>'+c.comment+'</p></div>');
                }
                if(buf.length>0) $('#SuiPost_cmt').html(buf.join('')).show();
                //if(_more!=''){}
                var newcmt='<div id="div_newcomment" style="display:none">Leave your comment here:<div><textarea id="newcomment"></textarea></div><button id="enter_newcomment">Submit</button></div>';
                $('#SuiPost_cmt').append(newcmt);
                if($('#lb1').html().indexOf('Login')<0)$('#div_newcomment').show();
                $('#enter_newcomment').click(function(){
                    if(console) console.log('Clicked enter_newcomment');
                    var txt=$('#newcomment').val();
                    if(txt.length<1)alert('Cannot be empty');else
                    if(txt.length>200)alert('Text too long (>200 chars)!');else{
                        if(txt.indexOf('<')>=0){
                            txt=txt.replace('<','&lt;').replace('&lt;p>','<p>');
                            $('#newcomment').val(txt);
                        }
                        //if(console)console.log('About to send to /stories/newcomment');
                        $.post('/home/newcomment',{p:pid,cmt:txt},function(resp){
                            if(resp.error)alert(resp.error);else{
                                $('<div><span style="color:gray;">By: me</span><p>'+txt+'</p></div>').insertBefore($('#div_newcomment'));
                                //$('#div_newcomment').insertBefore($('<div><span style="color:gray;">By: me</span><p>'+txt+'</p></div>'));
                                $('#newcomment').val('');
                            }
                        },'json');
                    }
                });
            }
        });
    }
}
