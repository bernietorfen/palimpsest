"""Verify public assets not already covered by a cold-restore receipt."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from studio.preserve import sha256
from studio.verify_choir_download import BASE,PublicRedirect


def main(args):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',args.tag):raise ValueError('Invalid release tag')
    receipt_path,prior_path,output=map(Path,(args.receipt,args.prior,args.report))
    if output.exists():raise FileExistsError(output)
    receipt=json.loads(receipt_path.read_text());prior=json.loads(prior_path.read_text())
    assert receipt['repository']==prior['repository']=='bernietorfen/palimpsest'
    assert prior['release']==args.tag and prior['receipt_sha256']==sha256(receipt_path)
    assets={item['name']:item for item in receipt['assets']};verified={}
    for item in prior['public_downloads']:
        expected=assets[item['name']];assert item['bytes']==expected['bytes'] and item['sha256']==expected['sha256'];verified[item['name']]=item
    remaining=[item for name,item in assets.items() if name not in verified]
    if args.max_bytes<0 or sum(item['bytes'] for item in remaining)>args.max_bytes:raise ValueError('Remaining assets exceed the explicit download budget')
    downloaded=[]
    for item in remaining:
        assert Path(item['name']).name==item['name'];digest=hashlib.sha256();size=0
        request=urllib.request.Request(BASE+args.tag+'/'+item['name'],headers={'User-Agent':'palimpsest-public-verification'})
        with urllib.request.build_opener(PublicRedirect()).open(request,timeout=120) as response:
            assert response.status==200
            for chunk in iter(lambda:response.read(256*1024),b''):
                size+=len(chunk)
                if size>item['bytes']:raise ValueError('Oversized public asset')
                digest.update(chunk)
        assert size==item['bytes'] and digest.hexdigest()==item['sha256'],item['name']
        downloaded.append({'name':item['name'],'bytes':size,'sha256':digest.hexdigest()})
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'tag':args.tag,'receipt_sha256':sha256(receipt_path),'prior_cold_receipt_sha256':sha256(prior_path),'previously_verified_assets':len(verified),'new_public_downloads':downloaded,'total_public_assets_verified':len(verified)+len(downloaded),'all_release_assets_covered':len(verified)+len(downloaded)==len(assets),'temporary_media_files':0,'scope':'Unauthenticated streamed verification of the remaining assets, combined with the exact earlier cold-restore receipt. Already verified downloads are not repeated.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--prior',required=True);p.add_argument('--tag',required=True);p.add_argument('--report',required=True);p.add_argument('--max-bytes',type=int,default=10_000_000);main(p.parse_args())
