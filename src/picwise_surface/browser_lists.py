"""History and Favourites, kept in the visitor's own browser (owner, 2026-10-31).

They take the place of the Login and Register buttons, which did nothing. The owner chose
favourites and search history without a login, kept in the visitor's browser («συμφωνώ
στο 6»; asked about a login: search history yes, no login for now). The design is the
proposal's (`docs/design/picwise_design_proposal_2026-10-31.html`).

What they keep, and where:

- **Favourites**: a product the visitor saves with the heart on its photo: its id, title,
  price and shop as the card showed them, its photo's address, the search it came from,
  and the time. Up to `FAVOURITES_MAX`, the oldest going first.
- **History**: the visitor's searches, newest first, up to `HISTORY_MAX`, and only once
  the visitor has asked for it («Keep my searches»). A list kept on the device must be
  something the visitor asked for (UK PECR, the EU's ePrivacy rules), so the history is
  off until switched on, and «Stop keeping history» forgets it.

Both live in the browser's local storage, under the keys below, and nothing of them is
ever sent to PicWise: the script makes no request, and the server never reads them. Both
need JavaScript and a browser that allows local storage; without either, their buttons
are not shown, rather than shown doing nothing.
"""
from __future__ import annotations

from html import escape

HISTORY_STORAGE_KEY = "picwise.history.v1"
HISTORY_ON_STORAGE_KEY = "picwise.history.on"
FAVOURITES_STORAGE_KEY = "picwise.favourites.v1"
HISTORY_MAX = 20
FAVOURITES_MAX = 50

DEVICE_ONLY_NOTE = "Kept only in this browser; PicWise never receives it."

_CLOCK_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>'
)
HEART_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<path d="M12 20.2s-7.6-4.6-7.6-10.3A4.2 4.2 0 0 1 12 7.4a4.2 4.2 0 0 1 7.6 2.5c0 5.7-7.6 10.3-7.6 10.3z"/></svg>'
)

# Run in the page's <head>, before anything is drawn: the buttons that need JavaScript
# and local storage appear with the page, never a moment after it (no layout shift).
# It only reads: finding out whether storage is allowed stores nothing.
HEAD_SCRIPT = (
    "(function(){var c=document.documentElement.classList;c.add('pw-js');"
    f"try{{if(window.localStorage){{window.localStorage.getItem('{FAVOURITES_STORAGE_KEY}');c.add('pw-store');}}}}"
    "catch(e){}})();"
)


def header_buttons_html() -> str:
    """The History and Favourites buttons of the page's header."""
    return (
        '<button class="pw-head-btn pw-needs-store" id="pw-history-button" type="button" '
        'aria-expanded="false" aria-controls="pw-history-panel">'
        f'{_CLOCK_ICON}<span class="pw-head-txt">History</span></button>'
        '<button class="pw-head-btn pw-needs-store" id="pw-favourites-button" type="button" '
        'aria-expanded="false" aria-controls="pw-favourites-panel">'
        f'{HEART_ICON}<span class="pw-head-txt">Favourites</span>'
        '<span class="pw-count" id="pw-favourites-count" hidden></span></button>'
    )


def _panel_html(*, key: str, title: str) -> str:
    return (
        f'<section class="pw-panel" id="pw-{key}-panel" aria-labelledby="pw-{key}-title" hidden>'
        '<div class="pw-panel-head">'
        f'<h2 class="pw-panel-title" id="pw-{key}-title" tabindex="-1">{title}</h2>'
        '<button class="pw-panel-close" type="button" aria-label="Close">&#215;</button></div>'
        f'<div class="pw-panel-body" id="pw-{key}-body"></div>'
        f'<p class="pw-panel-note">{DEVICE_ONLY_NOTE}</p>'
        "</section>"
    )


def panels_html() -> str:
    """The two panels the header's buttons open, filled by `BROWSER_LISTS_SCRIPT`."""
    return (
        '<div class="pw-panels pw-needs-store">'
        f'{_panel_html(key="history", title="History (on this device)")}'
        f'{_panel_html(key="favourites", title="Favourites (on this device)")}'
        "</div>"
    )


def favourite_button_html(*, product_id: str, title: str, price: str, shop: str, image: str) -> str:
    """The heart on a product's photo. It carries what the Favourites panel shows."""
    return (
        '<button class="pw-fav pw-needs-store" type="button" aria-pressed="false" '
        f'aria-label="{escape("Save to favourites: " + title, quote=True)}" '
        f'data-fav-id="{escape(product_id, quote=True)}" data-fav-title="{escape(title, quote=True)}" '
        f'data-fav-price="{escape(price, quote=True)}" data-fav-shop="{escape(shop, quote=True)}" '
        f'data-fav-image="{escape(image, quote=True)}">{HEART_ICON}</button>'
    )


# Plain JavaScript, no library. It reads and writes only local storage, makes no
# request, and builds every line with textContent, so nothing kept can become markup.
BROWSER_LISTS_SCRIPT = (
    r"""
(function(){
"use strict";
var root=document.documentElement;
if(!root.classList.contains("pw-store")){return;}
var HKEY="__HKEY__",HON="__HON__",FKEY="__FKEY__",HMAX=__HMAX__,FMAX=__FMAX__;
function read(key){try{return JSON.parse(window.localStorage.getItem(key)||"null");}catch(e){return null;}}
function write(key,value){try{window.localStorage.setItem(key,JSON.stringify(value));return true;}catch(e){return false;}}
function forget(key){try{window.localStorage.removeItem(key);}catch(e){}}
function list(key){var value=read(key);return Array.isArray(value)?value:[];}
function clean(text,max){return String(text==null?"":text).replace(/\s+/g," ").trim().slice(0,max||300);}
function el(tag,cls,text){var node=document.createElement(tag);if(cls){node.className=cls;}if(text!=null){node.textContent=text;}return node;}
function dayLabel(time){
  var date=new Date(time);
  if(isNaN(date.getTime())){return "";}
  var today=new Date();today.setHours(0,0,0,0);
  var day=new Date(date.getTime());day.setHours(0,0,0,0);
  var days=Math.round((today-day)/86400000);
  if(days===0){return "today";}
  if(days===1){return "yesterday";}
  return date.toLocaleDateString("en-GB",{day:"numeric",month:"short"});
}
var input=document.querySelector(".pw-search-input");
var query=input?clean(input.defaultValue,200):"";

/* History: only once the visitor has asked for it. */
function historyOn(){return read(HON)===1;}
function remember(q){
  if(!q||!historyOn()){return;}
  var key=q.toLowerCase();
  var items=list(HKEY).filter(function(item){return item&&typeof item.q==="string"&&item.q.toLowerCase()!==key;});
  items.unshift({q:q,t:Date.now()});
  write(HKEY,items.slice(0,HMAX));
}
remember(query);

/* Favourites. */
function favourites(){return list(FKEY).filter(function(item){return item&&typeof item.id==="string"&&item.id;});}
function isFavourite(id){return favourites().some(function(item){return item.id===id;});}
var count=document.getElementById("pw-favourites-count");
function showCount(){
  if(!count){return;}
  var n=favourites().length;
  count.textContent=n?String(n):"";
  count.hidden=!n;
}
function markHearts(){
  var saved={};
  favourites().forEach(function(item){saved[item.id]=true;});
  Array.prototype.forEach.call(document.querySelectorAll(".pw-fav"),function(button){
    var on=!!saved[button.getAttribute("data-fav-id")];
    button.classList.toggle("is-on",on);
    button.setAttribute("aria-pressed",on?"true":"false");
    var title=button.getAttribute("data-fav-title")||"";
    button.setAttribute("aria-label",(on?"Remove from favourites: ":"Save to favourites: ")+title);
  });
}
function toggleFavourite(button){
  var id=clean(button.getAttribute("data-fav-id"),200);
  if(!id){return;}
  var items=favourites();
  if(isFavourite(id)){
    items=items.filter(function(item){return item.id!==id;});
  }else{
    items.unshift({
      id:id,
      title:clean(button.getAttribute("data-fav-title"),300),
      price:clean(button.getAttribute("data-fav-price"),40),
      shop:clean(button.getAttribute("data-fav-shop"),120),
      image:clean(button.getAttribute("data-fav-image"),1000),
      q:query,
      t:Date.now()
    });
    items=items.slice(0,FMAX);
  }
  if(write(FKEY,items)){refresh();}
}
Array.prototype.forEach.call(document.querySelectorAll(".pw-fav"),function(button){
  button.addEventListener("click",function(event){event.preventDefault();toggleFavourite(button);});
});

/* The panels. */
var historyBody=document.getElementById("pw-history-body");
var favouritesBody=document.getElementById("pw-favourites-body");
function action(text,handler){
  var button=el("button","pw-panel-action",text);
  button.type="button";
  button.addEventListener("click",handler);
  return button;
}
function drawHistory(){
  if(!historyBody){return;}
  historyBody.textContent="";
  if(!historyOn()){
    historyBody.appendChild(el("p","pw-panel-text","Keep a list of your searches on this device, to run them again with one tap."));
    historyBody.appendChild(action("Keep my searches",function(){
      if(!write(HON,1)){historyBody.appendChild(el("p","pw-panel-text","This browser does not let PicWise keep anything on it."));return;}
      remember(query);
      drawHistory();
    }));
    return;
  }
  var items=list(HKEY).filter(function(item){return item&&typeof item.q==="string"&&item.q;});
  if(!items.length){
    historyBody.appendChild(el("p","pw-panel-text","No searches kept yet. Your next searches will show here."));
  }else{
    var ul=el("ul","pw-panel-list");
    items.forEach(function(item){
      var li=el("li","pw-panel-row");
      var link=el("a","pw-panel-link",item.q);
      link.href="/search?q="+encodeURIComponent(item.q);
      li.appendChild(link);
      li.appendChild(el("span","pw-panel-when",dayLabel(item.t)));
      ul.appendChild(li);
    });
    historyBody.appendChild(ul);
  }
  var actions=el("div","pw-panel-actions");
  if(items.length){actions.appendChild(action("Clear history",function(){write(HKEY,[]);drawHistory();}));}
  actions.appendChild(action("Stop keeping history",function(){forget(HKEY);forget(HON);drawHistory();}));
  historyBody.appendChild(actions);
}
function drawFavourites(){
  if(!favouritesBody){return;}
  favouritesBody.textContent="";
  var items=favourites();
  if(!items.length){
    favouritesBody.appendChild(el("p","pw-panel-text","Tap the heart on a product's photo to keep it here."));
    return;
  }
  var ul=el("ul","pw-panel-list");
  items.forEach(function(item){
    var li=el("li","pw-panel-row pw-panel-product");
    if(/^https?:\/\//i.test(item.image||"")){
      var img=el("img","pw-panel-thumb");
      img.alt="";
      img.loading="lazy";
      img.width=48;
      img.height=48;
      img.src=item.image;
      li.appendChild(img);
    }
    var text=el("div","pw-panel-product-text");
    var link=el("a","pw-panel-link",item.title||"Saved product");
    link.href="/out/feed?pid="+encodeURIComponent(item.id)+"&q="+encodeURIComponent(item.q||"")+"&src=favourites&rec=0";
    link.rel="nofollow sponsored noopener";
    text.appendChild(link);
    var facts=[];
    if(item.price){facts.push(item.price+" when saved"+(dayLabel(item.t)?", "+dayLabel(item.t):""));}
    if(item.shop){facts.push(item.shop);}
    text.appendChild(el("span","pw-panel-when",facts.join(" · ")));
    li.appendChild(text);
    var remove=action("Remove",function(){
      write(FKEY,favourites().filter(function(other){return other.id!==item.id;}));
      refresh();
    });
    remove.setAttribute("aria-label","Remove from favourites: "+(item.title||""));
    li.appendChild(remove);
    ul.appendChild(li);
  });
  favouritesBody.appendChild(ul);
  var actions=el("div","pw-panel-actions");
  actions.appendChild(action("Clear favourites",function(){write(FKEY,[]);refresh();}));
  favouritesBody.appendChild(actions);
}
function refresh(){showCount();markHearts();drawFavourites();drawHistory();}

var panels=[
  {button:document.getElementById("pw-history-button"),panel:document.getElementById("pw-history-panel")},
  {button:document.getElementById("pw-favourites-button"),panel:document.getElementById("pw-favourites-panel")}
];
function close(entry){
  if(!entry.panel||entry.panel.hidden){return;}
  entry.panel.hidden=true;
  if(entry.button){entry.button.setAttribute("aria-expanded","false");}
}
function open(entry){
  panels.forEach(function(other){if(other!==entry){close(other);}});
  refresh();
  entry.panel.hidden=false;
  entry.button.setAttribute("aria-expanded","true");
  var title=entry.panel.querySelector(".pw-panel-title");
  if(title){title.focus();}
}
panels.forEach(function(entry){
  if(!entry.button||!entry.panel){return;}
  entry.button.addEventListener("click",function(event){
    event.stopPropagation();
    if(entry.panel.hidden){open(entry);}else{close(entry);}
  });
  var shut=entry.panel.querySelector(".pw-panel-close");
  if(shut){shut.addEventListener("click",function(){close(entry);entry.button.focus();});}
  entry.panel.addEventListener("click",function(event){event.stopPropagation();});
});
document.addEventListener("click",function(){panels.forEach(close);});
document.addEventListener("keydown",function(event){
  if(event.key==="Escape"){panels.forEach(function(entry){if(entry.panel&&!entry.panel.hidden){close(entry);entry.button.focus();}});}
});
window.addEventListener("storage",function(event){
  if(event.key===FKEY||event.key===HKEY||event.key===HON){refresh();}
});
refresh();
})();
"""
    .replace("__HKEY__", HISTORY_STORAGE_KEY)
    .replace("__HON__", HISTORY_ON_STORAGE_KEY)
    .replace("__FKEY__", FAVOURITES_STORAGE_KEY)
    .replace("__HMAX__", str(HISTORY_MAX))
    .replace("__FMAX__", str(FAVOURITES_MAX))
)


BROWSER_LISTS_STYLES = (
    ".pw-needs-store,.pw-needs-js{display:none!important;}"
    ".pw-store .pw-head-btn.pw-needs-store{display:inline-flex!important;}"
    ".pw-store .pw-fav.pw-needs-store{display:flex!important;}"
    ".pw-store .pw-panels.pw-needs-store{display:block!important;}"
    ".pw-js .pw-needs-js{display:flex!important;}"
    ".pw-head-btn{align-items:center;gap:7px;height:36px;padding:0 13px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink-2);font:inherit;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;}"
    ".pw-head-btn svg{width:17px;height:17px;flex:0 0 auto;}"
    ".pw-head-btn[aria-expanded=true]{background:#eef4ff;border-color:#c9daf8;color:var(--blue);}"
    ".pw-head-btn:focus-visible,.pw-fav:focus-visible,.pw-panel-action:focus-visible,.pw-panel-close:focus-visible{outline:2px solid var(--blue-2);outline-offset:2px;}"
    ".pw-count{background:var(--blue);color:#fff;border-radius:999px;font-size:11px;line-height:16px;min-width:18px;padding:0 5px;text-align:center;}"
    ".pw-count[hidden]{display:none;}"
    ".pw-panels{position:relative;width:100%;max-width:1190px;margin:0 auto;height:0;z-index:30;}"
    ".pw-panel{position:absolute;right:22px;top:6px;width:min(380px,calc(100% - 24px));background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 16px 40px rgba(16,40,80,.16);padding:14px;text-align:left;}"
    ".pw-panel[hidden]{display:none;}"
    ".pw-panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px;}"
    ".pw-panel-title{margin:0;font-size:15px;color:var(--ink);outline:none;}"
    ".pw-panel-close{width:30px;height:30px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink-2);font-size:18px;line-height:1;cursor:pointer;}"
    ".pw-panel-text{margin:6px 0 10px;font-size:14px;line-height:1.5;color:var(--ink-2);}"
    ".pw-panel-list{list-style:none;margin:0 0 10px;padding:0;max-height:min(60vh,420px);overflow:auto;}"
    ".pw-panel-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid #f0f3f9;font-size:14px;color:var(--ink-2);}"
    ".pw-panel-link{color:var(--blue);text-decoration:none;font-weight:600;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-panel-link:hover{text-decoration:underline;}"
    ".pw-panel-when{color:var(--muted);font-size:12px;white-space:nowrap;}"
    ".pw-panel-product{justify-content:flex-start;}"
    ".pw-panel-thumb{width:48px;height:48px;object-fit:contain;border:1px solid #edf2fa;border-radius:8px;background:#fff;flex:0 0 auto;}"
    ".pw-panel-product-text{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1;}"
    ".pw-panel-product-text .pw-panel-link{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;white-space:normal;}"
    ".pw-panel-product-text .pw-panel-when{white-space:normal;}"
    ".pw-panel-actions{display:flex;flex-wrap:wrap;gap:8px;}"
    ".pw-panel-action{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer;}"
    ".pw-panel-row .pw-panel-action{flex:0 0 auto;padding:5px 10px;font-size:12px;}"
    ".pw-panel-body>.pw-panel-action{background:var(--blue-2);border-color:var(--blue-2);color:#fff;}"
    ".pw-panel-note{margin:10px 0 0;font-size:12px;line-height:1.45;color:var(--muted);}"
    ".pw-fav{position:absolute;top:8px;right:8px;width:36px;height:36px;border-radius:50%;border:1px solid var(--line);background:#fff;color:#5d6f8c;align-items:center;justify-content:center;cursor:pointer;padding:0;z-index:2;}"
    ".pw-fav svg{width:18px;height:18px;}"
    ".pw-fav.is-on{color:#e5484d;border-color:#f3c3c5;}"
    ".pw-fav.is-on svg{fill:#e5484d;}"
    "@media (max-width:699px){.pw-head-txt{display:none;}.pw-head-btn{padding:0 10px;}.pw-panel{left:12px;right:12px;width:auto;}}"
)
