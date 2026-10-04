"""Independently reconstruct the offset diagnostic with per-pair vector norms."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
from studio.preserve import sha256


def close(a,b,tolerance=1e-12):
    assert np.isfinite(a) and np.isfinite(b) and abs(float(a)-float(b))<=tolerance,(a,b)


def main(args):
    root,output=Path(args.study),Path(args.output)
    if output.exists():raise FileExistsError(output)
    manifest=json.loads((root/'manifest.json').read_text())
    for item in manifest['files']:
        path=root/item['path'];assert path.resolve().is_relative_to(root.resolve()) and sha256(path)==item['sha256'] and path.stat().st_size==item['bytes']
    report=json.loads((root/'report.json').read_text());source=Path(report['study']);assert sha256(source/'manifest.json')==report['study_manifest_sha256']
    arrays=[]
    for rate in report['rates']:
        name=f'rate-{rate:03d}/readouts.npz';assert sha256(source/name)==report['input_sha256'][name];data=np.load(source/name);assert data['orders'].tolist()==report['orders'];arrays.append(data['pitch_hz'][:,0].astype(float).reshape(24,2,-1))
    saved=np.load(root/'geometry.npz');n=arrays[0].shape[-1];orders=report['orders'];matrix_error=0.;algebra_error=0.;receivers=[]
    for r in range(2):
        coarse,fine=arrays[0][:,r],arrays[1][:,r];delta=fine-coarse;common=sum(delta)/24;residual=delta-common
        assert np.allclose(saved[f'receiver_{r+1}_common'].ravel(),common,rtol=0,atol=1e-12)
        assert np.allclose(saved[f'receiver_{r+1}_residual'].reshape(24,n),residual,rtol=0,atol=1e-12)
        original=np.empty((24,24));translated=np.empty((24,24))
        for i in range(24):
            for j in range(24):
                original[i,j]=np.linalg.norm(fine[i]-coarse[j])/np.sqrt(n)
                translated[i,j]=np.linalg.norm(fine[i]-common-coarse[j])/np.sqrt(n)
        expected=report['receivers'][r]
        for name,matrix in (('raw',original),('translated',translated)):
            stored=saved[f'receiver_{r+1}_'+('raw' if name=='raw' else 'translated')+'_distance'];matrix_error=max(matrix_error,float(np.max(np.abs(stored-matrix))));chosen=matrix.argmin(axis=1)
            assert expected[name]['predicted_orders']==[orders[i] for i in chosen] and expected[name]['own_nearest']==int((chosen==np.arange(24)).sum())
            assert expected[name]['all_unique']==bool(np.all((matrix==matrix.min(axis=1)[:,None]).sum(axis=1)==1))
            assert np.max(np.abs((np.sort(matrix,axis=1)[:,1]-np.sort(matrix,axis=1)[:,0])-expected[name]['nearest_margin_hz']))<1e-12
        total=float(np.sum(delta*delta)/(24*n));common_size=float(np.dot(common,common)/n);rest=float(np.sum(residual*residual)/(24*n))
        for key,value in (('rms_step_discrepancy_hz',np.sqrt(total)),('rms_common_offset_hz',np.sqrt(common_size)),('rms_history_specific_residual_hz',np.sqrt(rest)),('common_fraction_of_mean_squared_discrepancy',common_size/total)):
            close(value,expected[key])
        close(total,common_size+rest)
        wrong=original.argmin(axis=1);assert len(expected['wrong_match_decomposition'])==int((wrong!=np.arange(24)).sum())
        for item in expected['wrong_match_decomposition']:
            h,j=orders.index(item['actual']),orders.index(item['raw_choice']);assert wrong[h]==j and h!=j;d=coarse[h]-coarse[j]
            terms=[np.dot(d,d)/n,2*np.dot(common,d)/n,2*np.dot(residual[h],d)/n]
            actual=original[h,j]**2-original[h,h]**2;algebra_error=max(algebra_error,abs(actual-sum(terms)))
            for key,value in zip(('coarse_pair_squared_hz','common_offset_term_squared_hz','history_specific_term_squared_hz'),terms):close(value,item[key])
            close(actual,item['raw_wrong_minus_own_squared_hz']);close(translated[h,j]**2-translated[h,h]**2,item['translated_wrong_minus_own_squared_hz'])
        receivers.append({'receiver':r+1,'raw_own_matches':expected['raw']['own_nearest'],'translated_own_matches':expected['translated']['own_nearest'],'common_fraction':common_size/total})
    assert matrix_error<1e-12 and algebra_error<1e-12
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'diagnostic_manifest_sha256':sha256(root/'manifest.json'),'rates':report['rates'],'files_hashed':len(manifest['files']),'maximum_matrix_error_hz':matrix_error,'maximum_contrast_identity_error_squared_hz':algebra_error,'receivers':receivers,'scope':'Separate per-pair Euclidean norm reconstruction of all diagnostic distances, labels, margins, common/residual components and wrong-match contrasts. The full balanced collection defines the translation; original raw-reader results remain unchanged.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',default='artifacts/studies/observer-offset-001');p.add_argument('--output',default='research/observer-offset-verified-001.json');main(p.parse_args())
