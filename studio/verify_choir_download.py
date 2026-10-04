"""Cold-download the public two-act installation and scientific record on RunPod."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
from urllib.parse import urlparse
import zipfile
from studio.preserve import sha256
from studio.verify_pressure_edition import safe

BASE='https://github.com/bernietorfen/palimpsest/releases/download/'
EDITIONS={'v2.0.0':('palimpsest-choir-edition.json','choir-record-manifest.json','choir-scientific-record.tar.gz'),
          'v2.1.0':('palimpsest-observer-edition.json','observer-record-manifest.json','observer-scientific-record.tar.gz'),
          'v2.2.0':('palimpsest-moving-observer-edition.json','moving-observer-record-manifest.json','moving-observer-record.tar.gz')}
ALLOWED={'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        target=urlparse(newurl)
        if target.scheme!='https' or target.hostname not in ALLOWED:raise ValueError('Unexpected public delivery host')
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def download(item,out,tag):
    path=out/item['name'];assert path.name==item['name']
    request=urllib.request.Request(BASE+tag+'/'+path.name,headers={'User-Agent':'palimpsest-cold-recovery'})
    digest=hashlib.sha256();size=0
    with urllib.request.build_opener(PublicRedirect()).open(request,timeout=180) as source,path.open('xb') as target:
        for block in iter(lambda:source.read(1024*1024),b''):
            size+=len(block)
            if size>item['bytes']:raise ValueError('Oversized download')
            digest.update(block);target.write(block)
    assert size==item['bytes'] and digest.hexdigest()==item['sha256'],path.name
    return {'name':path.name,'bytes':size,'sha256':digest.hexdigest()}


def restore_record(root,destination,expected,archive_name='choir-scientific-record.tar.gz',manifest_name='choir-record-manifest.json'):
    destination.mkdir();seen=set();embedded=None;total=0
    inventory={item['path']:item for item in expected['files']};assert len(inventory)==len(expected['files'])
    with tarfile.open(root/archive_name,'r|gz') as archive:
        for member in archive:
            relative=safe(member.name)
            if not member.isfile() or member.name in seen:raise ValueError('Unexpected record member')
            seen.add(member.name)
            if member.name==manifest_name:
                with archive.extractfile(member) as stream:embedded=stream.read()
                continue
            item=inventory[member.name];assert member.size==item['bytes']
            path=destination/relative;path.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
            with archive.extractfile(member) as source,path.open('xb') as target:
                for block in iter(lambda:source.read(1024*1024),b''):size+=len(block);digest.update(block);target.write(block)
            assert size==item['bytes'] and digest.hexdigest()==item['sha256'],member.name
            total+=size
    assert seen==set(inventory)|{manifest_name} and embedded==(root/manifest_name).read_bytes()
    (destination/manifest_name).write_bytes(embedded)
    return {'files':len(seen),'bytes':total+len(embedded),'every_file_restored_and_hashed':True}


def restore_installation(root,destination,expected):
    destination.mkdir();inventory={item['path']:item for item in expected['files']};assert len(inventory)==len(expected['files']);total=0
    with zipfile.ZipFile(root/'palimpsest-two-acts.zip') as archive:
        names=archive.namelist();assert len(names)==len(set(names)) and set(names)==set(inventory)|{'installation-content.json'}
        assert archive.read('installation-content.json')==(root/'installation-content.json').read_bytes()
        for name,item in inventory.items():
            info=archive.getinfo(name);assert info.file_size==item['bytes'] and not info.flag_bits&1
            target=destination/safe(name);target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
            with archive.open(info) as source,target.open('xb') as output:
                for block in iter(lambda:source.read(1024*1024),b''):size+=len(block);digest.update(block);output.write(block)
            assert size==item['bytes'] and digest.hexdigest()==item['sha256'],name
            total+=size
        raw=archive.read('installation-content.json');(destination/'installation-content.json').write_bytes(raw)
    return {'files':len(names),'bytes':total+len(raw),'every_file_restored_and_hashed':True}


def main(args):
    receipt_path,report_path=Path(args.receipt),Path(args.report)
    if report_path.exists():raise FileExistsError(report_path)
    receipt=json.loads(receipt_path.read_text());assert receipt['repository']=='bernietorfen/palimpsest'
    assets={item['name']:item for item in receipt['assets']}
    edition_name,record_name,archive_name=EDITIONS[args.tag]
    names=[edition_name,'palimpsest-checksums.sha256',record_name,'installation-content.json',archive_name,'palimpsest-two-acts.zip']
    if sum(assets[name]['bytes'] for name in names)>2_000_000_000:raise ValueError('Download budget exceeded')
    downloaded=[]
    with tempfile.TemporaryDirectory(prefix='choir-public-cold-',dir='backups') as temporary:
        root=Path(temporary)
        for name in names[:4]:downloaded.append(download(assets[name],root,args.tag))
        manifest=json.loads((root/names[0]).read_text());record=json.loads((root/names[2]).read_text());installation=json.loads((root/names[3]).read_text())
        assert record['source_commit']==installation['source_commit']==manifest['source_commit']
        checksums={name:digest for digest,name in (line.split('  ',1) for line in (root/names[1]).read_text().splitlines())}
        assert checksums=={**{item['name']:item['sha256'] for item in manifest['files']},names[0]:assets[names[0]]['sha256']}
        for name in names[2:]:assert checksums[name]==assets[name]['sha256']
        downloaded.append(download(assets[names[4]],root,args.tag));scientific=restore_record(root,root/'scientific',record,archive_name,record_name)
        assert scientific['files']==manifest['scientific_archive_files'];shutil.rmtree(root/'scientific');(root/names[4]).unlink()
        downloaded.append(download(assets[names[5]],root,args.tag));portable=restore_installation(root,root/'portable',installation)
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'repository':receipt['repository'],'release':args.tag,'source_commit':manifest['source_commit'],'receipt_sha256':sha256(receipt_path),'public_downloads':downloaded,'scientific_record':scientific,'portable_installation':portable,'temporary_files_removed':True,'execution_host':'RunPod','scope':'Unauthenticated public delivery, complete byte hashes, fresh extraction and every member hash. Independent analyses and browser checks have separate receipts.'}
    report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--report',required=True);p.add_argument('--tag',choices=tuple(EDITIONS),default='v2.0.0');main(p.parse_args())
