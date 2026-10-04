"""Rebuild the received-history artwork from restored data at identical paths."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from studio.preserve import sha256


def main(args):
    proof,report=Path(args.proof),Path(args.report)
    if report.exists():raise FileExistsError(report)
    original=proof/'artwork/received-history-art-001';reference=proof/'artwork/received-history-art-001-reference'
    if reference.exists():raise FileExistsError(reference)
    original.rename(reference)
    run=subprocess.run([sys.executable,'-m','studio.received_history_art'],cwd=proof,env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'},capture_output=True,text=True)
    (proof/'received-art-rebuild.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError('Restored art generation failed')
    names=['received-histories-print.pdf','received-histories-6000x7500.png','received-histories.jpg','received-histories-companion.pdf','who-recognizes-the-order.png','the-smallest-difference.png']
    files=[]
    for name in names:
        digest=sha256(original/name);assert digest==sha256(reference/name),name
        files.append({'name':name,'bytes':(original/name).stat().st_size,'sha256':digest})
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'proof':str(proof),'files':files,'all_byte_identical':True,'scope':'Print PDF, 45-megapixel PNG, preview, four-page companion PDF and both evidence PNGs rebuilt from restored data at identical relative paths. Figure PDFs have ordinary Matplotlib container timestamps and are not asserted byte-identical.'}
    report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--proof',default='artwork/choir-proof-001');p.add_argument('--report',default='research/received-art-rebuild-001.json');main(p.parse_args())
