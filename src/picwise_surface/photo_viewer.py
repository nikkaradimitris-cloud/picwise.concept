"""A card's photo, opened large at a tap (owner, 2026-11-15).

The owner: «Ο χρήστης μπορεί να έχει τη δυνατότητα η εικόνα του προϊόντος να μεγαλώνει»,
after asking for it on shoes, clothes and jewellery: «με ένα πάτημα η εικόνα να μεγαλώνει
πολύ ... και μέ ενα δεύτερο πάτημα να επιστρέψει τη θέση της», on every search; and of
the shop's further photos: «όποιος στέλνει επιπλέον φωτογραφίες ... εμφανίζουμε έως 4».

On every card the photo opens over the page, the page dimmed behind it, as shops and
price comparison sites open theirs: nearly the whole width of a phone, most of a wide
screen. It closes with a second tap on the photo, the ✕, a tap beside it, Esc, a swipe
down or the phone's back button. Where the shop sends further photos
(`normalization.extra_image_urls`, at most three), the buyer moves between them with the
arrows, a swipe or the arrow keys, and the card's corner says how many there are. A tap on
the heart is the heart's, never the photo's. The cards do not move: the photo opens over
them.

The further photos are in the page as images that load only when opened (`loading=lazy`
inside a hidden list), so the page is no heavier for them. Without JavaScript the photo
stays as it is.
"""
from __future__ import annotations

from html import escape

_ZOOM_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'
    '<path d="M11 8v6M8 11h6"/></svg>'
)


def photo_extras_html(name: str, extra_urls: list[str] | tuple[str, ...]) -> str:
    """What a card's photo holds beyond the photo itself: the hint in its corner (with how
    many photos, when more than one) and the further photos, hidden until opened."""
    extras = [str(url).strip() for url in extra_urls if str(url or "").strip()]
    total = 1 + len(extras)
    count = f'<span class="pw-zoom-count">{total}</span>' if total > 1 else ""
    hint = f'<span class="pw-zoom-hint" aria-hidden="true">{_ZOOM_ICON}{count}</span>'
    if not extras:
        return hint
    images = "".join(
        f'<img class="pw-photo-extra" src="{escape(url, quote=True)}" '
        f'alt="{escape(name, quote=True)}, photo {index} of {total}" loading="lazy" decoding="async">'
        for index, url in enumerate(extras, start=2)
    )
    return f'{hint}<span class="pw-photo-extras" hidden>{images}</span>'


def photo_wrap_attributes(name: str, extra_urls: list[str] | tuple[str, ...]) -> str:
    """The photo's frame as something to open: a button for a keyboard and a reader."""
    total = 1 + len([url for url in extra_urls if str(url or "").strip()])
    words = f"Open the photo of {name}" if total == 1 else f"Open the {total} photos of {name}"
    return f' tabindex="0" role="button" aria-label="{escape(words, quote=True)}" data-photos="{total}"'


PHOTO_VIEWER_SCRIPT = r"""
(function(){
"use strict";
if(!document.querySelector||!window.Element||!Element.prototype.closest){return;}
var root=document.documentElement;
var viewer=null,big,count,prev,next,closeButton,photos=[],at=0,opener=null,pushed=false,touch=null,swiped=false;
function el(tag,cls,label){
  var node=document.createElement(tag);node.className=cls;
  if(label){node.setAttribute("aria-label",label);}
  return node;
}
function build(){
  viewer=el("div","pw-viewer");viewer.hidden=true;
  viewer.setAttribute("role","dialog");viewer.setAttribute("aria-modal","true");
  big=el("img","pw-viewer-img");big.alt="";
  closeButton=el("button","pw-viewer-close","Close");closeButton.type="button";closeButton.textContent="✕";
  prev=el("button","pw-viewer-prev","Previous photo");prev.type="button";prev.textContent="‹";
  next=el("button","pw-viewer-next","Next photo");next.type="button";next.textContent="›";
  count=el("p","pw-viewer-count");count.setAttribute("aria-live","polite");
  viewer.appendChild(big);viewer.appendChild(prev);viewer.appendChild(next);
  viewer.appendChild(closeButton);viewer.appendChild(count);
  document.body.appendChild(viewer);
  viewer.addEventListener("click",function(e){
    if(swiped){swiped=false;return;}
    if(e.target===prev){show(at-1);return;}
    if(e.target===next){show(at+1);return;}
    close(false);
  });
  viewer.addEventListener("touchstart",function(e){
    if(e.touches.length===1){touch={x:e.touches[0].clientX,y:e.touches[0].clientY};}else{touch=null;}
  },{passive:true});
  viewer.addEventListener("touchend",function(e){
    if(!touch||!e.changedTouches.length){return;}
    var dx=e.changedTouches[0].clientX-touch.x,dy=e.changedTouches[0].clientY-touch.y;touch=null;
    if(Math.abs(dx)>40&&Math.abs(dx)>Math.abs(dy)&&photos.length>1){swiped=true;show(dx<0?at+1:at-1);}
    else if(dy>80&&dy>Math.abs(dx)){swiped=true;close(false);}
    if(swiped){setTimeout(function(){swiped=false;},400);}
  },{passive:true});
}
function show(index){
  at=(index+photos.length)%photos.length;
  big.src=photos[at].src;big.alt=photos[at].alt;
  count.textContent=photos.length>1?(at+1)+" / "+photos.length:"";
  prev.hidden=next.hidden=photos.length<2;
}
function open(wrap){
  var images=wrap.querySelectorAll("img.pw-product-image, img.pw-photo-extra");
  photos=[];
  for(var i=0;i<images.length;i++){
    var src=images[i].getAttribute("src");
    if(src&&!(images[i].complete&&images[i].naturalWidth===0&&i>0)){photos.push({src:src,alt:images[i].getAttribute("alt")||""});}
  }
  if(!photos.length){return;}
  if(!viewer){build();}
  viewer.setAttribute("aria-label",wrap.getAttribute("aria-label")||"Photo");
  show(0);
  viewer.hidden=false;root.classList.add("pw-viewer-open");
  opener=wrap;
  try{history.pushState({pwViewer:1},"");pushed=true;}catch(err){pushed=false;}
  closeButton.focus();
}
function close(fromHistory){
  if(!viewer||viewer.hidden){return;}
  viewer.hidden=true;root.classList.remove("pw-viewer-open");
  big.removeAttribute("src");
  if(pushed&&!fromHistory){pushed=false;try{history.back();}catch(err){}}
  pushed=false;
  if(opener){try{opener.focus({preventScroll:true});}catch(err){}}
}
document.addEventListener("click",function(e){
  var target=e.target;
  if(!target||!target.closest||target.closest(".pw-fav")){return;}
  var wrap=target.closest(".pw-zoomable");
  if(wrap&&(!viewer||viewer.hidden)){e.preventDefault();open(wrap);}
});
document.addEventListener("keydown",function(e){
  if(viewer&&!viewer.hidden){
    if(e.key==="Escape"){e.preventDefault();close(false);}
    else if(e.key==="ArrowRight"&&photos.length>1){show(at+1);}
    else if(e.key==="ArrowLeft"&&photos.length>1){show(at-1);}
    else if(e.key==="Tab"){
      var stops=[prev,next,closeButton].filter(function(b){return !b.hidden;});
      var i=stops.indexOf(document.activeElement);
      e.preventDefault();stops[(i+(e.shiftKey?-1:1)+stops.length)%stops.length].focus();
    }
    return;
  }
  var wrap=e.target&&e.target.classList&&e.target.classList.contains("pw-zoomable")?e.target:null;
  if(wrap&&(e.key==="Enter"||e.key===" ")){e.preventDefault();open(wrap);}
});
window.addEventListener("popstate",function(){close(true);});
})();
"""

PHOTO_VIEWER_STYLES = (
    ".pw-zoomable{cursor:zoom-in;}"
    ".pw-zoomable:focus-visible{outline:2px solid var(--blue-2);outline-offset:2px;}"
    ".pw-zoom-hint{display:none;position:absolute;left:8px;bottom:8px;align-items:center;gap:3px;height:26px;padding:0 7px;"
    "border-radius:999px;background:rgba(255,255,255,.94);border:1px solid var(--line);color:#5d6f8c;"
    "font-size:12px;font-weight:700;line-height:1;pointer-events:none;}"
    ".pw-js .pw-zoom-hint{display:flex;}"
    ".pw-zoom-hint svg{width:15px;height:15px;}"
    ".pw-viewer{position:fixed;top:0;right:0;bottom:0;left:0;z-index:100;display:flex;align-items:center;justify-content:center;"
    "padding:60px 12px 52px;background:rgba(10,20,36,.88);cursor:zoom-out;}"
    ".pw-viewer[hidden]{display:none;}"
    ".pw-viewer-img{display:block;width:min(100%,85vh,960px);height:auto;max-height:100%;aspect-ratio:1/1;object-fit:contain;"
    "background:#fff;border-radius:14px;}"
    ".pw-viewer-close,.pw-viewer-prev,.pw-viewer-next{position:absolute;display:flex;align-items:center;justify-content:center;"
    "width:48px;height:48px;padding:0;border:0;border-radius:50%;background:rgba(255,255,255,.95);color:var(--ink);"
    "font:inherit;font-size:22px;line-height:1;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);}"
    ".pw-viewer-close{top:10px;right:12px;}"
    ".pw-viewer-prev{left:12px;top:50%;transform:translateY(-50%);font-size:30px;}"
    ".pw-viewer-next{right:12px;top:50%;transform:translateY(-50%);font-size:30px;}"
    ".pw-viewer-prev[hidden],.pw-viewer-next[hidden]{display:none;}"
    ".pw-viewer-close:focus-visible,.pw-viewer-prev:focus-visible,.pw-viewer-next:focus-visible{outline:3px solid #9cc0ff;outline-offset:2px;}"
    ".pw-viewer-count{position:absolute;left:0;right:0;bottom:14px;margin:0;text-align:center;color:#fff;font-size:14px;font-weight:600;}"
    "html.pw-viewer-open,html.pw-viewer-open body{overflow:hidden;}"
    "@media (max-width:699px){.pw-viewer{padding:56px 8px 48px;}.pw-viewer-img{width:100%;}"
    ".pw-zoom-hint{left:5px;bottom:5px;height:24px;padding:0 6px;}}"
)
