"""Check interactive distances against separate direct norms of all saved replies."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
from studio.preserve import sha256


def main(args):
    path,output=Path(args.data),Path(args.output)
    if output.exists():raise FileExistsError(output)
    data=json.loads(path.read_text())
    for name,digest in data['input_sha256'].items():assert sha256(Path(name))==digest
    root=Path('artifacts/studies/received-histories-002');replies=[]
    for rate in (96,192):
        saved=np.load(root/f'rate-{rate:03d}/readouts.npz');assert saved['orders'].tolist()==data['orders'];replies.append(saved['pitch_hz'][:,0,0].astype(float).reshape(24,-1))
    coarse,fine=replies;n=coarse.shape[1];common=sum(fine-coarse)/24
    a,b,c=np.array(data['a']),np.array(data['b']),data['c'];assert a.shape==b.shape==(24,24)
    points=set(np.linspace(0,1,17).tolist());tol=data['squared_hz_tie_tolerance'];assert tol==1e-15
    for event in data['events']:
        alpha=event['alpha'];assert 0<alpha<1
        points.update([max(0,alpha-1e-7),alpha,min(1,alpha+1e-7)])
    worst=0.;at={}
    for alpha in sorted(points):
        distances=np.empty((24,24))
        for h in range(24):
            for j in range(24):
                residual=fine[h]-alpha*common-coarse[j];distances[h,j]=np.dot(residual,residual)/n
        polynomial=a-2*alpha*b+alpha*alpha*c;worst=max(worst,float(np.max(np.abs(polynomial-distances))));assert worst<1e-12
        direct=[np.flatnonzero(row<=min(row)+tol).tolist() for row in distances]
        compact=[np.flatnonzero(row<=min(row)+tol).tolist() for row in polynomial];assert direct==compact
        at[alpha]=direct
    for event in data['events']:
        h,alpha=event['history'],event['alpha'];assert at[alpha][h]==event['at']
        assert at[max(0,alpha-1e-7)][h]==[event['before']] and at[min(1,alpha+1e-7)][h]==[event['after']]
    assert at[0]==data['raw_choices'] and at[1]==data['aligned_choices']
    for row in data['rows']:
        h,j=row['history'],row['rival'];direction=coarse[j]-coarse[h];squared=float(direction@direction)
        for key,reply in (('raw_projection',fine[h]),('aligned_projection',fine[h]-common)):
            projection=float((reply-coarse[h])@direction/squared);assert abs(projection-row[key])<1e-12
        assert abs(np.sqrt(squared/n)-row['pair_separation_hz'])<1e-12
    # Once a history is its own unique nearest candidate at both ends of a
    # transition-free interval, affine candidate contrasts cannot reverse inside.
    boundaries=[0]+sorted({event['alpha'] for event in data['events']})+[1]
    for left,right in zip(boundaries,boundaries[1:]):
        probes=np.linspace(left+(right-left)*1e-5,right-(right-left)*1e-5,7)
        labels=[np.argmin(a-2*alpha*b,axis=1).tolist() for alpha in probes];assert all(label==labels[0] for label in labels)
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'data_sha256':sha256(path),'coordinates_per_response':n,'direct_probe_positions':len(points),'candidate_norms_checked':len(points)*24*24,'maximum_squared_distance_error_hz2':worst,'all_nearest_sets_match':True,'transition_count':len(data['events']),'transitions':data['events'],'raw_own_matches':sum(v==[i] for i,v in enumerate(at[0])),'aligned_own_matches':sum(v==[i] for i,v in enumerate(at[1])),'exact_pair_projections_verified':True,'scope':'Independent direct dot-product norms in the complete recorded space at regular positions and on both sides of every displayed boundary, including tied nearest sets at crossings. No material simulation or unknown-history inference is introduced.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',default='artwork/observer-interaction-001/observer-origin-v1.json');p.add_argument('--output',default='research/observer-interaction-verified-001.json');main(p.parse_args())
