from pathlib import Path
from PIL import Image, ImageDraw
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import json, re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/'upstream'
OUT = ROOT/'eva/assets'
OUT.mkdir(exist_ok=True)
colors = dict(window='#0c0b12', panel='#151020', surface='#241733',
              surface_hover='#39244f', surface_active='#50336c', outline='#62418a',
              text='#eeeff4', secondary='#b8abc9', dim='#9586a6', accent='#a4ff39',
              accent_hover='#c2ff77', on_accent='#141c0b', danger='#ff647c',
              warning='#ffa34d', overlay='#07060dcc', shadow='#00000088')
(OUT/'EVA-01.json').write_text(json.dumps({'base':'dark','colors':colors},indent=2)+'\n')
def rgb(s): return tuple(bytes.fromhex(s.lstrip('#')))
old = ['0f1114','15181c','1d2127','262b33','2f353f','2a3038','f2f4f6','a9b1bc','6e7784','1ed760','0a140e','144a2a']
new = [colors[k] for k in ('window','panel','surface','surface_hover','surface_active','outline','text','secondary','dim','accent','on_accent')] + ['#354e18']
mapping = dict(zip(map(rgb,old),map(rgb,new)))
z = ZipFile(SRC/'assets/skins/spotifast.wsz')
images = {}
for name in z.namelist():
    if name.endswith('.bmp'):
        im = Image.open(BytesIO(z.read(name))).convert('RGB')
        im.putdata([mapping.get(p,p) for p in im.getdata()])
        images[name[:-4]] = im

# Keep the original sprite coordinates and pixel font; draw new console artwork.
source = (SRC/'examples/default_skin.rs').read_text()
font = dict(re.findall(r"\('([A-Z0-9 :+.-])', \"([.#/]+)\"\)",source))
def text(im,x,y,value,color):
    d=ImageDraw.Draw(im)
    for n,c in enumerate(value):
        for dy,row in enumerate(font.get(c.upper(),'').split('/')):
            for dx,v in enumerate(row):
                if v=='#': d.point((x+n*5+dx,y+dy),fill=color)

green=rgb(colors['accent']); purple=rgb(colors['outline']); orange=rgb(colors['warning'])
panel=rgb(colors['panel']); surface=rgb(colors['surface']); dim=rgb(colors['dim'])
def title(im,x,y,w,h,label,active=True):
    d=ImageDraw.Draw(im)
    d.rectangle((x+17,y+2,x+w-35,y+h-3),fill=surface)
    start=x+(w-(len(label)*5-1))//2
    text(im,start,y+(h-5)//2,label,green if active else dim)
    for a,b in ((x+20,start-9),(start+len(label)*5+7,x+w-38)):
        if b>a:
            d.line((a,y+5,b,y+5),fill=purple)
            d.line((a,y+8,b,y+8),fill=purple)

im=images['titlebar']
for y in (0,15,57,72): title(im,27,y,275,14,'EVA-01 : AUDIO',y in (0,57))
for y in (29,42):
    ImageDraw.Draw(im).rectangle((46,y+3,143,y+10),fill=surface)
    text(im,47,y+4,'EVA-01',green if y==29 else dim)

im=images['main']; d=ImageDraw.Draw(im)
# The distinctive armour edges and caution band stay clear of every hit target.
d.rectangle((1,14,273,19),fill=surface)
for x in range(8,273):
    for y in range(15,19):
        if (x+y)%12<3: d.point((x,y),fill=purple)
d.line((1,20,1,114),fill=purple); d.line((273,20,273,114),fill=purple)
d.rectangle((8,108,265,113),fill=panel)
text(im,12,109,'NERV',orange); text(im,211,109,'UNIT 01',green)
for x in range(41,198):
    if (x//5)%2==0: d.line((x,110,x,111),fill=purple)
# Original geometric Unit-01 mask in the clickable logo position.
d.rectangle((251,90,268,106),fill=panel)
d.polygon([(255,92),(259,94),(265,91),(264,102),(260,106),(255,102)],fill=purple)
d.line((260,94,259,89),fill=green,width=1)
d.line((254,96,258,98),fill=green); d.line((261,98,265,95),fill=green)
d.point((260,102),fill=orange)

for y in (134,149): title(images['eqmain'],0,y,275,14,'AT FIELD : EQ',y==134)
for y in (0,21):
    im=images['pledit']; d=ImageDraw.Draw(im)
    d.rectangle((26,y+3,125,y+16),fill=panel)
    text(im,43,y+7,'NERV QUEUE',green if y==0 else dim)

entries={}
for stem,im in images.items():
    stream=BytesIO(); im.save(stream,format='BMP'); entries[stem+'.bmp']=stream.getvalue()
entries['pledit.txt']=b'[Text]\nNormal=#b8abc9\nCurrent=#a4ff39\nNormalBG=#0c0b12\nSelectedBG=#39244f\nFont=DejaVu Sans\n'
# 24 RGB entries: dark background, gradient spectrum, peaks, scope.
vis=[rgb('#0c0b12'),rgb('#241733')]
vis += [tuple(round(a+(b-a)*i/15) for a,b in zip(green,orange)) for i in range(16)]
vis += [purple,green,green,green,green,green]
entries['viscolor.txt']=('\n'.join(','.join(map(str,p)) for p in vis)+'\n').encode()
entries['LICENSE.txt']=(SRC/'LICENSE').read_bytes()
entries['EVA-01.txt']=b'EVA-01 Audio, custom classic skin for Sendoa, 2026-10-14.\nBased on the MIT-licensed Spotifast built-in skin by Carmine Paolino.\nOriginal geometric artwork; fan theme inspired by Evangelion.\n'
with ZipFile(OUT/'EVA-01.wsz','w',ZIP_DEFLATED) as dest:
    for name,data in entries.items(): dest.writestr(name,data)

# Compose a truthful, idle-state preview using the very same sprite tables.
sprites={n:(s,*map(int,(x,y,w,h))) for n,s,x,y,w,h in re.findall(r'(\w+) = \((\w+), (\d+), (\d+), (\d+), (\d+)\);',(SRC/'src/skin/sprites.rs').read_text())}
areas={n:tuple(map(int,(x,y,w,h))) for n,x,y,w,h in re.findall(r'(\w+) = \((\d+), (\d+), (\d+), (\d+)\);',(SRC/'src/skin/layout.rs').read_text())}
stems={'Main':'main','CButtons':'cbuttons','TitleBar':'titlebar','ShufRep':'shufrep','PosBar':'posbar','Volume':'volume','Balance':'balance','MonoSter':'monoster','PlayPaus':'playpaus','Numbers':'numbers','NumsEx':'nums_ex','Text':'text','PlEdit':'pledit','EqMain':'eqmain','EqEx':'eq_ex'}
preview=images['main'].copy()
def blit(n,area):
    s,x,y,w,h=sprites[n]; a=areas[area]
    preview.paste(images[stems[s]].crop((x,y,x+w,y+h)),(a[0],a[1]))
for n,a in [('TITLE_BAR_ACTIVE','TITLE_BAR'),('OPTIONS_BUTTON','OPTIONS_BUTTON'),('MINIMIZE_BUTTON','MINIMIZE_BUTTON'),('SHADE_BUTTON','SHADE_BUTTON'),('CLOSE_BUTTON','CLOSE_BUTTON'),('CLUTTER_BAR','CLUTTER_BAR'),('STATUS_STOPPED','STATUS'),('MONO_OFF','MONO'),('STEREO_ON','STEREO'),('EQ_OFF','EQ_BUTTON'),('PLAYLIST_OFF','PLAYLIST_BUTTON'),('POSITION_TRACK','POSITION'),('PREVIOUS','PREVIOUS'),('PLAY','PLAY'),('PAUSE','PAUSE'),('STOP','STOP'),('NEXT','NEXT'),('EJECT','EJECT'),('SHUFFLE_OFF','SHUFFLE'),('REPEAT_OFF','REPEAT')]: blit(n,a)
text(preview,111,27,'EVA-01 AUDIO : STANDBY',green)
for area in ('MINUTE_TENS','MINUTE_ONES','SECOND_TENS','SECOND_ONES'):
    a=areas[area]; preview.paste(images['nums_ex'].crop((0,0,9,13)),a[:2])
preview.resize((1100,464),Image.Resampling.NEAREST).save(OUT/'EVA-01-preview.png')

icon='''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect x="8" y="8" width="240" height="240" rx="48" fill="#0c0b12"/><path d="M45 78 95 104 120 90 164 100 212 62 193 180 137 220 70 178Z" fill="#62418a"/><path d="m120 103 13-80 17 78-13 19Z" fill="#a4ff39"/><path d="m65 113 54 23-8 13-39-17Zm89 24 44-31-7 23-34 21Z" fill="#a4ff39"/><path d="m114 176 22-19 20 17-17 25Z" fill="#ffa34d"/><path d="m92 189 41 30 42-32" fill="none" stroke="#a4ff39" stroke-width="5"/><path d="M24 38h38M24 38v28M232 218h-38M232 218v-28" fill="none" stroke="#a4ff39" stroke-width="5"/></svg>'''
(OUT/'eva-01-audio.svg').write_text(icon)
print('Tema, skin completa de 15 hojas, icono y vista previa creados.')
