"""Export original choir states as a single textured mesh and closed STL.

The exported installation has separate suspended components. Closure is checked;
self-intersection, structural support and physical fabrication are not certified.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
import trimesh
from studio.choir_film import scene_at
from studio.choir_geometry import ListenerShape,build_listener
from studio.choir_render import SceneObject,transform
from studio.export_sculpture import hard_boundary_mesh,smoothstep
from studio.mesh_geometry import topology_report,unit
from studio.preserve import sha256
from studio.reconstruction import periodic_field


def pigment(field,kind,resolution):
    if kind==0:
        f=periodic_field(field,max(resolution,*field.shape[:2]));p=f[:,:,1];ink=smoothstep(.015,.34,np.abs(p))
        mix=smoothstep(-.025,.025,p)[:,:,None]
        color=np.array([.36,.047,.015])*(1-mix)+np.array([.014,.071,.115])*mix
        base=np.array([.76,.72,.63])*(1-ink[:,:,None]*.95)+color*ink[:,:,None]*.95
        line=(.5+.5*np.sin(p*61+f[:,:,0]*8))**18*smoothstep(.012,.10,np.abs(p))
        base=base*(1-line[:,:,None]*.75)+np.array([.52,.26,.07])*line[:,:,None]*.75
    else:
        t=np.linspace(0,len(field)-1,resolution);f=np.stack([np.interp(t,np.arange(len(field)),field[:,0,k]) for k in range(4)],axis=1)
        f=np.repeat(f[:,None],resolution,axis=1);energy=np.clip(np.sqrt(np.maximum(f[:,:,2],0))*.85,0,1)[:,:,None]
        base=np.array([.025,.076,.085])*(1-energy)+np.array([.62,.28,.046])*energy
        line=(.5+.5*np.sin(f[:,:,0]*23))**10*.24
        base=base*(1-line[:,:,None])+np.array([.55,.36,.16])*line[:,:,None]
    srgb=np.where(base<=.0031308,12.92*base,1.055*np.maximum(base,0)**(1/2.4)-.055)
    image=Image.fromarray(np.clip(srgb*255+.5,0,255).astype(np.uint8))
    if image.size!=(resolution,resolution):image=image.resize((resolution,resolution),Image.Resampling.LANCZOS)
    return np.asarray(image)


def main(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    sources=('studio/choir_sculpture.py','studio/choir_geometry.py','studio/choir_scene.py','studio/choir_cinematography.py','studio/export_sculpture.py','studio/mesh_geometry.py','studio/reconstruction.py')
    hashes={}
    for relative in sources:
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    performance=Path(args.performance);protocol=json.loads((performance/'protocol.json').read_text());scene=protocol['scene'];fields=np.load(performance/'fields.npy',mmap_mode='r')
    with np.load(performance/'readouts.npz') as data:readout={k:data[k] for k in ('bridge_u','bridge_v','endpoints','gates')}
    if args.state=='source':
        t=228.;field=periodic_field(fields[round(t*24),1],256);shape=ListenerShape(**scene['shapes'][scene['bodies'][1]['shape']])
        objects=[SceneObject(build_listener(field,args.nu,args.nv,shape),field,transform((0,0,0),turn=.18,tilt=.08))];labels=['B'];extent=.2
    else:
        t=216. if args.state=='encounter' else 288.
        objects=scene_at(scene,fields,readout,t,protocol['field_fps'],protocol['readout_hz'],args.nu,args.nv)
        objects=[o for o in objects if o.kind!=2];labels=[b['name'] for b in scene['bodies']]+[f'bridge-{i+1}' for i,g in enumerate(readout['gates'][round(t*96)]) if g>=.005]
        if args.state=='after':objects.pop(1);labels.pop(1)
        extent=.6
    count=len(objects);cols=min(8,count);rows=(count+cols-1)//cols;res=args.texture;tile=res+4
    atlas=np.zeros((rows*tile,cols*tile,3),dtype=np.uint8);parts=[];physical=[];reports=[];offset=0
    for i,(obj,label) in enumerate(zip(objects,labels)):
        topology=topology_report(obj.mesh)
        assert topology['finite'] and topology['watertight_edges'] and not topology['degenerate_faces'],(label,topology)
        base=trimesh.Trimesh(vertices=obj.mesh.positions,faces=obj.mesh.triangles,process=False)
        assert base.is_winding_consistent and base.volume>0,(label,base.volume)
        base.apply_transform(obj.model);physical.append(base)
        pos,norm,uv,faces=hard_boundary_mesh(obj.mesh);pos=(np.c_[pos,np.ones(len(pos))]@obj.model.T)[:,:3];norm=unit(norm@obj.model[:3,:3].T)
        color=pigment(obj.field,obj.kind,res);padded=np.pad(color,((2,2),(2,2),(0,0)),mode='wrap' if obj.kind==0 else 'edge')
        row,col=divmod(i,cols);atlas[row*tile:(row+1)*tile,col*tile:(col+1)*tile]=padded
        uv=uv.copy();factor=res if obj.kind==0 else res-1
        uv[:,0]=(col*tile+2.5+uv[:,0]*factor)/(cols*tile)
        uv[:,1]=1-(row*tile+2.5+uv[:,1]*factor)/(rows*tile)
        parts.append((pos,norm,uv,faces+offset));offset+=len(pos)
        reports.append({'name':label,'kind':'body' if obj.kind==0 else 'bridge','triangles':len(base.faces),'topology':topology,'signed_volume':float(base.volume)})
    positions=np.concatenate([p[0] for p in parts]);normals=np.concatenate([p[1] for p in parts]);uv=np.concatenate([p[2] for p in parts]);faces=np.concatenate([p[3] for p in parts]);bounds=np.array([positions.min(axis=0),positions.max(axis=0)]);center=bounds.mean(axis=0);scale=extent/np.max(bounds[1]-bounds[0]);positions=(positions-center)*scale
    texture=Image.fromarray(atlas);texture.save(out/'pigment.png')
    material=trimesh.visual.material.PBRMaterial(name='PALIMPSEST / A choir of absences',baseColorTexture=texture,baseColorFactor=[255]*4,metallicFactor=.025,roughnessFactor=.62,doubleSided=False,alphaMode='OPAQUE')
    visual=trimesh.visual.texture.TextureVisuals(uv=uv,material=material)
    display=trimesh.Trimesh(vertices=positions,faces=faces,vertex_normals=normals,visual=visual,process=False)
    display.metadata={'title':'A choir of absences','state':args.state,'time_seconds':t,'author':'Codex','units':'meters','maximum_extent_m':extent,
                      'source_absent':args.state=='after','source_absence':'B is omitted from the visible final installation; the retained source state remains in the scientific record.' if args.state=='after' else 'B is present.',
                      'scope':'Original artistic embedding of recorded fields. Separate suspended components; no fabrication validation.'}
    glb=out/'choir.glb';glb.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(display),include_normals=True))
    stl=trimesh.util.concatenate(physical);stl.vertices=(stl.vertices-center)*scale*1000;stl.export(out/'choir-mm.stl')
    restored=trimesh.load_scene(glb,process=False);restored_mesh=next(iter(restored.geometry.values()));bounds_error=float(np.max(np.abs(restored_mesh.bounds-display.bounds)))
    assert len(restored_mesh.faces)==len(display.faces) and bounds_error<1e-6
    restored_stl=trimesh.load_mesh(out/'choir-mm.stl',process=True);assert restored_stl.is_watertight and restored_stl.is_winding_consistent
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'performance_manifest_sha256':sha256(performance/'manifest.json'),
            'state':args.state,'time_seconds':t,'mesh':[args.nu,args.nv],'texture_resolution_per_component':res,'objects':reports,'visible_objects':count,
            'triangles':len(display.faces),'glb_bounds_roundtrip_error_m':bounds_error,'stl_watertight':bool(restored_stl.is_watertight),'stl_winding_consistent':bool(restored_stl.is_winding_consistent),
            'maximum_extent_mm':extent*1000,'source_absent':args.state=='after',
            'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha256(p)} for p in (glb,out/'choir-mm.stl',out/'pigment.png')},
            'scope':'Closed component geometry and roundtrips verified. The complete installation has separate suspended pieces. No self-intersection proof, physical support, structural strength or universal printability claim.'}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('objects','source_sha256')},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--state',choices=('encounter','after','source'),required=True);p.add_argument('--output',required=True);p.add_argument('--nu',type=int,default=128);p.add_argument('--nv',type=int,default=192);p.add_argument('--texture',type=int,default=256);main(p.parse_args())
