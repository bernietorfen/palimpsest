"""Package both acts with local media and a loopback-only range server."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zipfile
from studio.preserve import sha256

BASE='https://github.com/bernietorfen/palimpsest/releases/download/'
EXTRAS={
    'palimpsest-viewing.mp4':'artwork/public-edition-001/palimpsest-viewing-1080p.mp4',
    'palimpsest-notebook.pdf':'artwork/public-edition-001/palimpsest-notebook.pdf',
    'palimpsest-complete-notebook.pdf':'artwork/complete-edition-002/palimpsest-complete-notebook.pdf',
    'a-mark-at-three-scales-print.pdf':'artwork/complete-edition-002/a-mark-at-three-scales-print.pdf',
    'a-choir-of-absences-notebook.pdf':'artwork/masters/a-choir-of-absences-notebook.pdf',
    'received-histories-companion.pdf':'artwork/received-history-art-001/received-histories-companion.pdf',
    'received-histories-print.pdf':'artwork/received-history-art-001/received-histories-print.pdf',
    'the-observer-companion.pdf':'artwork/observer-art-002/the-observer-companion.pdf',
    'the-origin-moves-print.pdf':'artwork/observer-art-002/the-origin-moves-print.pdf',
}
REPLACEMENTS={
    BASE+'v1.0.0/palimpsest-viewing-1080p.mp4':'/assets/generated/palimpsest-viewing.mp4',
    BASE+'v1.0.0/palimpsest-notebook.pdf':'/assets/generated/palimpsest-notebook.pdf',
    BASE+'v1.3.0/palimpsest-complete-notebook.pdf':'/assets/generated/palimpsest-complete-notebook.pdf',
    BASE+'v1.3.0/a-mark-at-three-scales-print.pdf':'/assets/generated/a-mark-at-three-scales-print.pdf',
    BASE+'v2.0.0/a-choir-of-absences-notebook.pdf':'/assets/generated/a-choir-of-absences-notebook.pdf',
    BASE+'v2.0.0/received-histories-companion.pdf':'/assets/generated/received-histories-companion.pdf',
    BASE+'v2.0.0/received-histories-print.pdf':'/assets/generated/received-histories-print.pdf',
    BASE+'v2.1.0/the-observer-companion.pdf':'/assets/generated/the-observer-companion.pdf',
    BASE+'v2.1.0/the-origin-moves-print.pdf':'/assets/generated/the-origin-moves-print.pdf',
}


def main(args):
    out=Path(args.output)
    if out.exists():raise FileExistsError(out)
    for name in EXTRAS.values():
        if not Path(name).is_file():raise FileNotFoundError(name)
    if not Path('site/assets/generated/choir-viewing.mp4').is_file():raise FileNotFoundError('Second film is not staged')
    # The two older frozen editions supply their own independent input hashes.
    for folder,manifest in [('artwork/public-edition-001','palimpsest-edition.json'),('artwork/complete-edition-002','palimpsest-complete-edition.json')]:
        records=json.loads((Path(folder)/manifest).read_text())['files'];expected={r['name']:r for r in records}
        for source in EXTRAS.values():
            p=Path(source)
            if p.parent==Path(folder):
                r=expected[p.name];assert p.stat().st_size==r['bytes'] and sha256(p)==r['sha256']
    files={}
    for p in sorted(Path('site').rglob('*')):
        if not p.is_file():continue
        if p.is_symlink() or any(part.startswith('.') for part in p.parts):raise ValueError(p)
        if str(p) in ('site/vercel.json','site/assets/generated/edition.json'):continue
        if p.suffix in ('.html','.js','.json','.css') and 'assets' not in p.parts:
            content=p.read_text()
            for before,after in REPLACEMENTS.items():content=content.replace(before,after)
            if str(p)=='site/second-act.js':
                content=content.replace(BASE+'v2.0.0/choir-${name}.glb','/assets/generated/choir-${name}.glb')
            files[str(p)]=content.encode()
        else:files[str(p)]=p
    for name,source in EXTRAS.items():files['site/assets/generated/'+name]=Path(source)
    for catalog_name in ('edition.json','choir-edition.json'):
        key='site/'+catalog_name;catalog=json.loads(files[key])
        for entry in catalog['downloads']:
            if entry['url'].startswith('https://'):entry['detail']='Online / '+entry['detail']
        files[key]=(json.dumps(catalog,indent=2)+'\n').encode()
    files['serve.py']=Path('studio/serve_site.py').read_text().replace('Viewing room on RunPod loopback port','Viewing room on loopback port').encode()
    start=f'''PALIMPSEST / TWO ACTS
Codex / 3-4 October 2026

Extract this ZIP into an empty directory on an authorized computer.
From the extracted directory, run:

  python3 serve.py --site site --port 8080

Open http://127.0.0.1:8080/ in a modern browser on that same computer.
Stop the server with Ctrl+C. It listens only on the loopback interface.
The included server supports byte ranges for seeking through the films.
Opening the HTML directly as file: is unsupported by browser origin rules.

SECOND ACT / A choir of absences
The complete 4:48 film; the seven-body playable choir; The witness, a matched
before/after listening piece; three turnable sculptures; an eighteen-page
artist's notebook; the received-history print and four-page research companion;
the observer print and its three-page companion.
Use a deliberate click to start sound. The live material
can be saved to a JSON file and restored later; tab recovery is bounded.

FIRST ACT / An instrument that becomes its own score
The complete 7:12 film; its original playable surface; all 120 audible
histories; the pressure explorer; three turnable sculptures; the original
and complete notebooks; the three-grid print. These works remain in their
own first-act room.

Both films, all playing and listening assets, fonts, examples, sculptures
for the browser and the books are included. The experience requires no
external connection. Optional catalog links marked Online lead to the
larger 4K films, lossless sound, full sculpture masters, prints, complete
scientific records and source. External authorship references also need
a connection. Download glTF in the second-act viewer saves its included
browser mesh; the larger master remains an optional online download.

A modern browser with WebGL2 and Web Audio is required for the instruments.
The films and PDF books remain separate files. Sound requires interaction.
This is an invented numerical material, not a physical fracture simulation.

Source: https://github.com/bernietorfen/palimpsest/tree/{args.source_commit}
Exact file digests: installation-content.json.
Typeface license: site/assets/generated/font-license.txt.
'''.encode()
    files['START-HERE.txt']=start
    out.mkdir(parents=True);archive_path=out/'palimpsest-two-acts.zip';records=[]
    with zipfile.ZipFile(archive_path,'x') as archive:
        for name,source in sorted(files.items()):
            if isinstance(source,bytes):
                size=len(source);digest=hashlib.sha256(source).hexdigest();archive.writestr(name,source,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
            else:
                before=source.stat();size=before.st_size;digest=sha256(source)
                compressed=source.suffix in ('.mp4','.m4a','.jpg','.png','.woff2','.pdf','.glb')
                archive.write(source,name,compress_type=zipfile.ZIP_STORED if compressed else zipfile.ZIP_DEFLATED,compresslevel=None if compressed else 6)
                after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
            records.append({'path':name,'bytes':size,'sha256':digest})
        content={'source_commit':args.source_commit,'files':records,'portable_changes':'Both films, three notebooks, both research companions and three print PDFs are local. Second-act glTF download uses the included browser mesh. Optional external catalog entries are marked Online. Range server binds only to loopback; Vercel configuration is omitted.'}
        raw=(json.dumps(content,indent=2)+'\n').encode();archive.writestr('installation-content.json',raw,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    (out/'installation-content.json').write_bytes(raw);(out/'START-HERE.txt').write_bytes(start)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'source_commit':args.source_commit,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.iterdir()) if p.is_file()],'installation_files':len(records)+1,'uncompressed_bytes':sum(r['bytes'] for r in records)}
    (out/'two-acts-installation.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'path':str(archive_path),'bytes':archive_path.stat().st_size,'files':len(records)+1}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artwork/two-acts-installation-002');p.add_argument('--source-commit',required=True);main(p.parse_args())
