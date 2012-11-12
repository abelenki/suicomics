var SuiGift = function() {
    var self=this,_myacc=null;
    var _div=genAddPanelBox('div_gift','middlebox');
    _div.append(genTitledPanel('div_giftagent','Birthday Gift Agent',''));
    _div.append(genTitledPanel('div_gfriends','My Friends and Birthdays',''));
    _div.append(genTitledPanel('div_mygifts','Birthday Gifts I created',''));
    var creategift='<form action="/gift/upload" method="post" enctype="multipart/form-data" ><table>'+
    	'<tr><td>Name of gift:</td><td><input name="gname"></td><td></td></tr>'+
    	'<tr><td>Category:</td><td><select name="gcat">'+
    		'<option value="eat">Cakes(Food,Drink)</option>'+
    		'<option value="plant">Flowers(Plants)</option>'+
    		'<option value="art">Art(Paintings,Photos)</option>'+
    		'<option value="toy">Toys(Games)</option>'+
    		'<option value="dress">Clothes</option>'+
    		'<option value="wear">Jewelry</option>'+
    		'<option value="pet">Pet</option>'+
    		'<option value="other">Other</option>'+
    		'</select></td><td></td></tr>'+
    	'<tr><td>For gender:</td><td><select name="gsex"><option value="B">Both</option><option value="F">Female</option><option value="M">Male</option></select></td><td></td></tr>'+
    	'<tr><td>Picture(640x480):</td><td><input type="file" name="gpic"></td><td></td></tr>'+
    	'<tr><td>Use my own only:</td><td><input id="use_my_own_gifts" type="checkbox" name="myown"/></td><td></td></tr>'+
    	'<tr><td colspan="3"><input type="submit" value="Submit"></td></tr>'
    	'</table></form>';
    _div.append(genTitledPanel('div_creategift','Create a Birthday Gift',creategift));
    //_div.append(genTitledPanel('div_excludes','<span class="wsleft">Excluded Friends</span><button id="excludefs_btn" style="float:right">Select to exclude</button><div style="clear:both"></div>',''));

    self.show=function(){if(_myacc==null) load();_div.show();}
    self.hide=function(){_div.hide();}
    $('#div_gift div.wpanel').hide();
    
    $('#div_mygifts').delegate('button','click',function(){
    	var gid=$(this).attr('id');
    	if(gid=='ca_apply_btn'){
    		if(imAuthor())
    			$.post('/gift/permit',function(resp){location.href='/fb/gift'},'json');
    		else{
    			$('#div_mygifts').html(authorform());
    			$('#ca_bda').val('1');
    		}
    	}else{
	    	if(confirm('Are you sure to delete this gift?'))
	    	$.post('/gift/delete/'+gid,function(resp){
	    		if(resp.error)alert(resp.error);else{
	    			$(this).parent().remove();
	    		}
	    	},'json');
    	}
    });
    $('#excludefs_btn').click(function(){
    	if($('#exf_div').length>0)return;
    	if(get_friends)get_friends(3,function(fs){
    		//f.id,f.name
    		var buf=['<div id="exf_div" style="height:300px;overflow:auto;padding:5px;border-bottom:1px solid black;">Please tick those friends not to send birthday gifts:'];
    		for(var i=0,f;f=fs[i];i++){
    			buf.push('<div><input type="checkbox" value="'+f.id+'"/>'+f.name+'</div>');
    		}
    		buf.push('<div><button id="exf_submit">Submit</button><button id="exf_cancel">Cancel</button></div></div>');
    		$('#div_excludes').prepend(buf.join(''));
    	});
    });
    $('#div_excludes').delegate('button','click',function(){
    	var id=$(this).attr('id');
    	if(id=='exf_submit'){
    		var exids = $("#exf_div input:checked").map(function() {
    			return $(this).val();
    		}).get().join();
    		if(console)console.log('selected: ',exids);
    		if(exids.length>0)
    		$.post('/gift/exclude',{ids:exids},function(resp){
    			if(resp.error)alert(resp.error);else location.href='/gift';
    		},'json');
    		else alert('No one selected');
    	}else if(id=='exf_cancel'){
    		$('#exf_div').remove();
    	}else{
    		if(confirm('Remove this friend from excluded list?'))
    			$.post('/gift/include/'+$(this).attr('id'),function(resp){
    				if(resp.error)alert(resp.error);else {$(this).parent().remove();}
    			},'json');
    	}
    });
    function load(){
    	$.post('/gift/account/'+myinfo.uid,function(resp){
    		if(resp.error)alert(resp.error);else{
//resp = {name:'Test',creator:'false',excludes:'',usemyown:'false',mygifts:['vg_28','vg_29','vg_30','vg_31','vg_32','vg_33','vg_34','vg_35'],mywrapper:'',included:4};
    			_myacc = resp;
    			if(resp.notavail){
    				var msg='<div style="text-align:center;padding:5px;font-weight:bold;">You are not registered yet to enjoy the free Birthday-Gift Agent service, register now:</div>'+
						'<div style="text-align:center;padding:4px;"><button class="bigbtn">Register</button></div>'+
    					'<ul><li>This is the <b>Birthday-Gift Agent</b>, a free service by Suinova Comics;</li>'+
    					'<li>If you are too busy like me, and often forget your friends birthdays;</li>'+
    					'<li>This agent can help to send a virtual gift on your behalf automatically;</li>'+
    					'<li>You can select friends to send or not to send to;</li>'+
    					'<li>And you can create your own special gift card, or use others;</li>'+
    					'<li>If you find it inappropriate later on, you can cancel this service any time</li></ul>';
    				$('#div_giftagent').html(msg).delegate('button','click',function(){
    					location.href='/fb/?use=gift';
    				}).parent().show();
    			}else{
    				var msg='<div style="text-align:center;padding:5px;">You have '+resp.included+' friends on the birthday tracking list.<br/>'+
    					'And you can view, update the list by adding new friends or removing some friends from the list.</div>'+
    					'<div style="text-align:center;padding:4px;"><button id="v_u_btn" class="bigbtn">View and Update</button></div>';
    				$('#div_gfriends').html(msg).delegate('button','click',function(){
    					if($(this).attr('id')=='v_u_btn')loadFriends();else editBirthday($(this).attr('id'));
    				}).delegate("input[type='checkbox']",'click',changeSelect).parent().show();
    				
    				if(resp.usemyown=='true')$('#use_my_own_gifts').attr('checked','checked');else $('#use_my_own_gifts').removeAttr('checked');
    				
    				var buf=['<table class="tabfull" style="table-layout:fixed;"><tr>'];
    				if(resp.creator=='true'){
    					$('#div_creategift').parent().show();//$('#div_creategift').show();
	    				if(typeof(resp.mygifts)!='string'){
	    					for(var i=0,g;g=resp.mygifts[i];i++){
	    						if(i>0 && i % 6==0) buf.push('</tr><tr>');
	    						var il=(g.indexOf('_')>0)?g:'bdg_'+g;
	    						buf.push('<td style="text-align:center"><img src="/mm/'+il+'" width="80" height="80"/><br/><button id="'+g+'">Delete</button></td>')
	    					}
	    				}
	    			}else{
    					buf.push('<td style="text-align:center;padding:5px;">You can apply for a creators account to upload your own gift pictures.<div style="text-align:center;padding:4px;"><button id="ca_apply_btn" class="bigbtn">Apply for a Creators Account</button></div>After submission, please wait for approval. Check your email for notification.</td>');
    				}
    				buf.push('</tr></table>');
    				$('#div_mygifts').html(buf.join('')).parent().show();
    				
    			}
    		}
    	},'json');
    }
    var _birthdays = {};//{'23434':['M','01-01'],}
    var _friends = [];
    var _loaded = 0;
    var _edited = false;
    var _bigroups = [];
    function loadFriends(){
    	_loaded = 0;
    	$('#v_u_btn').hide();
    	$.post('/gift/birthdays',function(resp){
//    		if(console)console.log('from /gift/birthdays:',resp);
//resp='{"01-01":[M123,F456],"02-12":[F11111],"01-01":[M22222]}';
    		if(resp.indexOf('error')<0){
    			//convert data
    			var re=/"[0-9\-]{5}":\[[MF,0-9]+\]/g;
    			var ms=resp.match(re);
//    		if(console)console.log('ms:',ms);
    			for(var i=0,m;m=ms[i];i++){
    				var md=m.substr(1,5);
    				var uids=m.substring(9,m.length-1).split(',');
    				if(uids.length>15) _bigroups.push([md,uids.length]);
//    				if(console)console.log(i,m,typeof(m),md,uids);
    				for(var k=0,u;u=uids[k];k++){
    					_birthdays[u.substr(1)] = [u.substr(0,1),md];
    				}
//    				if(console)console.log(_birthdays);
    			}
    			//show table
    		}
			_loaded ++;
   			if(_loaded>1){mergeFriends();showFriends();}
    	});
    	if(FB && FB.api){
//    	if(FB){
    		FB.api('/me/friends',{fields:'name,birthday,gender'},function(resp){
//    			if(console)console.log('from fb/me/friends:',resp);
//    		$.post('/gift/birthdays',function(resp){
//resp={data:[{id:12345,name:'Ted Wen',gender:'male',birthday:'09/26/1964'},{id:11111,name:'Test',gender:'female'},{id:22222,name:'Tom Hanks',birthday:'01/01'}]};
    			for(var i=0,u;u=resp.data[i];i++){
    				//[id,name,gender,birthday,included] can sort on name, birthday
    				var rec=[u.id,u.name,u.gender || '',monthday(u.birthday),false];
    				_friends.push(rec);
    			}
    			_loaded ++;
      		if(console)console.log('_loaded=',_loaded);
    			if(_loaded>1){mergeFriends();showFriends();}
    		});
    	}
    }
    function mergeFriends(){
    	for(var i=0,f;f=_friends[i];i++){
    		if(_birthdays[f[0]]){
    			var b=_birthdays[f[0]];
    			f[4]=true;
    			if(f[2]=='')f[2]=genderWord(b[0]);
    			if(f[3]=='')f[3]=b[1];
    		}
    	}
    }
    function showFriends(order){
    	if(order){
    		_friends.sort(function(a,b){
    			return (a[order]>b[order])?1:((a[order]<b[order])?-1:0);
    		});
    	}
    	var buf=['<div style="max-height:300px;overflow:auto;"><table class="tabright" style="width:90%;">'];
    	buf.push('<tr><th><button style="font-weight:bold" id="gsort_name" title="Sort by name">Name</button></th>');
    	buf.push('<th>Gender</th><th><button style="font-weight:bold" id="gsort_bday" title="Sort by birthday">Birthday</button></th>');
    	buf.push('<th>Send</th><th>Change</th></tr>');
    	for(var i=0,f;f=_friends[i];i++){
    		buf.push('<tr>');
    		buf.push('<td><a href="http://www.facebook.com/profile.php?id='+f[0]+'" target="_blank">'+f[1]+'</a></td>');
    		buf.push('<td><span id="gsp_'+f[0]+'">'+f[2]+'</span><button id="gbt_'+f[0]+'">Change</button></td>');
    		buf.push('<td id="rbd_'+f[0]+'">'+genderWord(f[3])+'</td>');
    		buf.push('<td><input type="checkbox" id="bch_'+f[0]+'"'+(f[4]?' checked="checked"':'')+'/></td>');
    		buf.push('<td><input id="bed_'+f[0]+'" value="mm-dd" maxlength="5" size="5" onfocus="javascript:if(this.value==\'mm-dd\')this.value=\'\';" onblur="javascript:if(this.value==\'\')this.value=\'mm-dd\';"/> <button id="bbt_'+f[0]+'">Change</button></td>');
    		buf.push('</tr>');
    	}
    	buf.push('</table><div style="text-align:center"><button id="bga_save" class="bigbtn">Save</div></div>');
		if(_bigroups.length>0){
			buf.push('<div>The following days have too many people, the limit is 15.<br/>');
			for(var i=0,g;g=_bigroups[i];i++){
				buf.push(g[0]+': '+g[1]+', ');
			}
			buf.push('</div>');
		}
		buf.push('</div>');
    	$('#div_gfriends').html(buf.join(''));
    }
    function changeSelect(){
    	var x=$(this).parent().parent().index();
    	_friends[x-1][4]=$(this).attr('checked');
    	_edited=true;
    }
    function editBirthday(btnid){
    	if(btnid.indexOf('bbt_')==0){
    		var id=btnid.substr(4);
    		var newbds=$('#bed_'+id).val();
    		var re=/^\d\d-\d\d$/;
    		if(!re.test(newbds)){alert('Invalid birthday, should be MM-DD like 01-31');return;}
    		var newmd=newbds.split('-');
    		var nm=parseInt(newmd[0],10),nd=parseInt(newmd[1],10);//if(console)console.log(newmd,nm,nd);
    		if(isNaN(nm) || nm<=0 || nm>12){alert('Invalid month:'+nm);return;}
    		if(isNaN(nd) || nd<=0 || nd>daysofmonth(nm)){alert('Invalid day:'+nd);return;}
    		$('#rbd_'+id).html(newbds);
    		var x=$('#'+btnid).parent().parent().index();
    		_friends[x-1][3]=newbds;
    		_edited = true;
    	} else if (btnid.indexOf('gbt_')==0){
    		var id=btnid.substr(4);
    		var g=$('#gsp_'+id).html();
    		if(g=='male')g='female';else g='male';
    		$('#gsp_'+id).html(g);
    		var x=$('#'+btnid).parent().parent().index();
    		_friends[x-1][2]=g;
    		_edited = true;
    	} else if (btnid=='bga_save'){
    		if(_edited){
    			_edited = false;
    			saveFriends();
    		} else alert('No change');
    	} else if (btnid=='gsort_name'){
    		showFriends(1);
    	} else if (btnid=='gsort_bday'){
    		showFriends(3);
    	}
    }
    function saveFriends(){
    	var ar={};
    	var cs = 0;
    	for(var i=0,f;f=_friends[i];i++){
    		if(f[4]){
    			cs ++;
    			var g=(f[2].length>0)?f[2].substr(0,1).toUpperCase():'F';
	    		if(ar[f[3]])
	    			ar[f[3]].push(g+f[0]);
	    		else
	    			ar[f[3]]=[g+f[0]];
    		}
    	}
    	var st=[];
    	for(var a in ar){
    		st.push('"'+a+'":['+ar[a].join(',')+']');
    	}
    	if(st.length<1)return;
    	var s='{'+st.join(',')+'}';
//    	if(console)console.log(s);
    	$.post('/gift/birthdays',{bds:s,n:cs},function(resp){
    		if(resp.error)alert(resp.error);else location.href='/fb/gift';
    	},'json');
    }
    function daysofmonth(m){
    	var long=[1,3,5,7,8,10,12];
    	if(long.indexOf(m)>=0)return 31;
    	if(m==2)return 29;else return 30;
    }
    function monthday(birthday){//format: 01/12/1999
    	if (birthday){
    		return birthday.substr(0,5).replace('/','-');
    	}else return '';
    }
    function genderWord(g){
    	if(g=='F')return 'female';else if(g=='M')return 'male';else return g;
    }
}
