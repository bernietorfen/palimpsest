"""Bounded visual and text-margin proofs of the received-history print and book."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw
from pypdf import PdfReader
from studio.preserve import sha256


def bounds(pdf,out,expected,limits):
    reader=PdfReader(pdf);assert len(reader.pages)==expected
    target=out/(pdf.stem+'-bounds.html')
    subprocess.run(['pdftotext','-bbox',str(pdf),str(target)],check=True)
    root=ET.parse(target).getroot();ns={'x':'http://www.w3.org/1999/xhtml'};records=[]
    for n,page in enumerate(root.findall('.//x:page',ns),1):
        words=page.findall('x:word',ns);assert words
        b=[min(float(w.attrib[k]) for w in words) for k in ('xMin','yMin')]+[max(float(w.attrib[k]) for w in words) for k in ('xMax','yMax')]
        assert b[0]>=limits[0] and b[1]>=limits[1] and b[2]<=limits[2] and b[3]<=limits[3],(n,b,limits)
        records.append({'page':n,'words':len(words),'bounds':b})
    return records,' '.join(' '.join(p.extract_text() for p in reader.pages).split())


def main(args):
    root,out=Path(args.art),Path(args.output);out.mkdir(parents=True,exist_ok=False)
    pdf=root/'received-histories-companion.pdf'
    book,text=bounds(pdf,out,4,(44,18,820,635))
    for phrase in ('eighteen','twenty-four','0.002101487','6.735325e-6','768','six rust crosses'):assert phrase in text,phrase
    poster,_=bounds(root/'received-histories-print.pdf',out,1,(68,40,1372,1755))
    subprocess.run(['pdftoppm','-jpeg','-jpegopt','quality=84','-scale-to','1200',str(pdf),str(out/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    files=sorted(out.glob('page-*.jpg'));assert len(files)==4
    contact=Image.new('RGB',(1240,980),'#d7d1c5');draw=ImageDraw.Draw(contact)
    for i,path in enumerate(files):
        with Image.open(path) as original:
            thumb=original.copy();thumb.thumbnail((600,450));x=10+(i%2)*620;y=10+(i//2)*490;contact.paste(thumb,(x,y));draw.text((x,y+455),f'{i+1:02d}',fill='#293e42')
    contact.save(out/'contact.jpg',quality=88)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'art':str(root),'companion_sha256':sha256(pdf),'poster_sha256':sha256(root/'received-histories-print.pdf'),'companion_bounds':book,'poster_bounds':poster,'scope':'All five PDF pages checked for extracted-word margins. Four book pages rendered for visual review; print reviewed from its separate bounded preview.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--art',default='artwork/received-history-art-001');p.add_argument('--output',default='artwork/received-history-proof-001');main(p.parse_args())
