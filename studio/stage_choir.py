"""Stage the reviewed second-act images and sculpture views, entirely on RunPod."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from studio.preserve import sha256


def main():
    output=Path('site/assets/generated');records=[]
    copies={
      'choir-encounter.jpg':'artwork/choir-plates-001/02-encounter-scene.jpg',
      'choir-after.jpg':'artwork/choir-plates-001/03-after-scene.jpg',
      'choir-before.jpg':'artwork/choir-plates-001/01-before-scene.jpg',
      'choir-source.jpg':'artwork/choir-plates-001/the-source-view.jpg',
      'choir-encounter.glb':'artwork/choir-sculptures/encounter-web-002/choir.glb',
      'choir-after.glb':'artwork/choir-sculptures/after-web/choir.glb',
      'choir-source.glb':'artwork/choir-sculptures/source-web/choir.glb',
    }
    for name,relative in copies.items():
        source=Path(relative);destination=output/name
        if destination.exists():raise FileExistsError(destination)
        shutil.copy2(source,destination);digest=sha256(source);assert digest==sha256(destination)
        records.append({'path':str(destination),'source':relative,'bytes':destination.stat().st_size,'sha256':digest})
    # The original files remain in their immutable public edition. Verify that
    # identity before taking their duplicate bytes out of the hosted directory.
    manifest=json.loads(Path('artwork/public-edition-001/palimpsest-edition.json').read_text())
    originals={item['name']:item for item in manifest['files']};removed=[]
    for name,edition in [('palimpsest-viewing.mp4','palimpsest-viewing-1080p.mp4'),('palimpsest-notebook.pdf','palimpsest-notebook.pdf')]:
        path=output/name;record=originals[edition]
        if path.stat().st_size!=record['bytes'] or sha256(path)!=record['sha256']:raise ValueError('The frozen first-edition asset identity differs')
        removed.append({'path':str(path),'bytes':record['bytes'],'sha256':record['sha256'],'public_asset':edition})
        path.unlink()
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'files':records,'duplicate_hosted_files_removed':removed,
            'scope':'The first film and first notebook remain downloadable from v1.0.0; permanent deployment redirects preserve their former asset URLs. The portable second edition must include local copies and rewrite the film URL.'}
    Path('research/choir-site-assets-001.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
