function $(v) { return(document.getElementById(v)); }
function $S(v) { return($(v).style); }
function agent(v) { return(Math.max(navigator.userAgent.toLowerCase().indexOf(v),0)); }
function isset(v) { return((typeof(v)=='undefined' || v.length==0)?false:true); }
function XYwin(v) { var z=agent('msie')?Array(document.body.clientHeight,document.body.clientWidth):Array(window.innerHeight,window.innerWidth); return(isset(v)?z[v]:z); }

function sexyTOG() { document.onclick=function(){ $S('sexyBG').display='none'; $S('sexyBOX').display='none'; document.onclick=function(){}; }; }
function sexyBOX(v,b) { setTimeout("sexyTOG()",100); $S('sexyBG').height=XYwin(0)+'px'; $S('sexyBG').display='block'; $('sexyBOX').innerHTML=v+'<div class="sexyX">(Bitte auﬂerhalb der Hinweisbox klicken)'+"<\/div>"; $S('sexyBOX').left=Math.round((XYwin(1)-b)/2)+'px'; $S('sexyBOX').width=b+'px'; $S('sexyBOX').display='block'; }

