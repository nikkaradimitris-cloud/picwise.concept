"""The search page's own script, written into each page (`reference._SEARCH_SCRIPT`);
moved here word for word from `reference.py` in the clean-up of 2026-11-12."""
from __future__ import annotations

# Step 4 (owner, 2026-10-16): the scanning screen, suggestions as the buyer types, and
# the microphone. Plain JavaScript, no library, and only additions: without it the box
# is a plain form and the search works as before (docs/LANDING_PAGE_SPEC.md).
# - The scanning screen shows on a search or on "More", with the counts the server
#   wrote into the page, and says nothing the browser cannot see happening.
# - The suggestions are fetched once, on the first focus, and matched in the browser.
# - The microphone shows only where the browser can listen; the search starts when
#   the buyer stops speaking (owner, 2026-10-17).
_SEARCH_SCRIPT = r"""
(function(){
"use strict";
var form=document.querySelector(".pw-search-shell");
if(!form){return;}
var input=form.querySelector(".pw-search-input");
var list=document.getElementById("pw-suggest-list");
var ghostTyped=document.getElementById("pw-ghost-typed");
var ghostRest=document.getElementById("pw-ghost-rest");
var scan=document.getElementById("pw-scan");
var scanText=document.getElementById("pw-scan-text");
var mic=document.getElementById("pw-mic");
if(!input||!list||!ghostTyped||!ghostRest){return;}
function scanFor(q){
  if(!scan||!scanText||!q){return;}
  var products=scan.getAttribute("data-products");
  var shops=scan.getAttribute("data-shops");
  var quoted="\u201c"+q+"\u201d";
  scanText.textContent=(products&&shops)
    ?"Searching "+products+(products==="1"?" product":" products")+" from "+shops+(shops==="1"?" shop":" shops")+" for "+quoted+"\u2026"
    :"Searching the shops connected to PicWise for "+quoted+"\u2026";
  scan.hidden=false;
}
window.addEventListener("pageshow",function(){if(scan){scan.hidden=true;}});
form.addEventListener("submit",function(){
  var q=input.value.trim();
  closeList();
  if(q){scanFor(q);}
});
var more=document.querySelector(".pw-more-button");
if(more){more.addEventListener("click",function(){scanFor(input.defaultValue.trim());});}
(function(){
  // The words of a search, kept on the server to measure the search (owner, 2026-11-07;
  // picwise_app.search_log): only from a browser, only a search's first page.
  var q=input.defaultValue.trim();
  var path=location.pathname;
  if(!q||!window.fetch||(path!=="/search"&&path!=="/results")||/[?&](shown|assist)=/.test(location.search)){return;}
  try{fetch("/searched?q="+encodeURIComponent(q),{cache:"no-store",credentials:"omit",keepalive:true}).catch(function(){});}catch(e){}
})();
function norm(s){
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase()
    .replace(/\u03c2/g,"\u03c3").replace(/\s+/g," ");
}
var words=null,keys=null,loading=false,shown=[],active=-1;
function load(){
  if(words||loading||!window.fetch){return;}
  loading=true;
  fetch("/suggest.json").then(function(r){return r.ok?r.json():{};}).then(function(d){
    words=(d&&d.suggestions)||[];
    keys=words.map(norm);
    if(document.activeElement===input){update();}
  }).catch(function(){words=[];keys=[];});
}
function setGhost(typed,rest){
  ghostTyped.textContent=typed;
  ghostRest.textContent=rest;
}
function closeList(){
  list.hidden=true;
  list.textContent="";
  shown=[];
  active=-1;
  input.setAttribute("aria-expanded","false");
  input.removeAttribute("aria-activedescendant");
}
function update(){
  var raw=input.value;
  var q=norm(raw).replace(/^ /,"");
  setGhost("","");
  if(!words||!q.trim()){closeList();return;}
  var starts=[],inner=[];
  for(var i=0;i<words.length&&starts.length<8;i++){
    if(keys[i].indexOf(q)===0){starts.push(i);}
    else if(inner.length<8&&keys[i].indexOf(" "+q)>=0){inner.push(i);}
  }
  shown=starts.concat(inner).slice(0,8);
  if(!shown.length){closeList();return;}
  list.textContent="";
  shown.forEach(function(index,pos){
    var item=document.createElement("li");
    item.id="pw-suggest-"+pos;
    item.className="pw-suggest-item";
    item.setAttribute("role","option");
    item.setAttribute("aria-selected","false");
    item.textContent=words[index];
    item.addEventListener("mousedown",function(e){e.preventDefault();});
    item.addEventListener("click",function(){choose(words[index]);});
    list.appendChild(item);
  });
  active=-1;
  list.hidden=false;
  input.setAttribute("aria-expanded","true");
  if(starts.length&&raw.charAt(0)!==" "&&input.selectionStart===raw.length){
    setGhost(raw,words[starts[0]].slice(raw.length));
  }
}
function accept(){
  var rest=ghostRest.textContent;
  if(!rest){return false;}
  input.value=input.value+rest;
  update();
  return true;
}
function choose(text){
  input.value=text;
  closeList();
  setGhost("","");
  if(form.requestSubmit){form.requestSubmit();}else{scanFor(text);form.submit();}
}
input.addEventListener("focus",load);
input.addEventListener("input",update);
input.addEventListener("blur",function(){setTimeout(closeList,150);setGhost("","");});
input.addEventListener("keydown",function(e){
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){
    if(!shown.length){return;}
    e.preventDefault();
    active=e.key==="ArrowDown"?(active+1)%shown.length:(active<=0?shown.length-1:active-1);
    Array.prototype.forEach.call(list.children,function(item,pos){
      item.classList.toggle("is-active",pos===active);
      item.setAttribute("aria-selected",pos===active?"true":"false");
    });
    input.setAttribute("aria-activedescendant","pw-suggest-"+active);
  }else if(e.key==="Enter"&&active>=0){
    e.preventDefault();
    choose(words[shown[active]]);
  }else if(e.key==="Escape"){
    closeList();
    setGhost("","");
  }else if((e.key==="Tab"&&!e.shiftKey)||e.key==="ArrowRight"){
    if(input.selectionStart===input.value.length&&ghostRest.textContent){
      e.preventDefault();
      accept();
    }
  }
});
ghostRest.addEventListener("mousedown",function(e){e.preventDefault();accept();});
var Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(mic&&Recognition){
  mic.hidden=false;
  var recognition=null;
  var resting=input.getAttribute("placeholder");
  var stopListening=function(){
    recognition=null;
    mic.classList.remove("is-listening");
    mic.setAttribute("aria-pressed","false");
    input.setAttribute("placeholder",resting);
  };
  mic.addEventListener("click",function(){
    if(recognition){recognition.stop();return;}
    var heard="";
    recognition=new Recognition();
    recognition.lang=navigator.language||"en-GB";
    recognition.interimResults=true;
    recognition.maxAlternatives=1;
    recognition.onresult=function(e){
      var spoken="";
      heard="";
      for(var i=0;i<e.results.length;i++){
        if(e.results[i].isFinal){heard+=e.results[i][0].transcript;}
        else{spoken+=e.results[i][0].transcript;}
      }
      input.value=(heard+spoken).trim();
    };
    recognition.onerror=function(){heard="";};
    recognition.onend=function(){
      stopListening();
      var q=heard.trim();
      if(q){choose(q);}
    };
    closeList();
    setGhost("","");
    mic.classList.add("is-listening");
    mic.setAttribute("aria-pressed","true");
    input.setAttribute("placeholder","Listening\u2026");
    try{recognition.start();}catch(err){stopListening();}
  });
}
})();
"""
