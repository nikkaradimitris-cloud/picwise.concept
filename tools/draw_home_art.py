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

A['toaster']=svg(p('M68 70 H96 Q102 70 102 62 V46 Q102 36 90 36 H74 Q62 36 62 46 V62 Q62 70 68 70 Z','#e9c98f')
  +p('M110 70 H138 Q144 70 144 62 V50 Q144 40 132 40 H116 Q104 40 104 50 V62 Q104 70 110 70 Z','#e9c98f')
  +r(34,66,132,88,16,'#e9ecef',f'stroke="{G3}" stroke-width="2"')+r(56,62,44,10,5)+r(104,62,44,10,5)
  +r(48,88,60,6,3,G3)+c(140,112,10,W,f'stroke="{G2}" stroke-width="3"')+c(140,112,3,MI)+r(162,84,10,26,4)
  +r(46,154,22,8,3)+r(132,154,22,8,3))
A['blender']=svg(r(60,120,80,44,10)+c(100,142,10,YE)+r(70,164,60,6,3,DK2)+s('M138 46 Q168 50 160 96',G2,8)
  +p('M64 34 H136 L126 120 H74 Z','#cfe1fa',f'stroke="{G2}" stroke-width="2"')+p('M70 78 H130 L126 120 H74 Z',MI,'fill-opacity="0.55"')
  +r(78,44,7,60,3.5,W,'fill-opacity="0.6"')+r(58,24,84,12,6)+r(88,14,24,12,5,DK2))
A['mattress']=svg(p('M20 100 L58 64 H180 L142 100 Z','#ffffff',f'stroke="{G3}" stroke-width="2"')
  +r(20,100,122,50,9,'#f4f5f7',f'stroke="{G3}" stroke-width="2"')+p('M142 100 L180 64 V114 L142 150 Z','#e5e9ee',f'stroke="{G3}" stroke-width="2"')
  +r(20,119,122,12,0,MI)+p('M142 119 L180 83 V95 L142 131 Z',OR)
  +''.join(c(x,y,2.6,G2) for x,y in ((76,76),(110,76),(144,76),(62,89),(96,89),(130,89))))
A['hoodie']=svg(p('M70 44 Q100 20 130 44 L126 66 Q100 52 74 66 Z',RE)
  +p('M74 60 Q100 48 126 60 L152 80 L174 132 L152 142 L138 108 V166 Q100 174 62 166 V108 L48 142 L26 132 L48 80 Z',OR)
  +p('M86 62 Q100 74 114 62 Q100 54 86 62 Z','#16357a')+s('M92 70 V98',W,3)+s('M108 70 V98',W,3)
  +p('M74 128 H126 L132 152 H68 Z',ORL)+r(62,158,76,10,4,RE))

# The kinds added on 2026-11-27 (owner: «πρόσθεσε κατηγορίες που ενδιαφέρουν τον κόσμο και
# λείπουν από την αρχική», «δεν θέλω να αλλάξουμε τα γραφικά»): drawn as the ones above, the
# same colours, the same light.
SKY='#5fa8f5'; WOOD='#c98a4b'; WOOD2='#b07a40'; NAVY='#1f3f7a'; NAVY2='#16357a'; SKIN='#f2d7b6'; PALE='#f4f5f7'; PALE2='#e9ecef'
def e(cx,cy,rx,ry,f=DK,extra=''):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{f}" {extra}/>'
A['monitor']=svg(r(18,34,164,104,8,DK)+r(26,42,148,88,3,SKY)+p('M26 42 L96 42 L58 130 L26 130 Z',W,'fill-opacity="0.16"')
  +r(92,138,16,20,0,G2)+r(62,156,76,10,5,G3))
A['keyboard']=svg(r(14,72,172,76,10,PALE2,f'stroke="{G3}" stroke-width="2"')
  +''.join(r(25+i*15,82+row*15,11,11,2.5,G2) for row in range(3) for i in range(10))
  +r(25,127,11,11,2.5,G2)+r(40,127,11,11,2.5,G2)+r(55,127,90,11,2.5,G1)+r(149,127,11,11,2.5,G2)+r(164,127,11,11,2.5,MI))
A['desktop_pc']=svg(r(58,22,84,152,9,DK)+r(68,32,64,8,4,DK2)+r(68,46,64,8,4,DK2)+c(100,76,8,MI)+c(100,76,3,W)
  +''.join(r(72,y,56,4,2,DK2) for y in (104,114,124,134,144,154))+r(64,174,14,6,2)+r(122,174,14,6,2))
A['smartphone']=svg(r(60,16,80,168,15,DK)+r(66,24,68,152,9,SKY)+p('M66 24 L112 24 L82 176 L66 176 Z',W,'fill-opacity="0.16"')
  +r(88,28,24,6,3,DK)+r(86,166,28,4,2,W,'fill-opacity="0.75"'))
A['tablet']=svg(r(36,22,128,156,13,DK)+r(45,31,110,138,5,SKY)+p('M45 31 L112 31 L70 169 L45 169 Z',W,'fill-opacity="0.16"')
  +c(100,26.5,2,G1))
A['smartwatch']=svg(r(76,10,48,180,12,DK2)+r(58,56,84,88,22,DK)+r(66,64,68,72,15,SKY)
  +s('M84 110 A17 17 0 1 1 116 110',W,5)+r(96,116,8,8,2,YE)+r(142,88,8,18,3,G2))
A['console']=svg(r(22,76,156,58,13,DK)+r(34,86,132,6,3,MI)+r(38,106,74,5,2.5,DK2)+c(138,110,6,G2)+c(156,110,6,YE)
  +r(38,134,18,6,2)+r(144,134,18,6,2))
A['video_game']=svg(r(52,24,96,152,9,OR)+r(52,24,96,20,9,RE)+r(60,48,80,120,4,PALE)
  +r(76,88,48,28,14,DK)+r(84,98,10,4,1,G3)+r(87,95,4,10,1,G3)+c(110,98,3,YE)+c(116,106,3,MI)+r(72,130,56,5,2.5,G3)+r(80,142,40,5,2.5,G3))
A['vr_headset']=svg(s('M30 92 Q100 34 170 92',DK2,11)+r(28,78,144,66,26,DK)+r(42,90,116,42,18,DK2)+r(58,104,84,10,5,MI)
  +p('M88 144 Q100 128 112 144 Z',G1))
A['jacket']=svg(p('M70 38 L100 56 L130 38 L156 60 L178 132 L154 142 L140 106 V170 H60 V106 L46 142 L22 132 L44 60 Z',NAVY)
  +p('M70 38 L100 56 L86 78 Z',NAVY2)+p('M130 38 L100 56 L114 78 Z',NAVY2)+s('M100 58 V168',G3,3)
  +s('M70 132 L86 124',"#5f86c8",3)+s('M130 132 L114 124',"#5f86c8",3)+r(60,162,80,9,3,NAVY2))
A['jeans']=svg(p('M60 24 H140 L152 176 H110 L100 82 L90 176 H48 Z','#3f6cb5')+r(60,24,80,13,3,'#2f5596')
  +s('M70 44 Q82 58 94 46','#9cc2f7',2.5)+s('M130 44 Q118 58 106 46','#9cc2f7',2.5)+s('M100 38 V80','#2f5596',3)+c(100,30.5,3.5,GO)
  +s('M54 164 H92','#9cc2f7',2.5)+s('M108 164 H146','#9cc2f7',2.5))
A['handbag']=svg(s('M70 86 Q100 14 130 86',"#6e4520",9)+p('M42 82 H158 L170 160 Q100 174 30 160 Z','#a8743f')
  +p('M42 82 H158 L161 104 Q100 116 39 104 Z',BR)+r(90,100,20,16,4,GO)+r(96,105,8,6,2,'#a8894a'))
A['shoe']=svg(p('M26 140 C24 112 40 98 62 98 L88 98 C98 112 116 122 138 126 L164 132 C178 136 182 144 178 152 H26 Z',BR)
  +p('M62 98 L88 98 C92 104 97 109 103 113 L82 124 C72 118 64 108 62 98 Z','#6e4520')
  +s('M84 104 L96 100',SKIN,3)+s('M90 111 L102 107',SKIN,3)+s('M96 118 L108 114',SKIN,3)+r(22,150,160,11,5))
A['washing_machine']=svg(r(38,22,124,152,10,PALE,f'stroke="{G3}" stroke-width="2"')+s('M40 52 H160',G3,3)
  +c(58,37,8,G2)+r(108,30,40,14,3,INK)+r(114,35,16,4,2,MI)+c(100,112,46,G3)+c(100,112,38,DK2)+c(100,112,31,SKY)
  +p('M70 116 Q85 106 100 116 T130 116 A31 31 0 0 1 70 116 Z',OR)+r(46,174,14,6,2)+r(140,174,14,6,2))
A['dishwasher']=svg(r(38,22,124,152,10,PALE2,f'stroke="{G3}" stroke-width="2"')+r(38,22,124,26,10,DK2)
  +c(56,35,4,MI)+c(70,35,4,G2)+r(112,30,34,10,3,INK)+r(60,58,80,8,4,G1)
  +c(100,120,32,W,f'stroke="{G3}" stroke-width="3"')+c(100,120,19,PALE,f'stroke="{G3}" stroke-width="2"')
  +r(46,174,14,6,2)+r(140,174,14,6,2))
A['tumble_dryer']=svg(r(38,22,124,152,10,PALE,f'stroke="{G3}" stroke-width="2"')+s('M40 52 H160',G3,3)
  +r(52,30,40,14,3,INK)+r(58,35,16,4,2,YE)+c(142,37,8,G2)+c(100,112,46,G3)+c(100,112,38,DK2)+c(100,112,31,DK)
  +s('M86 122 q7 -9 0 -18',YE,4)+s('M100 122 q7 -9 0 -18',YE,4)+s('M114 122 q7 -9 0 -18',YE,4)+r(46,174,14,6,2)+r(140,174,14,6,2))
A['cooker']=svg(r(38,30,124,144,8,PALE2,f'stroke="{G3}" stroke-width="2"')+r(34,24,132,14,5,DK)
  +''.join(c(58+i*21,54,6,G1) for i in range(5))+r(56,70,88,7,3.5,G2)+r(52,84,96,58,7,DK)
  +p('M60 92 L92 92 L74 134 L60 134 Z',W,'fill-opacity="0.12"')+s('M40 154 H160',G3,3)+r(46,174,14,6,2)+r(140,174,14,6,2))
A['vacuum_cleaner']=svg(s('M62 104 C40 30 128 22 150 64 L164 148',DK,8)+r(138,146,50,16,7,DK2)
  +r(30,98,104,62,28,OR)+r(46,108,62,8,4,ORL)+c(112,152,20)+c(112,152,8,G2)+c(52,160,9)+r(40,120,22,10,5,DK2))
A['fan']=svg(r(62,162,76,12,6)+r(95,118,10,46,0,G2)+c(100,70,56,PALE2,f'stroke="{G1}" stroke-width="5"')
  +e(100,44,14,24,MI)+e(100,44,14,24,MI,'transform="rotate(120 100 70)"')+e(100,44,14,24,MI,'transform="rotate(240 100 70)"')
  +c(100,70,10,DK)+c(100,70,4,G2))
A['wardrobe']=svg(r(44,18,112,150,6,WOOD)+r(44,18,112,10,4,WOOD2)+s('M100 30 V160',"#8b5a2b",3)
  +r(88,84,5,24,2.5,DK)+r(107,84,5,24,2.5,DK)+r(44,158,112,10,3,WOOD2)+r(52,168,10,8,1)+r(138,168,10,8,1))
A['table']=svg(r(16,72,168,15,6,WOOD)+r(32,87,136,11,2,WOOD2)+r(32,98,11,76,2,BR)+r(157,98,11,76,2,BR)
  +r(56,98,7,52,2,"#6e4520")+r(137,98,7,52,2,"#6e4520"))
A['chair']=svg(r(62,22,62,12,5,WOOD)+r(62,22,9,84,3,WOOD2)+r(115,22,9,84,3,WOOD2)+r(80,34,6,62,2,WOOD)+r(98,34,6,62,2,WOOD)
  +r(54,98,92,16,6,WOOD)+r(58,114,9,60,2,BR)+r(133,114,9,60,2,BR)+r(74,114,6,40,2,"#6e4520")+r(120,114,6,40,2,"#6e4520"))
A['ring']=svg(c(100,118,50,'none',f'stroke="{GO}" stroke-width="13"')+c(100,118,50,'none','stroke="#a8894a" stroke-width="3"')
  +p('M84 66 L92 52 H108 L116 66 L100 84 Z','#9cc2f7')+p('M92 52 H108 L104 66 H96 Z',W,'fill-opacity="0.7"')+r(88,64,24,6,2,GO))
A['necklace']=svg(s('M38 26 Q100 168 162 26',GO,4)+s('M52 26 Q100 138 148 26','#a8894a',2)
  +p('M86 110 L100 94 L114 110 L100 142 Z',MI)+p('M92 110 L100 100 L108 110 Z',W,'fill-opacity="0.6"')+c(100,92,5,GO))
A['earrings']=svg(s('M62 34 V66',GO,4)+c(62,30,6,GO)+p('M62 62 C48 82 42 94 42 106 A20 20 0 0 0 82 106 C82 94 76 82 62 62 Z',MI)
  +e(55,102,5,9,W,'fill-opacity="0.55"')
  +s('M138 34 V66',GO,4)+c(138,30,6,GO)+p('M138 62 C124 82 118 94 118 106 A20 20 0 0 0 158 106 C158 94 152 82 138 62 Z',MI)
  +e(131,102,5,9,W,'fill-opacity="0.55"'))
A['bracelet']=svg(e(100,100,70,48,'none',f'stroke="{GO}" stroke-width="13"')+e(100,100,70,48,'none','stroke="#a8894a" stroke-width="3"')
  +c(100,148,12,MI)+c(100,148,5,W,'fill-opacity="0.7"')+c(70,143,6,GO)+c(130,143,6,GO))
A['bricks']=svg(''.join(r(40+i*34,84,22,18,4,OR2) for i in range(4))+r(28,98,144,64,7,OR)+r(38,108,124,8,4,ORL)
  +r(72,36,22,18,4,YE2)+r(106,36,22,18,4,YE2)+r(60,50,80,46,7,YE))
A['board_game']=svg(r(22,62,124,112,9,PALE,f'stroke="{G3}" stroke-width="2"')
  +''.join(r(34+col*34,74+row*30,32,28,3,(MI if (row+col)%2==0 else W)) for row in range(3) for col in range(3))
  +r(130,24,52,52,11,W,f'stroke="{G3}" stroke-width="2"')+c(144,38,5)+c(168,38,5)+c(156,50,5)+c(144,62,5)+c(168,62,5)
  +c(60,36,13,YE)+p('M44 72 L60 40 L76 72 Z',YE)+r(40,68,40,9,4,GO))
A['doll']=svg(p('M74 52 A26 28 0 0 1 126 52 V78 H118 V56 H82 V78 H74 Z',BR)+c(100,54,22,SKIN)+c(92,54,2.5)+c(108,54,2.5)
  +s('M94 63 Q100 68 106 63',"#6e4520",2)+s('M82 96 L60 124',SKIN,9)+s('M118 96 L140 124',SKIN,9)
  +r(88,146,9,30,3,SKIN)+r(103,146,9,30,3,SKIN)+p('M84 82 H116 L140 150 H60 Z',MI)+r(84,96,32,7,3,YE)+r(84,172,16,7,3)+r(100,172,16,7,3))
A['bike']=svg(c(50,128,34,'none',f'stroke="{DK}" stroke-width="7"')+c(150,128,34,'none',f'stroke="{DK}" stroke-width="7"')
  +s('M50 128 L82 78 H126 L150 128',OR,7)+s('M82 78 L104 128 H50',OR,7)+s('M104 128 L126 78',OR,7)
  +r(66,62,30,9,4.5)+s('M78 70 L82 78',DK,5)+s('M126 78 L122 58 H140',DK,6)+c(50,128,6,G2)+c(150,128,6,G2)+c(104,128,8,DK2))
A['treadmill']=svg(p('M14 152 H158 L166 168 H10 Z',DK)+r(22,146,130,8,4,G1)+s('M138 150 L158 58',G1,9)
  +r(132,42,52,22,7,DK)+r(140,47,26,12,3,MI)+s('M152 82 L108 96',G2,7)+c(28,168,6,DK2)+c(150,168,6,DK2))

A['camera']=svg(r(72,52,44,18,5,DK2)+r(26,64,148,96,14,DK)+r(26,92,148,34,0,DK2)+r(136,74,26,12,4,YE)
  +c(96,112,38,G3)+c(96,112,31,INK)+c(96,112,22,SKY)+p('M82 100 A18 18 0 0 1 100 92 L96 112 Z',W,'fill-opacity="0.35"')+c(40,78,5,MI))
A['speaker']=svg(r(54,18,92,156,14,DK)+c(100,58,18,DK2)+c(100,58,9,G1)+c(100,120,34,DK2)+c(100,120,24,G1)+c(100,120,10,DK)
  +c(100,164,3,MI))
A['projector']=svg(r(22,76,156,70,16,PALE,f'stroke="{G3}" stroke-width="2"')+c(72,111,26,G3)+c(72,111,19,INK)+c(72,111,11,SKY)
  +''.join(r(118,y,44,5,2.5,G3) for y in (92,102,112))+c(124,130,5,MI)+c(140,130,5,G2)+r(40,146,16,8,3)+r(144,146,16,8,3))

# The drawings a tile of the home page uses (the picture the owner kept on 2026-11-23).
USED = (
    'air_fryer', 'air_purifier', 'bed', 'boot', 'chainsaw', 'coffee_machine',
    'dehumidifier', 'desk', 'dress', 'drill', 'dumbbell', 'headphones',
    'heater', 'kettle', 'lamp', 'laptop', 'lawn_mower', 'microwave',
    'mitre_saw', 'office_chair', 'perfume', 'pressure_washer', 'printer', 'robot_vacuum',
    'router', 'sneaker', 'sofa', 'toy_blocks', 'tyre', 'watch',
    # The month's ten (mattress, hoodie) and a department's kinds (toaster, blender), 2026-11-24.
    'blender', 'hoodie', 'mattress', 'toaster',    # The kinds added on 2026-11-27, and five drawn before them that no tile had used.
    'angle_grinder', 'bike', 'camera', 'projector', 'soundbar', 'speaker', 'board_game', 'bracelet', 'bricks', 'chair', 'console', 'cooker',
    'desktop_pc', 'dishwasher', 'doll', 'earrings', 'fan', 'fridge', 'gamepad', 'handbag',
    'hedge_trimmer', 'jacket', 'jeans', 'keyboard', 'monitor', 'necklace', 'ring', 'shoe',
    'smartphone', 'smartwatch', 'tablet', 'table', 'tent', 'treadmill', 'tumble_dryer', 'tv',
    'vacuum_cleaner', 'video_game', 'vr_headset', 'wardrobe', 'washing_machine',
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
