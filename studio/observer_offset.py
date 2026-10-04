"""A declared post-result diagnostic: shared timestep offset versus order geometry."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from studio.preserve import sha256


def cross(a,b):
    return np.sqrt(np.mean((a[:,None]-b[None,:])**2,axis=(-2,-1)))


def choices(distance,orders):
    nearest=distance.argmin(axis=1);unique=(distance==distance.min(axis=1)[:,None]).sum(axis=1)==1
    return {'own_nearest':int((nearest==np.arange(24)).sum()),'all_unique':bool(unique.all()),'predicted_orders':[orders[i] for i in nearest],'nearest_margin_hz':(np.sort(distance,axis=1)[:,1]-np.sort(distance,axis=1)[:,0]).tolist()}


def main(args):
    root,out=Path(args.study),Path(args.output);out.mkdir(parents=True,exist_ok=False)
    protocol=json.loads((root/'protocol.json').read_text());rates=protocol['rates'];assert len(rates)==2
    manifest=json.loads((root/'manifest.json').read_text());expected={item['path']:item for item in manifest['files']}
    data={};inputs={}
    for rate in rates:
        relative=f'rate-{rate:03d}/readouts.npz';path=root/relative;item=expected[relative]
        assert path.stat().st_size==item['bytes'] and sha256(path)==item['sha256']
        loaded=np.load(path);data[rate]=loaded['pitch_hz'][:,0].astype(np.float64);inputs[relative]=sha256(path)
        assert loaded['orders'].tolist()==protocol['orders'] and loaded['conditions'].tolist()[0]=='connected'
    orders=protocol['orders'];reports=[];arrays={}
    for receiver in range(2):
        coarse,fine=data[rates[0]][:,receiver],data[rates[1]][:,receiver]
        delta=fine-coarse;common=delta.mean(axis=0);residual=delta-common;translated=fine-common
        total_squared=float(np.mean(delta**2));common_squared=float(np.mean(common**2));residual_squared=float(np.mean(residual**2))
        variance_error=abs(total_squared-common_squared-residual_squared);assert variance_error<1e-14
        raw,centered=cross(fine,coarse),cross(translated,coarse)
        saved=np.load(root/f'cross-rate-receiver-{receiver+1}.npz')['rms_hz'];assert np.array_equal(raw,saved)
        invariant_error=float(np.max(np.abs(cross(fine,fine)-cross(translated,translated))));assert invariant_error<3e-12
        selected=raw.argmin(axis=1);decomposition=[]
        for h,j in enumerate(selected):
            if h==j:continue
            d=coarse[h]-coarse[j];separation=float(np.mean(d*d));common_term=float(2*np.mean(common*d));residual_term=float(2*np.mean(residual[h]*d))
            observed=float(raw[h,j]**2-raw[h,h]**2);algebra_error=abs(observed-separation-common_term-residual_term);assert algebra_error<1e-12
            decomposition.append({'actual':orders[h],'raw_choice':orders[j],'raw_wrong_minus_own_squared_hz':observed,'coarse_pair_squared_hz':separation,'common_offset_term_squared_hz':common_term,'history_specific_term_squared_hz':residual_term,'translated_wrong_minus_own_squared_hz':float(centered[h,j]**2-centered[h,h]**2),'identity_error_squared_hz':algebra_error})
        reports.append({'receiver':receiver+1,'raw':choices(raw,orders),'translated':choices(centered,orders),'rms_step_discrepancy_hz':float(np.sqrt(total_squared)),'rms_common_offset_hz':float(np.sqrt(common_squared)),'rms_history_specific_residual_hz':float(np.sqrt(residual_squared)),'common_fraction_of_mean_squared_discrepancy':common_squared/total_squared if total_squared else 0.,'variance_identity_error_squared_hz':variance_error,'within_rate_translation_error_hz':invariant_error,'wrong_match_decomposition':decomposition})
        for name,value in (('common',common),('residual',residual),('raw_distance',raw),('translated_distance',centered)):arrays[f'receiver_{receiver+1}_{name}']=value
    np.savez_compressed(out/'geometry.npz',**arrays,orders=np.array(orders),rates=np.array(rates))
    sources={}
    for relative in ('studio/observer_offset.py','research/OBSERVER-REFINEMENT-PLAN.md'):
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);sources[relative]=sha256(Path(relative))
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'study':str(root),'study_manifest_sha256':sha256(root/'manifest.json'),'input_sha256':inputs,'source_sha256':sources,'rates':rates,'orders':orders,'receivers':reports,'scope':'Post-result geometric diagnostic using the complete balanced 24-history collection. A shared translation preserves each within-rate geometry. It is not an independently usable reader of one unknown history and does not replace the original raw-reader score.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    files=[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()];(out/'manifest.json').write_text(json.dumps({'files':files},indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',default='artifacts/studies/received-histories-002');p.add_argument('--output',default='artifacts/studies/observer-offset-001');main(p.parse_args())
