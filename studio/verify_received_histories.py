"""Independent reconstruction of received-order distances and field interventions."""
import argparse
from datetime import datetime,timezone
import itertools
import json
from pathlib import Path
import numpy as np
from studio.preserve import sha256


def distance(a,b):
    delta=np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64)
    return float(np.sqrt(np.sum(delta*delta)/delta.size))


def check_number(actual,expected):
    if not np.isfinite(actual) or abs(float(actual)-float(expected))>1e-10:raise ValueError((actual,expected))


def main(args):
    root=Path(args.study);output=Path(args.output)
    if output.exists():raise FileExistsError(output)
    manifest=json.loads((root/'manifest.json').read_text());count=0
    for item in manifest['files']:
        path=root/item['path'];assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
        assert path.stat().st_size==item['bytes'] and sha256(path)==item['sha256'],path;count+=1
    protocol=json.loads((root/'protocol.json').read_text());summary=json.loads((root/'summary.json').read_text())
    orders=[''.join(p) for p in itertools.permutations('ABCD')];conditions=['connected','inscription-erased','wear-erased','both-erased']
    rates=tuple(protocol['rates']);assert rates in ((96,192),(192,384))
    assert protocol['orders']==orders and protocol['conditions']==conditions and protocol['batch_size']==1
    if rates!=(96,192):assert protocol['follow_up_plan']=='research/OBSERVER-REFINEMENT-PLAN.md'
    assert summary['orders']==orders
    admission=np.load(root/'admission.npz');admission_report=json.loads((root/'admission.json').read_text())
    reference_path=root.parent/'received-histories-001/admission.npz';assert sha256(reference_path)==admission_report['reference_sha256'];reference=np.load(reference_path)
    for key in ('u','v','p','z','bridge_u','bridge_v'):
        assert np.array_equal(admission[key+'_reference'],reference[key+'_single'])
        difference=float(np.max(np.abs(admission[key+'_reference'].astype(float)-admission[key+'_serial'])));assert difference<=2e-6;check_number(difference,admission_report['field_max_errors'][key])
    assert np.array_equal(admission['pitch_reference'],reference['pitch_single'])
    pitch_error=float(np.max(np.abs(admission['pitch_reference'].astype(float)-admission['pitch_serial'])));assert pitch_error<=1e-4 and admission_report['passed'];check_number(pitch_error,admission_report['pitch_max_error_hz'])
    arrays={};reconstructed={};maximum_matrix_error=0.;erased_error=0.;interventions=0
    for rate in rates:
        directory=root/f'rate-{rate:03d}';data=np.load(directory/'readouts.npz');pitches=data['pitch_hz'];fresh=data['fresh_pitch_hz']
        assert data['orders'].tolist()==orders and data['conditions'].tolist()==conditions
        assert pitches.shape==(24,4,2,289,12) and fresh.shape==(289,12)
        assert np.array_equal(data['time'],np.arange(289)/24) and np.isfinite(pitches).all() and np.isfinite(fresh).all()
        arrays[rate]=pitches;error=float(np.max(np.abs(pitches[:,3].astype(float)-fresh[None,None])))
        erased_error=max(erased_error,error);assert error<=1e-6
        for batch in range(24):
            folder=directory/f'batch-{batch:02d}';written=np.load(folder/'written-state.npz');initial=np.load(folder/'probe-initial.npz');report=json.loads((folder/'report.json').read_text())
            assert initial['orders'].tolist()==orders[batch:batch+1] and report['orders']==initial['orders'].tolist()
            assert int(written['steps'])==30*rate and written['gates'].shape==(2,) and np.all(written['gates']==1)
            assert int(initial['steps'])==0 and int(initial['index'])==0
            assert np.array_equal(initial['u'],initial['p'])
            for key in ('v','delay','echo_phase'):assert np.all(initial[key]==0)
            for key in ('p','z'):
                original=written[key].reshape(1,3,64,64)[:,1:];actual=initial[key][:-1].reshape(1,4,2,64,64)
                assert np.isfinite(original).all() and np.isfinite(actual).all()
                if key=='p':assert np.max(np.abs(original))<=np.float32(.8)
                else:assert np.min(original)>=0 and np.max(original)<=1
                for condition in range(4):
                    expected=original.copy()
                    if condition==3 or (condition==1 and key=='p') or (condition==2 and key=='z'):expected.fill(0)
                    assert np.array_equal(actual[:,condition],expected),(rate,batch,key,condition);interventions+=2
                assert np.all(initial[key][-1]==0)
            batch_error=float(np.max(np.abs(pitches[batch:batch+1,3].astype(float)-fresh[None,None])))
            check_number(batch_error,report['both_erased_max_error_hz'])
        saved=np.load(directory/'distances.npz')['rms_hz'];assert saved.shape==(4,2,24,24)
        reconstructed[str(rate)]={}
        for c,condition in enumerate(conditions):
            reconstructed[str(rate)][condition]={}
            for receiver in range(2):
                matrix=np.zeros((24,24));pairs=[]
                for a in range(24):
                    for b in range(a+1,24):
                        value=distance(pitches[a,c,receiver],pitches[b,c,receiver]);matrix[a,b]=matrix[b,a]=value;pairs.append((value,a,b))
                maximum_matrix_error=max(maximum_matrix_error,float(np.max(np.abs(matrix-saved[c,receiver]))))
                values=np.array([p[0] for p in pairs]);closest=min(pairs,key=lambda p:p[0]);report=summary['rates'][str(rate)]['observations'][condition][str(receiver+1)]
                assert report['pairs']==276 and report['closest_pair']==[orders[closest[1]],orders[closest[2]]]
                for name,value in [('minimum_hz',values.min()),('median_hz',np.median(values)),('maximum_hz',values.max())]:check_number(value,report[name])
                for ending in (1,2):
                    values_ending=np.array([v for v,a,b in pairs if orders[a][-ending:]==orders[b][-ending:]]);subset=report[f'same_last_{ending}'];assert len(values_ending)==subset['pairs']
                    for name,value in [('minimum_hz',values_ending.min()),('median_hz',np.median(values_ending)),('maximum_hz',values_ending.max())]:check_number(value,subset[name])
                reconstructed[str(rate)][condition][str(receiver+1)]={k:report[k] for k in ('minimum_hz','median_hz','maximum_hz','closest_pair')}
    cross=[]
    for receiver in range(2):
        matrix=np.array([[distance(arrays[rates[1]][a,0,receiver],arrays[rates[0]][b,0,receiver]) for b in range(24)] for a in range(24)])
        saved=np.load(root/f'cross-rate-receiver-{receiver+1}.npz')['rms_hz'];maximum_matrix_error=max(maximum_matrix_error,float(np.max(np.abs(matrix-saved))))
        chosen=np.argmin(matrix,axis=1);unique=bool(np.all((matrix==matrix.min(axis=1)[:,None]).sum(axis=1)==1));own=int(np.sum(chosen==np.arange(24)));report=summary['cross_rate'][receiver]
        assert report['receiver']==receiver+1 and report['own_nearest']==own and report['all_unique']==unique and report['predicted_orders']==[orders[i] for i in chosen]
        for name,values in [('own_distances_hz',np.diag(matrix)),('nearest_distances_hz',matrix[np.arange(24),chosen]),('nearest_margin_hz',np.sort(matrix,axis=1)[:,1]-np.sort(matrix,axis=1)[:,0])]:assert np.max(np.abs(values-report[name]))<=1e-10
        cross.append({'receiver':receiver+1,'own_nearest':own,'all_unique':unique,'misidentified':[{'actual':orders[i],'predicted':orders[chosen[i]]} for i in range(24) if chosen[i]!=i]})
    repeated=None
    if protocol.get('reference_study'):
        reference=Path(protocol['reference_study']);repeated=json.loads((root/'repeated-rate-admission.json').read_text());assert sha256(reference/'manifest.json')==repeated['reference_manifest_sha256']
        previous={item['path']:item for item in json.loads((reference/'manifest.json').read_text())['files']};checked=0
        for path in sorted((root/f'rate-{rates[0]:03d}').rglob('*.npz')):
            relative=str(path.relative_to(root));old=reference/relative;item=previous[relative];assert old.stat().st_size==item['bytes'] and sha256(old)==item['sha256']
            current,saved=np.load(path),np.load(old);assert set(current.files)==set(saved.files)
            for key in current.files:assert np.array_equal(current[key],saved[key]);checked+=1
        assert checked==repeated['arrays_checked'] and repeated['every_array_identical']
    gate=all(reconstructed[str(rate)]['connected']['2']['minimum_hz']>.001 for rate in rates) and cross[1]['own_nearest']==24 and cross[1]['all_unique'] and erased_error<=1e-6
    assert gate==summary['distant_receiver_gate_passed'] and maximum_matrix_error<1e-10
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'study_manifest_sha256':sha256(root/'manifest.json'),'verified_files':count,'rates':list(rates),'repeated_rate_admission':repeated,'orders':24,'pairwise_cases_per_receiver_and_condition':276,'checked_retained_field_interventions':interventions,
        'maximum_distance_reconstruction_error_hz':maximum_matrix_error,'both_erased_max_error_hz':erased_error,'field_interventions_exact':True,'distant_receiver_gate_passed':gate,'reconstructed':reconstructed,'cross_rate':cross,
        'scope':'Independent NumPy analysis of every saved trajectory and exact reconstruction of all initial field interventions. No independent reimplementation of the dynamics, audibility claim or continuum proof.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',default='artifacts/studies/received-histories-002');p.add_argument('--output',default='research/received-histories-verified-001.json');main(p.parse_args())
