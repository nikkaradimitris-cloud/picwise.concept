"""The price bar's script and style (owner, 2026-11-12: «Να μπει ένα φίλτρο με τη μορφή
μπάρας που να διαλέγει με την τιμή για να γλιτώσουμε το πρόβλημα που βγάζει τα
φθηνότερα και μπορεί να είναι smartwatch και να δείχνει λουράκια ... βάζοντας ένα φίλτρο
τιμής το οποίο να τερματίζει στην υψηλοτερή και να ξεκινάει από την χαμηλότερη κουνώντας
μία μπίλια θα μπορεί αμέσως να φιλτράρει»).

The bar itself is drawn by `reference._price_bar_html`: a plain form whose knob is in whole
pounds, with a button to show. The script turns it into the bar the owner asked for: the
knob follows the answer's prices on a scale of ratios, as the steps drawn above it do
(`search_selection._price_bar`), so a £2 strap and a £400 watch both have room; while it
moves, the price it stands at is said ("From £150") and the steps below it turn pale; let
go, the page is drawn again from that price, behind the loading screen. At its left end
it is "Any price". The prices it offers are round ones (£7, £45, £150, £1,250), never
above the price at the knob, so a product at that price stays in.

A second knob, on the right, ends the answer at a price (owner, 2026-11-15: «Ο χρήστης
μπορεί να διαλέξει στο φίλτρο τιμής από έως»): "Up to £80", or "£30 – £80" with both;
its round prices are never under the price at the knob, and at its right end it chooses
nothing. The two never cross.
"""
from __future__ import annotations

PRICE_BAR_SCRIPT = r"""
(function(){
"use strict";
var form=document.querySelector(".pw-pricebar");
if(!form){return;}
var range=form.querySelector("#pw-pricebar-range");
var top=form.querySelector("#pw-pricebar-range-max");
var track=form.querySelector(".pw-pricebar-track");
var out=document.getElementById("pw-pricebar-value");
var bars=form.querySelectorAll(".pw-pricebar-bars i");
if(!range||!top||!out||!track){return;}
var low=parseFloat(range.getAttribute("data-low"));
var high=parseFloat(range.getAttribute("data-high"));
var base=Math.max(low,0.01);
var span=Math.log(high/base);
if(!(span>0)){return;}
var chosen=parseFloat(range.value)||0;
var chosenTop=parseFloat(top.value)||0;
function hidden(name){
  var input=document.createElement("input");
  input.type="hidden";input.name=name;input.disabled=true;
  form.appendChild(input);return input;
}
var price=hidden("min");
var priceTop=hidden("max");
range.removeAttribute("name");top.removeAttribute("name");
function placeOf(p){return p>base?Math.round(1000*Math.log(Math.min(p,high)/base)/span):0;}
[range,top].forEach(function(r){r.min="0";r.max="1000";r.step="1";});
range.value=String(placeOf(chosen));
top.value=String(chosenTop&&chosenTop<high?placeOf(chosenTop):1000);
function priceAt(place){return base*Math.exp(span*place/1000);}
function round(p){
  if(p<20){return Math.floor(p);}
  if(p<100){return Math.floor(p/5)*5;}
  if(p<1000){return Math.floor(p/10)*10;}
  return Math.floor(p/50)*50;
}
function roundUp(p){
  if(p<20){return Math.ceil(p);}
  if(p<100){return Math.ceil(p/5)*5;}
  if(p<1000){return Math.ceil(p/10)*10;}
  return Math.ceil(p/50)*50;
}
function chosenAt(place){var p=round(priceAt(place));return place<=0||p<=low?0:p;}
function chosenTopAt(place){var p=roundUp(priceAt(place));return place>=1000||p>=high?0:p;}
function places(){return [parseInt(range.value,10)||0,parseInt(top.value,10)||0];}
function paint(){
  var at=places();
  track.style.setProperty("--pos",(at[0]/10).toFixed(1)+"%");
  track.style.setProperty("--end",(at[1]/10).toFixed(1)+"%");
  range.style.zIndex=at[0]>500?"3":"2";
  for(var i=0;i<bars.length;i++){
    bars[i].classList.toggle("out",(i+1)/bars.length<=at[0]/1000||i/bars.length>=at[1]/1000);
  }
}
function money(p){return "£"+p.toLocaleString("en-GB");}
function say(){
  var at=places(),from=chosenAt(at[0]),to=chosenTopAt(at[1]);
  var words=from&&to?money(from)+" – "+money(to):from?"From "+money(from):to?"Up to "+money(to):"Any price";
  out.textContent=words;
  range.setAttribute("aria-valuetext",words);top.setAttribute("aria-valuetext",words);
}
range.addEventListener("input",function(){
  var at=places();if(at[0]>at[1]){range.value=String(at[1]);}
  paint();say();
});
top.addEventListener("input",function(){
  var at=places();if(at[1]<at[0]){top.value=String(at[0]);}
  paint();say();
});
function show(){
  var at=places(),from=chosenAt(at[0]),to=chosenTopAt(at[1]);
  price.value=from?String(from):"";price.disabled=!from;
  priceTop.value=to?String(to):"";priceTop.disabled=!to;
  var scan=document.getElementById("pw-scan");
  if(scan){scan.hidden=false;}
  form.submit();
}
range.addEventListener("change",show);
top.addEventListener("change",show);
paint();
})();
"""

PRICE_BAR_STYLES = (
    ".pw-pricebar{display:flex;align-items:center;gap:14px;max-width:560px;margin:8px 0 2px;}"
    ".pw-pricebar-track{position:relative;flex:1;min-width:0;height:48px;}"
    # How many products stand at each price, drawn just above the bar's line.
    ".pw-pricebar-bars{position:absolute;left:11px;right:11px;bottom:26px;height:22px;display:flex;align-items:flex-end;gap:2px;pointer-events:none;}"
    ".pw-pricebar-bars i{flex:1;min-width:0;background:#b9cdf2;border-radius:2px 2px 0 0;}"
    ".pw-pricebar-bars i.out{background:#e2e7ee;}"
    # The bar's line, blue between the two knobs, drawn under the two ranges.
    ".pw-pricebar-line{position:absolute;left:11px;right:11px;bottom:22px;height:4px;border-radius:999px;pointer-events:none;"
    "background:linear-gradient(to right,#dfe5ee 0,#dfe5ee var(--pos,0%),var(--blue-2) var(--pos,0%),var(--blue-2) var(--end,100%),#dfe5ee var(--end,100%),#dfe5ee 100%);}"
    # Two ranges, one over the other: only their knobs take a finger or a mouse.
    ".pw-pricebar-range{position:absolute;left:0;right:0;bottom:2px;width:100%;height:44px;margin:0;padding:0;background:transparent;-webkit-appearance:none;appearance:none;pointer-events:none;touch-action:pan-y;z-index:2;}"
    ".pw-pricebar-range-max{z-index:2;}"
    ".pw-pricebar-range:focus{outline:none;}"
    ".pw-pricebar-range::-webkit-slider-runnable-track{height:4px;background:transparent;}"
    ".pw-pricebar-range::-moz-range-track{height:4px;background:transparent;}"
    ".pw-pricebar-range::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:22px;height:22px;margin-top:-9px;border-radius:999px;background:#fff;border:2px solid var(--blue-2);box-shadow:0 2px 6px rgba(15,36,66,.25);pointer-events:auto;cursor:pointer;}"
    ".pw-pricebar-range::-moz-range-thumb{width:18px;height:18px;border-radius:999px;background:#fff;border:2px solid var(--blue-2);box-shadow:0 2px 6px rgba(15,36,66,.25);pointer-events:auto;cursor:pointer;}"
    ".pw-pricebar-range:focus-visible::-webkit-slider-thumb{outline:2px solid var(--blue);outline-offset:2px;}"
    ".pw-pricebar-range:focus-visible::-moz-range-thumb{outline:2px solid var(--blue);outline-offset:2px;}"
    ".pw-pricebar-value{flex:0 0 auto;min-width:92px;font-size:14px;font-weight:700;color:var(--ink);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;}"
    # Without JavaScript the knobs are in pounds and a button shows the answer from them.
    ".pw-pricebar-go{flex:0 0 auto;height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--blue-2);background:#fff;color:var(--blue-2);font:inherit;font-size:14px;font-weight:700;cursor:pointer;}"
    ".pw-js .pw-pricebar-go{display:none;}"
    "@media (max-width:699px){.pw-pricebar{gap:10px;margin:6px 0 2px;}.pw-pricebar-value{min-width:84px;}.pw-pricebar-go{height:44px;}}"
)
