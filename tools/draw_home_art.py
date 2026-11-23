"""The drawings of the home page as a store (`docs/PICWISE_HOME_STORE_SPEC.md`).

The owner, 2026-11-23, of the home page's banners and tiles: «τα προϊόντα που παρουσιάζονται
στα μπανεράκια δεν χρειάζεται να είναι τα κανονικά προϊόντα»; then, shown them, «Θα το βλεπα
και έτσι με τα πρόχειρα σχεδιάκια»; and of their colours, «γίνεσαι παιδική χαρά»: one family
only, the logo's blues, a gold, greys and wood. They are drawings of a kind of product, never
of a product a shop sells: nothing on them is a product's photo, name or price.

    python tools/draw_home_art.py            writes assets/home/art/*.svg and assets/home/ov/*.svg
    python tools/draw_home_art.py --all      also the drawings no tile uses yet
    python tools/draw_home_art.py DIR        writes under DIR instead (art/, ov/)

A drawing is 200 x 200, its ground clear, with a soft shadow under it; a background is
400 x 400, clear, laid over a tile's plain colour. Each flat colour of a drawing becomes a
gradient lit from above (`svg`). To add a drawing: one more `A['name']=svg(...)` line, its
name in `USED`, and this script run again. The files it writes are the ones the site
serves: change a drawing here, never in its file.
"""
import os, sys

DK="#232a36"; DK2="#39424f"; G1="#6b7686"; G2="#9aa5b3"; G3="#c9d0d9"; G4="#e5e9ee"; W="#ffffff"
OR="#1f5fd6"; ORL="#6f9ff0"; OR2="#3d7be6"; YE="#f9bd3b"; YE2="#fcd98a"; RE="#1f4fb0"; REL="#7da2ea"
MI="#3f86ea"; BR="#8b5a2b"; GO="#c9a85c"; INK="#0f1826"
import re
def adj(hexc, f):
    h = hexc.lstrip('#'); rgb = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    rgb = [int(v + (255 - v) * f) if f >= 0 else int(v * (1 + f)) for v in rgb]
    return '#%02x%02x%02x' % tuple(rgb)
def svg(body, shadow=True):
    # every flat fill becomes a soft top-lit gradient, for a studio-photo feel
    cols = sorted(set(re.findall(r'fill="(#[0-9a-fA-F]{6})"', body)))
    defs = ['<filter id="blur" x="-40%" y="-300%" width="180%" height="700%"><feGaussianBlur stdDeviation="5"/></filter>']
    for col in cols:
        gid = 'g' + col[1:]
        defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="{adj(col, 0.30)}"/>'
                    f'<stop offset="0.55" stop-color="{col}"/><stop offset="1" stop-color="{adj(col, -0.25)}"/></linearGradient>')
        body = body.replace(f'fill="{col}"', f'fill="url(#{gid})"')
    sh = '<ellipse cx="100" cy="186" rx="68" ry="8" fill="#000000" fill-opacity="0.32" filter="url(#blur)"/>' if shadow else ''
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">'
            + '<defs>' + ''.join(defs) + '</defs>' + sh + body + '</svg>')
def r(x,y,w,h,rx=0,f=DK,extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" {extra}/>'
def c(cx,cy,rr,f=DK,extra=''):
    return f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{f}" {extra}/>'
def p(d,f=DK,extra=''):
    return f'<path d="{d}" fill="{f}" {extra}/>'
def s(d,col=DK,w=6,extra=''):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
A={}
A['drill']=svg(r(52,150,70,24,6)+r(58,156,58,4,2,OR)+p('M76 98 L102 98 L96 152 L68 152 Z')
  +r(38,56,104,46,22,OR)+r(52,62,70,8,4,ORL)+r(50,74,4,16,2,DK2)+r(58,74,4,16,2,DK2)+r(66,74,4,16,2,DK2)
  +r(140,64,14,30,3)+r(154,68,18,22,4,G2)+r(172,76,22,6,2,G3)+r(100,100,8,14,3,YE))
A['mitre_saw']=svg(r(26,146,148,16,4)+r(52,136,96,12,3,G2)+r(40,120,10,26,2,G1)+r(150,120,10,26,2,G1)
  +r(136,76,16,62,5,DK2)+c(92,100,42,G3)+c(92,100,42,'none',f'stroke="{G1}" stroke-width="4" stroke-dasharray="5 4"')+c(92,100,9,G1)
  +p('M50 100 A42 42 0 0 1 134 100 L124 100 A32 32 0 0 0 60 100 Z',OR)+r(112,48,46,32,12)+s('M100 56 Q110 24 148 38',DK,10))
A['air_compressor']=svg(s('M42 98 V66 H62',DK,7)+r(28,98,144,58,29,RE)+r(46,106,100,8,4,REL)+r(68,62,62,38,8)
  +r(76,70,46,4,2,DK2)+r(76,78,46,4,2,DK2)+r(76,86,46,4,2,DK2)+c(150,78,13,W,f'stroke="{DK}" stroke-width="4"')
  +s('M150 78 L157 71',RE,3)+c(56,164,13)+c(56,164,5,G2)+c(144,164,13)+c(144,164,5,G2))
A['angle_grinder']=svg(r(18,88,36,30,13)+r(40,82,104,42,20,OR)+r(54,88,70,7,3.5,ORL)+r(58,104,4,12,2,DK2)+r(66,104,4,12,2,DK2)+r(74,104,4,12,2,DK2)
  +r(84,76,22,8,4)+r(136,76,30,50,9,G1)+r(146,44,12,34,5)+p('M118 132 Q156 104 194 132 Z',G2)+r(116,130,80,8,4,G3))
A['lawn_mower']=svg(p('M114 96 L146 70 L166 94 L134 120 Z',G1)+s('M120 112 L154 40 H170 L138 112',DK,7)
  +p('M26 128 Q30 98 68 96 H130 Q154 98 154 128 V136 H26 Z',YE)+r(40,104,70,6,3,YE2)+r(58,84,50,18,8)
  +c(48,146,17)+c(48,146,6,G3)+c(134,146,17)+c(134,146,6,G3))
A['pressure_washer']=svg(s('M58 72 V40 H104 V72',DK,9)+r(46,68,70,96,18,YE)+r(56,74,8,70,4,YE2)+r(60,86,42,26,6)+c(81,99,7,G3)
  +c(64,166,14)+c(64,166,5,G2)+s('M114 142 C152 142 156 112 132 108 C110 104 118 78 148 80',DK,5)
  +p('M144 84 L158 72 L166 80 L152 94 Z')+s('M160 74 L192 44',G2,6))
A['chainsaw']=svg(r(96,98,98,28,14,G3)+r(96,98,98,28,14,'none',f'stroke="{G1}" stroke-width="4" stroke-dasharray="4 3"')
  +r(8,104,24,30,10)+r(22,82,88,58,16,OR)+r(34,90,60,7,3.5,ORL)+s('M38 84 Q38 46 74 46 H100 V84',DK,10)
  +c(50,112,13)+c(50,112,5,G1))
A['hedge_trimmer']=svg(s('M102 94 H194',G2,6,'stroke-dasharray="4 5"')+s('M102 116 H194',G2,6,'stroke-dasharray="4 5"')
  +r(98,98,98,14,5,G3)+r(10,92,30,24,11)+r(30,84,76,40,16,OR)+r(42,91,52,7,3.5,ORL)+s('M70 86 Q70 50 98 58 L104 86',DK,9))
A['air_fryer']=svg(r(46,38,108,132,32)+r(60,44,80,10,5,DK2)+r(74,60,52,22,6,INK)+r(84,67,32,8,2,YE)
  +s('M50 104 H150',DK2,3)+r(82,124,36,16,8,G2))
A['coffee_machine']=svg(r(38,32,124,134,14,'#d6dade')+r(38,32,124,20,10)+r(54,82,92,66,8)+r(80,82,40,12,3,G2)
  +r(108,90,60,9,4.5,INK)+p('M86 120 H114 L111 142 H89 Z',W)+s('M113 125 Q124 127 112 136',W,3)
  +c(70,66,8,W,f'stroke="{G2}" stroke-width="2"')+c(120,66,5,YE)+c(136,66,5,G2)+r(54,148,92,8,3,G2))
A['microwave']=svg(r(22,56,156,98,10,G4,f'stroke="{G3}" stroke-width="2"')+r(34,68,98,74,6)+p('M42 76 L70 76 L52 134 L42 134 Z',W,'fill-opacity="0.12"')
  +r(140,68,28,74,4,G3)+c(154,86,7,G1)+c(154,112,7,G1)+r(146,128,16,6,3,YE)+r(34,154,14,6,2)+r(152,154,14,6,2))
A['kettle']=svg(r(54,154,92,12,6)+s('M132 74 Q174 80 160 142',DK,11)+p('M68 82 L38 70 L44 86 L64 102 Z',MI)
  +p('M68 64 H132 L144 156 H56 Z',MI)+r(80,92,8,44,4,W,'fill-opacity="0.55"')+r(74,54,52,12,6)+r(92,46,16,10,4))
A['dehumidifier']=svg(r(54,28,92,144,18,'#f4f5f7',f'stroke="{G3}" stroke-width="2"')
  +''.join(r(66,y,68,4,2,G3) for y in (40,48,56,64))+c(80,84,6,MI)+r(92,80,32,8,4,G3)+r(66,110,68,48,8,'#cfe9ff')
  +p('M100 120 C94 128 91 132 91 138 A9 9 0 0 0 109 138 C109 132 106 128 100 120 Z','#3aa0ff'))
A['heater']=svg(''.join(r(38+i*22,46,18,110,9,W,f'stroke="{G3}" stroke-width="2"') for i in range(6))+r(40,154,116,6,3,G2)
  +r(166,64,18,40,5)+c(175,76,5,YE)+c(50,166,9)+c(146,166,9)
  +s('M70 32 q6 -7 0 -14',YE,3)+s('M100 32 q6 -7 0 -14',YE,3)+s('M130 32 q6 -7 0 -14',YE,3))
A['robot_vacuum']=svg(c(100,104,68)+c(100,104,58,DK2)+s('M42 80 A68 68 0 0 1 158 80',G3,6)+c(100,104,18,G2)+c(100,104,10,G1)+c(100,142,5,MI))
A['air_purifier']=svg(r(58,36,84,132,26,'#f4f5f7',f'stroke="{G3}" stroke-width="2"')+r(70,42,60,10,5,G3)
  +''.join(r(68+i*10,96,4,58,2,G3) for i in range(7))+c(100,72,5,MI))
A['tv']=svg('<defs><clipPath id="scr"><rect x="20" y="44" width="160" height="96" rx="3"/></clipPath></defs>'
  +r(14,38,172,108,6,INK)+'<g clip-path="url(#scr)">'+r(20,44,160,96,0,'#0f1826')
  +p('M20 60 C70 30 110 80 180 40 V62 C130 92 90 52 20 88 Z','#1f5fd6')
  +p('M20 96 C56 60 92 112 126 74 S170 52 180 50 V84 C150 96 130 132 96 120 S40 122 20 140 Z','#ffc23d')
  +p('M20 120 C60 84 92 140 132 100 S180 76 180 76 V140 H20 Z',OR)
  +p('M20 132 C80 112 120 150 180 120 V140 H20 Z',MI)+'</g>'
  +r(84,146,32,8,2,INK)+r(64,154,72,6,3,INK))
A['headphones']=svg(s('M50 116 V98 A50 50 0 0 1 150 98 V116',DK,12)+r(32,104,36,58,17,MI)+r(60,110,12,46,6)
  +r(132,104,36,58,17,MI)+r(128,110,12,46,6))
A['gamepad']=svg(p('M58 70 H142 C166 70 182 92 176 118 L168 150 C164 166 144 170 134 158 L120 140 H80 L66 158 C56 170 36 166 32 150 L24 118 C18 92 34 70 58 70 Z')
  +r(52,96,10,30,2,G3)+r(42,106,30,10,2,G3)+c(138,96,7,YE)+c(154,111,7,MI)+c(122,111,7,'#3f86ea')+c(138,126,7,'#5fa8f5')
  +c(82,132,10,DK2)+c(118,132,10,DK2))
A['soundbar']=svg(r(8,90,184,34,17)+r(24,103,152,8,4,DK2)+r(92,116,16,3,1.5,MI)+r(56,124,10,8,2,DK2)+r(134,124,10,8,2,DK2))
A['fridge']=svg(r(58,18,84,154,10,'#e9ecef',f'stroke="{G3}" stroke-width="2"')+s('M60 72 H140',G3,3)+r(66,40,6,22,3,G1)+r(66,84,6,40,3,G1)
  +r(64,172,12,6,2)+r(124,172,12,6,2))
A['sofa']=svg(r(34,62,132,52,14,'#5f7fb4')+r(14,88,30,60,12,'#5f7fb4')+r(156,88,30,60,12,'#5f7fb4')+r(22,104,156,40,12,'#4d6da2')
  +s('M100 70 V108',"#3f5d90",3)+r(34,144,8,16,2)+r(158,144,8,16,2))
A['boot']=svg(r(80,20,16,16,4,'#6e4520')+p('M62 30 H112 V112 L156 128 C170 133 176 142 176 154 V160 H52 V120 C62 112 62 104 62 96 Z',BR)
  +r(70,36,6,60,3,'#a8743f')+''.join(s(f'M80 {y} H104','#f2d7b6',3) for y in (52,66,80,94))+r(50,156,128,14,5))
A['watch']=svg(r(82,14,36,172,12,BR)+c(100,100,46,GO)+c(100,100,40,'#a8894a')+c(100,100,36,W)
  +r(98,68,4,8,1)+r(98,124,4,8,1)+r(68,98,8,4,1)+r(124,98,8,4,1)+s('M100 100 V76',DK,4)+s('M100 100 L118 108',DK,3)+c(100,100,3)+r(144,94,10,12,3,GO))
A['toy_blocks']=svg(r(30,108,60,60,8,YE)+r(96,108,60,60,8,'#3f86ea')+r(62,44,60,60,8,'#5fa8f5')
  +c(60,138,13,W,'fill-opacity="0.75"')+p('M126 124 L140 150 H112 Z',W,'fill-opacity="0.75"')+r(80,62,24,24,3,W,'fill-opacity="0.75"'))
A['dumbbell']=svg(r(50,94,100,12,6,G3)+r(30,70,22,60,6)+r(148,70,22,60,6)+r(16,82,16,36,5,DK2)+r(168,82,16,36,5,DK2))
A['perfume']=svg(r(76,24,48,34,8)+r(88,56,24,16,0,GO)+r(52,70,96,104,16,'#fbe3ae')+r(62,80,10,80,5,W,'fill-opacity="0.5"')
  +r(78,112,44,26,4,W,'fill-opacity="0.9"')+r(86,123,28,4,2,GO))
spokes=''.join(f'<line x1="100" y1="100" x2="{100+40*__import__("math").cos(i*1.2566):.1f}" y2="{100+40*__import__("math").sin(i*1.2566):.1f}" stroke="{G2}" stroke-width="10" stroke-linecap="round"/>' for i in range(5))
A['tyre']=svg(c(100,100,76)+c(100,100,70,'none',f'stroke="{DK2}" stroke-width="8" stroke-dasharray="6 6"')+c(100,100,44,G3)+spokes+c(100,100,10,G1))
A['sneaker']=svg(p('M30 140 C30 112 44 96 64 92 L92 88 C100 100 112 108 128 112 L160 120 C172 124 178 132 172 142 Z',MI)
  +p('M64 92 C70 82 86 80 92 88 L88 96 C80 92 72 94 66 98 Z',DK2)+r(26,84,10,30,4,DK2)
  +s('M58 130 C90 118 122 122 152 134',W,4)+s('M96 98 L104 94',W,3)+s('M104 104 L112 100',W,3)+s('M112 110 L120 106',W,3)
  +p('M20 140 H170 C184 140 188 152 178 158 H28 C18 158 14 146 20 140 Z','#f4f5f7')+r(20,154,160,8,4))
A['dress']=svg(s('M84 30 L86 52',"#1f3f7a",5)+s('M116 30 L114 52',"#1f3f7a",5)+p('M80 50 H120 L116 92 H84 Z','#1f3f7a')
  +p('M84 92 H116 L152 172 Q100 184 48 172 Z','#1f3f7a')+r(82,86,36,9,3,'#c9a85c')
  +s('M94 100 L82 170',"#5f86c8",3)+s('M106 100 L120 170',"#5f86c8",3))
A['bed']=svg(r(24,56,42,108,8,BR)+r(24,134,158,24,6,'#a8743f')+r(58,112,122,26,8,'#f4f5f7')+r(62,94,38,22,9,W)
  +p('M92 104 H174 Q184 104 184 114 V140 H92 Z','#3f86ea')+s('M120 108 V138','#9cc2f7',3)+r(28,158,8,14,2)+r(170,158,8,14,2))
A['office_chair']=svg(r(70,22,60,76,18)+r(78,30,44,58,12,DK2)+s('M58 96 V80 H68',G1,6)+s('M142 96 V80 H132',G1,6)
  +r(56,98,88,24,11,DK2)+r(96,122,8,26,0,G2)+s('M100 150 L52 164',G1,7)+s('M100 150 L148 164',G1,7)+s('M100 150 L74 172',G1,7)+s('M100 150 L126 172',G1,7)
  +c(52,166,6)+c(148,166,6)+c(74,174,6)+c(126,174,6))
A['lamp']=svg(r(94,98,12,56,0,GO)+r(64,150,72,16,8,GO)+p('M70 38 H130 L152 100 H48 Z','#ffd978')+s('M72 44 L58 94','#ffe9a8',4))
A['exercise_bike']=svg(r(26,166,148,8,4)+c(56,140,24,G3)+c(56,140,9,G1)+s('M64 150 L96 92 L142 160',DK,10)
  +s('M126 132 L136 76',DK,8)+r(118,64,44,12,6,DK2)+s('M78 122 L64 52',DK,8)+s('M50 48 H82',DK,8)+r(56,58,22,14,3,MI)
  +c(104,130,9,DK2)+s('M104 130 L114 142',G1,4))
A['tent']=svg(s('M22 160 L8 172',G1,2)+s('M178 160 L192 172',G1,2)+s('M100 40 L100 26',DK,4)
  +p('M22 160 L100 40 L178 160 Z','#3f86ea')+p('M100 40 L178 160 H138 Z','#2f6fd0')+p('M100 84 L78 160 H122 Z',DK2))
A['desk']=svg(r(56,48,42,30,3)+r(60,52,34,22,2,'#5fa8f5')+r(50,78,54,5,2,G2)+r(18,84,164,14,4,'#c98a4b')
  +r(28,98,10,76,2)+r(162,98,10,76,2)+r(118,98,46,50,4,'#b07a40')+r(132,118,18,4,2,G1)+r(132,134,18,4,2,G1))
A['laptop']=svg(r(38,46,124,86,8,DK)+r(46,54,108,70,3,'#5fa8f5')+p('M46 54 L98 54 L64 124 L46 124 Z',W,'fill-opacity="0.16"')
  +p('M20 138 H180 L170 156 H30 Z',G3)+r(84,142,32,5,2,G1))
A['printer']=svg(r(62,26,76,52,4,'#f4f5f7')+r(28,70,144,64,12,'#e9ecef')+r(44,82,30,8,4,G2)+c(152,86,4,MI)+c(140,86,4,G2)
  +r(44,102,112,10,5,DK)+r(54,106,92,46,3,W)+s('M64 122 H136',G3,3)+s('M64 132 H122',G3,3)+r(40,146,120,18,6,G3))
A['router']=svg(s('M52 120 L40 50',DK,7)+s('M100 118 L100 42',DK,7)+s('M148 120 L160 50',DK,7)
  +r(24,114,152,40,13,'#f4f5f7')+c(52,134,4,MI)+c(70,134,4,MI)+c(88,134,4,YE)+r(120,130,36,8,4,G3)+r(40,154,14,6,2,DK)+r(146,154,14,6,2,DK))

# The drawings a tile of the home page uses (the picture the owner kept on 2026-11-23).
USED = (
    'air_fryer', 'air_purifier', 'bed', 'boot', 'chainsaw', 'coffee_machine',
    'dehumidifier', 'desk', 'dress', 'drill', 'dumbbell', 'headphones',
    'heater', 'kettle', 'lamp', 'laptop', 'lawn_mower', 'microwave',
    'mitre_saw', 'office_chair', 'perfume', 'pressure_washer', 'printer', 'robot_vacuum',
    'router', 'sneaker', 'sofa', 'toy_blocks', 'tyre', 'watch',
)

# ---- backgrounds: clear layers laid over a tile's plain colour ----
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400" preserveAspectRatio="xMidYMid slice">'
B = {}


def save(name, body):
    B[name] = HEAD + body + '</svg>'


stripes = ''.join(f'<rect x="{x}" y="0" width="14" height="400" fill="url(#rib)"/>' for x in range(0, 400, 20))

# ribs with a glowing ring; plain colour inside the ring (the rows of tiles)
save('ov_ring.svg',
     '<defs><linearGradient id="rib" x1="0" y1="0" x2="1" y2="0">'
     '<stop offset="0" stop-color="#000000" stop-opacity="0.14"/><stop offset="0.45" stop-color="#ffffff" stop-opacity="0.26"/>'
     '<stop offset="1" stop-color="#000000" stop-opacity="0.08"/></linearGradient>'
     '<mask id="hole"><rect width="400" height="400" fill="#ffffff"/><circle cx="200" cy="200" r="158" fill="#000000"/></mask>'
     '<radialGradient id="inner" cx="0.5" cy="0.42" r="0.5"><stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/>'
     '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'
     '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="9"/></filter></defs>'
     '<g mask="url(#hole)">' + stripes + '</g>'
     '<circle cx="200" cy="200" r="158" fill="url(#inner)"/>'
     '<circle cx="200" cy="200" r="154" fill="none" stroke="#fff4d6" stroke-width="26" stroke-opacity="0.55" filter="url(#soft)"/>'
     '<circle cx="200" cy="200" r="154" fill="none" stroke="#fff8e8" stroke-width="9"/>')

# a diagonal light streak; the lower-right half a touch lighter (the banners)
save('ov_streak.svg',
     '<defs><filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>'
     '<radialGradient id="glow" cx="0.5" cy="0.5" r="0.6"><stop offset="0" stop-color="#ffffff" stop-opacity="0.25"/>'
     '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>'
     '<polygon points="400,0 400,400 0,400" fill="#ffffff" fill-opacity="0.10"/>'
     '<rect width="400" height="400" fill="url(#glow)"/>'
     '<line x1="-20" y1="420" x2="420" y2="-20" stroke="#fff6dc" stroke-width="22" stroke-opacity="0.55" filter="url(#soft)"/>'
     '<line x1="-20" y1="420" x2="420" y2="-20" stroke="#fffaf0" stroke-width="5"/>')

# faint ribs and a calm studio light (the tiles)
soft = ''.join(f'<rect x="{x}" y="0" width="16" height="400" fill="url(#rib)"/>' for x in range(0, 400, 25))
save('ov_soft.svg',
     '<defs><linearGradient id="rib" x1="0" y1="0" x2="1" y2="0">'
     '<stop offset="0" stop-color="#000000" stop-opacity="0.05"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.12"/>'
     '<stop offset="1" stop-color="#000000" stop-opacity="0.04"/></linearGradient>'
     '<radialGradient id="glow" cx="0.5" cy="0.45" r="0.62"><stop offset="0" stop-color="#ffffff" stop-opacity="0.38"/>'
     '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>'
     + soft + '<rect width="400" height="400" fill="url(#glow)"/>')


def main(argv):
    everything = '--all' in argv
    places = [a for a in argv if not a.startswith('--')]
    root = places[0] if places else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'home')
    art, ov = os.path.join(root, 'art'), os.path.join(root, 'ov')
    os.makedirs(art, exist_ok=True)
    os.makedirs(ov, exist_ok=True)
    names = sorted(A) if everything else list(USED)
    for name in names:
        with open(os.path.join(art, name + '.svg'), 'w', encoding='utf-8') as handle:
            handle.write(A[name])
    for name, text in sorted(B.items()):
        with open(os.path.join(ov, name), 'w', encoding='utf-8') as handle:
            handle.write(text)
    print(len(names), 'drawings in', art)
    print(len(B), 'backgrounds in', ov)


if __name__ == '__main__':
    main(sys.argv[1:])
