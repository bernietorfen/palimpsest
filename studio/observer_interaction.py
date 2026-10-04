"""Exact affine decision paths for the visitor-controlled observation origin."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from studio.preserve import sha256

TOLERANCE=1e-15


def predictions(a,b,alpha):
    values=a-2*alpha*b
    return [np.flatnonzero(row<=row.min()+TOLERANCE).tolist() for row in values]


def transitions(a,b):
    events=[]
    for history in range(24):
        candidates={0.,1.}
        for j in range(24):
            for k in range(j):
                denominator=2*(b[history,j]-b[history,k])
                if denominator:
                    value=(a[history,j]-a[history,k])/denominator
                    if 0<value<1:candidates.add(float(value))
        candidates=sorted(candidates)
        segments=[]
        for left,right in zip(candidates,candidates[1:]):
            alpha=(left+right)/2;choice=int(np.argmin(a[history]-2*alpha*b[history]))
            if segments and segments[-1]['choice']==choice:segments[-1]['right']=right
            else:segments.append({'left':left,'right':right,'choice':choice})
        for left,right in zip(segments,segments[1:]):
            assert left['right']==right['left'];alpha=left['right'];tied=predictions(a,b,alpha)[history]
            assert left['choice'] in tied and right['choice'] in tied
            events.append({'history':history,'alpha':alpha,'before':left['choice'],'after':right['choice'],'at':tied})
    return sorted(events,key=lambda event:(event['alpha'],event['history']))


def main(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    root=Path('artifacts/studies/received-histories-002');report_path=Path('artifacts/studies/observer-offset-001/report.json');report=json.loads(report_path.read_text())
    reference=Path('artifacts/studies/observer-offset-001/geometry.npz');geometry=np.load(reference)
    coarse=np.load(root/'rate-096/readouts.npz')['pitch_hz'][:,0,0].astype(float).reshape(24,-1)
    fine=np.load(root/'rate-192/readouts.npz')['pitch_hz'][:,0,0].astype(float).reshape(24,-1)
    orders=report['orders'];assert coarse.shape==fine.shape==(24,3468)
    common=(fine-coarse).mean(axis=0);assert np.array_equal(common,geometry['receiver_1_common'].ravel())
    delta=fine[:,None]-coarse[None,:];a=np.mean(delta*delta,axis=-1);b=np.mean(delta*common,axis=-1);c=float(np.mean(common*common))
    events=transitions(a,b);rows=[]
    for item in report['receivers'][0]['wrong_match_decomposition']:
        h,j=orders.index(item['actual']),orders.index(item['raw_choice']);d=coarse[j]-coarse[h];length_squared=float(np.mean(d*d))
        raw=float(np.mean((fine[h]-coarse[h])*d)/length_squared)
        aligned=float(np.mean((fine[h]-common-coarse[h])*d)/length_squared)
        rows.append({'history':h,'rival':j,'raw_projection':raw,'aligned_projection':aligned,'pair_separation_hz':float(np.sqrt(length_squared))})
    inputs={str(path):sha256(path) for path in (root/'manifest.json',root/'rate-096/readouts.npz',root/'rate-192/readouts.npz',report_path,reference,Path('research/OBSERVER-INTERACTION.md'))}
    data={'version':1,'title':'The origin moves','orders':orders,'rates':[96,192],'receiver':1,'coordinates':3468,'squared_hz_tie_tolerance':TOLERANCE,'a':a.tolist(),'b':b.tolist(),'c':c,'rows':rows,'events':events,'raw_choices':predictions(a,b,0),'aligned_choices':predictions(a,b,1),'input_sha256':inputs,'scope':'One shared translation of the complete balanced finer-step collection. All nearest-candidate decisions use full recorded trajectories. The six visible strips are exact own/rival projections. This is not an unknown-history classifier, changed material or new simulation.'}
    assert sum(v==[i] for i,v in enumerate(data['raw_choices']))==18 and sum(v==[i] for i,v in enumerate(data['aligned_choices']))==24
    (out/'observer-origin-v1.json').write_text(json.dumps(data,indent=2)+'\n')
    for relative in ('studio/observer_interaction.py','research/OBSERVER-INTERACTION.md'):
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()]};(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(out),'data_sha256':sha256(out/'observer-origin-v1.json'),'events':events,'rows':rows}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artwork/observer-interaction-001');main(p.parse_args())
