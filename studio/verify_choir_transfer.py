"""Independently recompute every reported transfer outcome from saved arrays."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
from studio.preserve import sha256


def main(args):
    root=Path(args.study);manifest=json.loads((root/'manifest.json').read_text())
    for item in manifest['files']:
        path=root/item['path'];assert path.stat().st_size==item['bytes'];assert sha256(path)==item['sha256'],str(path)
    rows=[];maximum_error=0.;failures=[]
    for directory in sorted(root.glob('rate-*/phrase-*')):
        report=json.loads((directory/'report.json').read_text());data=np.load(directory/'probe-readouts.npz');pitches=data['pitch_hz'].astype(np.float64)
        assert pitches.shape==(289,6,3,12);assert np.array_equal(data['time'],np.arange(289)/24);assert np.isfinite(pitches).all()
        names=data['conditions'].tolist();initial=np.load(directory/'probe-initial.npz');written=np.load(directory/'written-state.npz')
        assert names==['connected','isolated','second-link-absent','inscription-erased','wear-erased','both-erased']
        assert written['steps']==30*report['rate']
        for i,name in enumerate(names):
            origin=3 if name=='isolated' else 6 if name=='second-link-absent' else 0
            for field in ('p','z'):
                expected=written[field][origin:origin+3].copy()
                if (field=='p' and name in ('inscription-erased','both-erased')) or (field=='z' and name in ('wear-erased','both-erased')):expected.fill(0)
                assert np.array_equal(initial[field][3*i:3*i+3],expected),(directory,name,field)
        for receiver in (1,2):
            differences=pitches[:,:,receiver,:]-pitches[:,1:2,receiver,:]
            values=np.linalg.norm(differences.reshape(289,6*12).reshape(289,6,12),axis=(0,2))/np.sqrt(289*12)
            saved=report['outcomes'][receiver-1]
            for index,name in enumerate(names):maximum_error=max(maximum_error,abs(float(values[index])-saved['rms_hz'][name]))
            assert np.max(np.abs(differences[:,5]))==0
            if receiver==2:assert np.max(np.abs(differences[:,2]))==0
            memory=float(np.linalg.norm(written['p'][receiver].astype(np.float64))/64)
            fatigue=float(written['z'][receiver].astype(np.float64).mean())
            admitted=values[0]>.01 and memory>0 and fatigue>0
            assert bool(admitted)==saved['admitted']
            if not admitted:failures.append({'directory':str(directory),'receiver':receiver})
            rows.append({'rate':report['rate'],'phrase':report['phrase'],'receiver':receiver,'rms_hz':float(values[0]),'memory_rms':memory,'wear_mean':fatigue})
    assert len(rows)==48;assert maximum_error<1e-12
    summary=json.loads((root/'summary.json').read_text())
    by_key={(r['rate'],r['phrase'],r['receiver']):r['rms_hz'] for r in rows}
    relative=max(abs(by_key[96,p,r]-by_key[192,p,r])/by_key[192,p,r] for p in range(12) for r in (1,2))
    assert abs(relative-summary['maximum_relative_timestep_discrepancy'])<1e-12
    for rate in (96,192):
        for receiver in (1,2):
            values=[r['rms_hz'] for r in rows if r['rate']==rate and r['receiver']==receiver]
            actual=summary['primary_ranges_hz'][str(rate)][receiver-1]
            for key,value in [('minimum',min(values)),('median',np.median(values)),('maximum',max(values))]:assert abs(actual[key]-value)<1e-12
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'files_hashed':len(manifest['files']),
            'receiver_cases':len(rows),'maximum_report_discrepancy_hz':maximum_error,'exact_negative_controls':True,
            'field_interventions_exact':True,'all_cases_admitted':not failures,'failures':failures,
            'primary_ranges_hz':summary['primary_ranges_hz'],'maximum_relative_timestep_discrepancy':relative,
            'scope':'Independent analysis of frozen arrays and exact field interventions. Does not independently reimplement the generating dynamics or establish a continuum result.'}
    with Path(args.output).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--study',default='artifacts/studies/choir-transfer-001');parser.add_argument('--output',default='research/choir-transfer-verified-001.json');main(parser.parse_args())
