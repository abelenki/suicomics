#global variable dict to be used by Templite parser
global_vars = {'LOGIN':'''
  <div id="lb1">Login via:
    <select id="login_options"><option value="gg">Google</option><option value="fb">Facebook</option></select> 
    <button id="login_go">Go</button>
  </div>''',
  'WELCOME':'''<div id="lb1">Welcome back, <span id="myuname">{{ uname }}</span>!&nbsp; &nbsp; </div>''',
  'FB_SHARE':'<img id="info_switch" title="Show/hide information box" style="cursor:pointer" src="/img/info.png"/>',
  'OTHER_SHARE':'''Tell friends:
    <a name="fb_share" title="Share on Facebook" type="button" href="http://www.facebook.com/sharer.php">Share</a><script src="http://static.ak.fbcdn.net/connect.php/js/FB.Share" type="text/javascript"></script>
    <a title="Post to Google Buzz" class="google-buzz-button" href="http://www.google.com/buzz/post" data-button-style="small-button" data-locale="en_GB" data-url="http://suicomics.appspot.com"></a>
<script type="text/javascript" src="http://www.google.com/buzz/api/button.js"></script>
    <a href="javascript:void(window.open('http://www.myspace.com/Modules/PostTo/Pages/?u='+encodeURIComponent(document.location.toString()),'ptm','height=450,width=440').focus())">
    <img src="http://cms.myspacecdn.com/cms/ShareOnMySpace/small.png" border="0" align="absmiddle" style="border-right:1px solid gray;border-bottom:1px solid gray;" alt="Share on MySpace" /></a>
    <a title="Share on Twitter" href="http://twitter.com/?status=Come+join+me+at+http%3a%2f%2fquicart.com" target="_blank"><img border="0" align="absmiddle" src="http://twitter-badges.s3.amazonaws.com/t_mini-b.png" style="border-bottom:2px solid #09336A;border-right:2px solid #09336A;"/></a>
    <img id="info_switch" title="Show/hide information box" style="cursor:pointer" src="/img/info.png"/>
  ''',
  'MYBOOKS':'''
<div class="wpanel">
    <div class="wtitle">My Books</div>
    <div id="mybooks" class="wtable">
    </div>
</div>
''',
  'MYREADS':'''
<div class="wpanel">
    <div class="wtitle">My Reading List</div>
    <div id="myreads" class="wtable">
    </div>
</div>
''',
  'LOAD_FB':'''<div id="fb-root"></div>
<script type="text/javascript" src="http://connect.facebook.net/en_US/all.js"></script>
<script type="text/javascript">
    FB.init({appId: '179008415461930', status: true, cookie: true, xfbml: true});
    FB.Event.subscribe('auth.login',function(resp){/*window.location.reload();*/});
</script>
''',
  'NEW_STORY':'''
<div class="wpanel" id="newstory">
    <div class="wtitle">New Story</div>
    <div><form id="gameinform" enctype="multipart/form-data" action="/stories/addstory" method="post">
        <table style="margin:5px auto;">
            <tr><td>Title:</td><td><input type="text" name="title"/></td></tr>
            <tr><td>Game:</td><td><select name="game">{{mygameoptions}}</select></td></tr>
            <tr><td>Content:</td><td><textarea name="content" style="height:200px;"></textarea></td></tr>
            <tr><td colspan="2" style="text-align:center;"><input type="submit" value="Submit" style="width:120px"/></td></tr>
        </table>
    </form></div>
</div>
''',
  'NEW_ITEM':'''
<div class="wpanel" id="newitem">
    <div class="wtitle">New Item</div>
    <div>
    <form id="gameinform" enctype="multipart/form-data" action="/market/upload" method="post">
        <table style="margin:5px auto;">
            <caption>Create a New Virtual Goods Item</caption>
            <tbody>
                <tr>
                    <td>Unique name:</td>
                    <td><input type="text" name="itemkey" width="40"/></td>
                    <td class="note">6 to 16 letters and digits</td>
                </tr>
                <tr>
                    <td>Display name:</td>
                    <td><input type="text" name="itemname" width="40"/></td>
                    <td class="note">2 to 10 characters</td>
                </tr>
                <tr>
                    <td>Game:</td>
                    <td><select name="gamekey">{{ mygameoptions }}</select></td>
                    <td class="note"></td>
                </tr>
                <tr>
                    <td>Price:</td>
                    <td><input type="text" name="price" width="40"/></td>
                    <td class="note">Price for this item</td>
                </tr>
                <tr>
                    <td>Display:</td>
                    <td><select name="display"><option value="True">Yes</option><option value="False">No</option></select>
                    <td class="note">Display on public market or not</td>
                </tr>
                <tr>
                    <td>Description:</td>
                    <td><textarea name="note" width="40"></textarea></td>
                    <td class="note">100 characters.</td>
                </tr>
                <tr>
                    <td>Logo image:</td>
                    <td><input name="logofile" id="logofile" type="file"/></td>
                    <td class="note">80x80 pixels jpg, png file</td>
                </tr>
                <tr>
                    <td colspan="3" style="text-align:center"><input name="submit" type="submit" value="Submit" style="width:120px"/></td>
                </tr>
        </table>
    </form>
    </div>
</div>
''',
  'NEW_COMMENT':'''
    <div id="new_comment">
        <form id="commentform" enctype="multipart/form-data" action="/stories/addcomment" method="post">
        <input type="hidden" name="story" value="{{ skey }}"/>
        <div>Your comment:</div>
        <div><textarea name="comment"></textarea></div>
        <div><input type="submit" value="Submit"/></div>
        </form>
    </div>
''',
  'FB_LIKE_BTN':'''<div style="clear:both;background:none;border:0;overflow:auto;">
<iframe id="fb_like" src="http://www.facebook.com/plugins/like.php?href=http%3A%2F%2Fapps.facebook.com%2Fsuinova&amp;layout=button_count&amp;show_faces=true&amp;width=45&amp;action=like&amp;colorscheme=light&amp;height=21" scrolling="no" frameborder="0" style="border:none; overflow:hidden; width:45px; height:21px;" allowTransparency="true"></iframe>
</div>
''',
  'INTRO_BOX':'''<div id="intro_box"><div id="readers_html">&nbsp;</div><div id="gallery_html">&nbsp;</div><div id="suicomics_html">&nbsp;</div><div id="quest_html">&nbsp;</div><div id="creators_html">&nbsp;</div></div>''',
  'NOTHING':''
}

#print global_vars
