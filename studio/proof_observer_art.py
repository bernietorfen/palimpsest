"""Render all three observer companion pages and check both PDF page margins."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw
from studio.proof_received_history_art import bounds
from studio.preserve import sha256


def main(args):
    root,out=Path(args.art),Path(args.output);out.mkdir(parents=True,exist_ok=False)
    pdf=root/'the-observer-companion.pdf';book,text=bounds(pdf,out,3,(44,18,820,635))
    for phrase in ('99.1753%','488','384','0.002128870','ordinary Euclidean','No recurrence theorem'):assert phrase in text,phrase
    poster,_=bounds(root/'the-origin-moves-print.pdf',out,1,(68,40,1372,1040))
    subprocess.run(['pdftoppm','-jpeg','-jpegopt','quality=85','-scale-to','1200',str(pdf),str(out/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    files=sorted(out.glob('page-*.jpg'));assert len(files)==3;files.append(root/'the-origin-moves.jpg')
    contact=Image.new('RGB',(1240,980),'#d7d1c5');draw=ImageDraw.Draw(contact)
    for i,path in enumerate(files):
        with Image.open(path) as original:
            thumb=original.copy();thumb.thumbnail((600,450));x=10+(i%2)*620;y=10+(i//2)*490;contact.paste(thumb,(x,y));draw.text((x,y+455),'Print' if i==3 else f'{i+1:02d}',fill='#293e42')
    contact.save(out/'contact.jpg',quality=88)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'art':str(root),'companion_sha256':sha256(pdf),'poster_sha256':sha256(root/'the-origin-moves-print.pdf'),'companion_bounds':book,'poster_bounds':poster,'scope':'All four PDF pages checked for extracted-word margins. Every companion page and the print rendered for visual inspection.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--art',default='artwork/observer-art-002');p.add_argument('--output',default='artwork/observer-proof-002');main(p.parse_args())
