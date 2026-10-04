"""Inspect all notebook text bounds and produce bounded remote review sheets."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw
from pypdf import PdfReader
from studio.preserve import sha256


def main(args):
    pdf=Path(args.pdf);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    reader=PdfReader(pdf);assert len(reader.pages)==18
    subprocess.run(['pdftotext','-bbox',str(pdf),str(out/'bounds.html')],check=True)
    root=ET.parse(out/'bounds.html').getroot();ns={'x':'http://www.w3.org/1999/xhtml'}
    bounds=[]
    for n,page in enumerate(root.findall('.//x:page',ns),1):
        words=page.findall('x:word',ns);assert words
        b=[min(float(w.attrib[k]) for w in words) for k in ('xMin','yMin')]+[max(float(w.attrib[k]) for w in words) for k in ('xMax','yMax')]
        assert b[0]>=44 and b[2]<=820 and b[1]>=18 and b[3]<=635,(n,b)
        bounds.append({'page':n,'words':len(words),'bounds':b})
    text=' '.join(('\n'.join(p.extract_text() for p in reader.pages)).split())
    for phrase in ['forty-eight','0.7352%','1.704590','1.09e-13','The frozen model separates two questions','No supported perceptual audition']:
        assert phrase in text,phrase
    subprocess.run(['pdftoppm','-jpeg','-jpegopt','quality=82','-scale-to','1000',str(pdf),str(out/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    files=sorted(out.glob('page-*.jpg'));assert len(files)==18
    contact=Image.new('RGB',(1000,1600),'#d7d1c5');draw=ImageDraw.Draw(contact)
    for i,path in enumerate(files):
        with Image.open(path) as original:
            thumb=original.copy();thumb.thumbnail((320,240));x=10+(i%3)*330;y=10+(i//3)*265;contact.paste(thumb,(x,y));draw.text((x,y+242),f'{i+1:02d}',fill='#293e42')
    contact.save(out/'contact.jpg',quality=88)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'pdf':str(pdf),'sha256':sha256(pdf),'pages':18,'text_bounds':bounds,'scope':'Every page rendered and all extracted words checked against page margins; contact sheet and selected pages receive visual review separately.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--output',required=True);main(p.parse_args())
