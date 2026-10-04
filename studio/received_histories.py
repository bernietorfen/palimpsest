"""All 24 source-contact orders, read only after indirect writing and separation."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import itertools
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from studio.batched_material import BatchedMaterial
from studio.choir_material import MaterialChoir,Port,port_footprint
from studio.choir_transfer_study import chain
from studio.material import MaterialConfig
from studio.preserve import sha256
from studio.score import Gesture

TOKENS=((.165,.345,.85,1),(.215,.395,.78,1),(.190,.370,.92,-1),(.215,.345,.71,1))
ONSETS=(2.,8.,15.,22.)
ORDERS=tuple(itertools.permutations(range(4)))
CONDITIONS=('connected','inscription-erased','wear-erased','both-erased')
SOURCES=('studio/received_histories.py','studio/choir_transfer_study.py','studio/choir_material.py','studio/batched_material.py','studio/material.py','studio/score.py','research/RECEIVED-HISTORIES-PROTOCOL.md','research/RECEIVED-HISTORIES-REVISION-001.md')


def label(order):return ''.join('ABCD'[i] for i in order)


def contacts(orders,rate,seconds):
    values=np.zeros((seconds*rate,len(orders),4),dtype=np.float32)
    for history,order in enumerate(orders):
        for slot,token in enumerate(order):
            event=Gesture(ONSETS[slot],0,TOKENS[token][2],.7,.8,3.,TOKENS[token][3])
            values[:,history,token]=[event.at(step/rate) for step in range(seconds*rate)]
    return torch.tensor(values,device='cuda')


def make_choir(config,count):
    bridges=tuple(edge for i in range(count) for edge in chain(i*3))
    assert all(edge.first.body//3==edge.second.body//3 for edge in bridges)
    return MaterialChoir(config,count*3,bridges,beads=16)


def footprints():
    return torch.stack([port_footprint(Port(0,x,y,.16),64,device='cuda',dtype=torch.float32) for x,y,_,_ in TOKENS]).reshape(4,-1)


def write_step(choir,levels,maps,force,drive):
    force.zero_();force[::3]=(levels@maps).reshape(-1,64,64);choir.step(drive,contact_force=force)


def admission(output):
    cfg=MaterialConfig(size=64,dt=1/96,feedback=.08)
    one=make_choir(cfg,1);maps=footprints();values=contacts(ORDERS[:1],96,6)
    reference_path=Path('artifacts/studies/received-histories-001/admission.npz');reference=np.load(reference_path)
    force_one=torch.zeros_like(one.material.u);drive_one=torch.zeros((3,12),device='cuda')
    for step in range(6*96):
        write_step(one,values[step],maps,force_one,drive_one)
    arrays={};errors={}
    for name in ('u','v','p','z'):
        a=reference[name+'_single'];b=getattr(one.material,name).cpu().numpy();arrays[name+'_reference']=a;arrays[name+'_serial']=b;errors[name]=float(np.max(np.abs(a.astype(float)-b)))
    for name in ('u','v'):
        a=reference['bridge_'+name+'_single'];b=getattr(one.wave,name).cpu().numpy();arrays['bridge_'+name+'_reference']=a;arrays['bridge_'+name+'_serial']=b;errors['bridge_'+name]=float(np.max(np.abs(a.astype(float)-b)))
    a=reference['pitch_single'];b=one.material.tuning()[2].cpu().numpy();arrays['pitch_reference']=a;arrays['pitch_serial']=b;pitch_error=float(np.max(np.abs(a.astype(float)-b)))
    finite=one.diagnostics()['finite'];passed=finite and max(errors.values())<=2e-6 and pitch_error<=1e-4
    np.savez_compressed(output/'admission.npz',**arrays)
    report={'seconds':6,'rate':96,'method':'single-chain execution against the preserved single-chain reference','reference_path':str(reference_path),'reference_sha256':sha256(reference_path),'history':label(ORDERS[0]),'field_max_errors':errors,'pitch_max_error_hz':pitch_error,'all_finite':finite,'passed':passed}
    (output/'admission.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'admission':report}),flush=True)
    if not passed:raise ValueError('The serial-chain reference admission failed')


def pairwise(response):
    value=response.astype(np.float64)
    return np.sqrt(np.mean((value[:,None]-value[None,:])**2,axis=(-2,-1)))


def summarize(distance,labels):
    rows,columns=np.triu_indices(len(labels),1);values=distance[rows,columns];index=int(np.argmin(values))
    out={'minimum_hz':float(values.min()),'median_hz':float(np.median(values)),'maximum_hz':float(values.max()),'closest_pair':[labels[rows[index]],labels[columns[index]]],'pairs':len(values)}
    for length in (1,2):
        mask=np.array([labels[a][-length:]==labels[b][-length:] for a,b in zip(rows,columns)]);selected=values[mask]
        out[f'same_last_{length}']={'pairs':len(selected),'minimum_hz':float(selected.min()),'median_hz':float(np.median(selected)),'maximum_hz':float(selected.max())}
    return out


def main(args):
    torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.set_float32_matmul_precision('highest')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False);hashes={}
    for relative in SOURCES:
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    labels=[label(o) for o in ORDERS];protocol={'created_utc':datetime.now(timezone.utc).isoformat(),'plan':'research/RECEIVED-HISTORIES-PROTOCOL.md','execution_revision':'research/RECEIVED-HISTORIES-REVISION-001.md','source_sha256':hashes,'rates':[96,192],'size':64,'write_seconds':30,'probe_seconds':12,'probe_hz':24,'orders':labels,'tokens':TOKENS,'onsets':ONSETS,'conditions':CONDITIONS,'batch_size':1}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n');began=time.monotonic();admission(out);rate_data={};rate_reports={}
    for rate in (96,192):
        root=out/f'rate-{rate:03d}';root.mkdir();cfg=MaterialConfig(size=64,dt=1/rate,feedback=.08)
        all_pitches=np.empty((24,4,2,289,12),dtype=np.float32);fresh=None;controls=[]
        for start in range(24):
            batch=root/f'batch-{start:02d}';batch.mkdir();orders=ORDERS[start:start+1];choir=make_choir(cfg,1);maps=footprints();levels=contacts(orders,rate,30)
            force=torch.zeros_like(choir.material.u);drive=torch.zeros((3,12),device='cuda')
            for step in range(30*rate):
                write_step(choir,levels[step],maps,force,drive)
                if step%(rate*10)==0 and not choir.diagnostics()['finite']:raise FloatingPointError('Non-finite writing')
            state=choir.state_dict();assert choir.diagnostics()['finite']
            np.savez_compressed(batch/'written-state.npz',**{key:value.numpy() for key,value in state['material'].items()},bridge_u=state['bridge_u'].numpy(),bridge_v=state['bridge_v'].numpy(),gates=state['gates'].numpy(),steps=state['steps'],index=state['index'])
            p=choir.material.p.reshape(1,3,64,64)[:,1:];z=choir.material.z.reshape(1,3,64,64)[:,1:]
            probe=BatchedMaterial(cfg,9)
            for condition in range(4):
                probe.p[:-1].reshape(1,4,2,64,64)[:,condition]=p
                probe.z[:-1].reshape(1,4,2,64,64)[:,condition]=z
            probe.p[:-1].reshape(1,4,2,64,64)[:,1].zero_();probe.z[:-1].reshape(1,4,2,64,64)[:,2].zero_()
            probe.p[:-1].reshape(1,4,2,64,64)[:,3].zero_();probe.z[:-1].reshape(1,4,2,64,64)[:,3].zero_();probe.reset_transients()
            np.savez_compressed(batch/'probe-initial.npz',**{name:getattr(probe,name).cpu().numpy() for name in ('u','v','p','z','delay','echo_phase')},steps=probe.steps,index=probe.index,orders=np.array([label(o) for o in orders]))
            question=(Gesture(1,0,.025,.5,.4,1.6),Gesture(4,4,.025,.5,.4,1.6),Gesture(7,8,.025,.5,.4,1.6));excitation=torch.zeros((9,12),device='cuda');readouts=[]
            for step in range(12*rate+1):
                if step%(rate//24)==0:readouts.append(probe.tuning()[2].cpu().numpy())
                if step==12*rate:break
                excitation.zero_()
                for event in question:excitation[:,event.voice]=event.at(step/rate)
                probe.step(excitation)
            assert probe.finite();raw=np.asarray(readouts);assert np.isfinite(raw).all()
            current=raw[:,:8].reshape(289,1,4,2,12).transpose(1,2,3,0,4);all_pitches[start:start+1]=current
            if fresh is None:fresh=raw[:,-1].copy()
            else:assert np.array_equal(fresh,raw[:,-1])
            erasure_error=float(np.max(np.abs(current[:,3].astype(float)-fresh[None,None])))
            controls.append({'batch':start,'both_erased_max_error_hz':erasure_error,'all_finite':True})
            (batch/'report.json').write_text(json.dumps({'rate':rate,'orders':[label(o) for o in orders],'config':asdict(cfg),**controls[-1]},indent=2)+'\n')
            print(json.dumps({'rate':rate,'batch':start,'erasure_max_hz':erasure_error,'elapsed_seconds':time.monotonic()-began}),flush=True)
            del choir,probe,levels,p,z
        distances=np.array([[pairwise(all_pitches[:,condition,receiver]) for receiver in range(2)] for condition in range(4)])
        np.savez_compressed(root/'readouts.npz',time=np.arange(289)/24,pitch_hz=all_pitches,fresh_pitch_hz=fresh,orders=np.array(labels),conditions=np.array(CONDITIONS))
        np.savez_compressed(root/'distances.npz',rms_hz=distances,orders=np.array(labels),conditions=np.array(CONDITIONS))
        report={'rate':rate,'observations':{condition:{str(receiver+1):summarize(distances[c,receiver],labels) for receiver in range(2)} for c,condition in enumerate(CONDITIONS)},'controls':controls,'erasure_controls_pass':all(r['both_erased_max_error_hz']<=1e-6 for r in controls)}
        (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');rate_data[rate]=all_pitches;rate_reports[str(rate)]=report
    cross=[]
    for receiver in range(2):
        fine=rate_data[192][:,0,receiver].astype(np.float64);coarse=rate_data[96][:,0,receiver].astype(np.float64)
        distances=np.sqrt(np.mean((fine[:,None]-coarse[None,:])**2,axis=(-2,-1)));nearest=distances.argmin(axis=1);ties=(distances==distances.min(axis=1)[:,None]).sum(axis=1)
        np.savez_compressed(out/f'cross-rate-receiver-{receiver+1}.npz',rms_hz=distances,orders=np.array(labels))
        cross.append({'receiver':receiver+1,'own_nearest':int((nearest==np.arange(24)).sum()),'all_unique':bool((ties==1).all()),'predicted_orders':[labels[i] for i in nearest],
            'own_distances_hz':np.diag(distances).tolist(),'nearest_distances_hz':distances[np.arange(24),nearest].tolist(),'nearest_margin_hz':(np.sort(distances,axis=1)[:,1]-np.sort(distances,axis=1)[:,0]).tolist()})
    summary={'finished_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-began,'orders':labels,'rates':rate_reports,'cross_rate':cross,
        'distant_receiver_gate_passed':all(rate_reports[str(rate)]['observations']['connected']['2']['minimum_hz']>.001 and rate_reports[str(rate)]['erasure_controls_pass'] for rate in (96,192)) and cross[1]['own_nearest']==24 and cross[1]['all_unique'],
        'scope':'The complete selected four-token order universe in an invented finite material. All outcomes and erasures retained. Timestep consistency is not continuum convergence, human audibility, physical capacity or infinite-time rank.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');members=[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()]
    (out/'manifest.json').write_text(json.dumps({'source_sha256':hashes,'files':members},indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artifacts/studies/received-histories-002');main(p.parse_args())
