"""Preserve an actual material state as textured glTF and closed STL geometry."""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image
import trimesh

from studio.mesh_geometry import build_sheet, topology_report, unit
from studio.mesh_render import model_matrix
from studio.preserve import sha256
from studio.reconstruction import periodic_field
from studio.simulate import source_hashes


def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def pigment(field,size=1024):
    f=periodic_field(field,size)
    ink=smoothstep(.035,.66,np.abs(f[:,:,1]))
    line=(.5+.5*np.sin(f[:,:,1]*47+f[:,:,0]*16))**18
    line*=smoothstep(.035,.14,np.abs(f[:,:,1]))
    base=np.array([.68,.65,.55])*(1-ink[:,:,None]*.91)
    base+=np.array([.025,.045,.053])*ink[:,:,None]*.91
    base=base*(1-line[:,:,None]*.82)+np.array([.43,.20,.066])*line[:,:,None]*.82
    srgb=np.where(base<=.0031308,12.92*base,1.055*np.power(base,1/2.4)-.055)
    # A half-texel offset aligns a repeat texture with the sampled material grid.
    return Image.fromarray(np.clip(srgb*255+.5,0,255).astype(np.uint8))


def hard_boundary_mesh(sheet):
    first=sheet.first_wall_triangle
    walls=sheet.triangles[first:]
    wall_positions=sheet.positions[walls].reshape(-1,3)
    triangles=sheet.positions[walls]
    normals=unit(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]))
    normals=np.repeat(normals,3,axis=0)
    wall_ids=np.arange(len(wall_positions)).reshape(-1,3)+len(sheet.positions)
    return (np.concatenate((sheet.positions,wall_positions)),
            np.concatenate((sheet.normals,normals)),
            np.concatenate((sheet.uv,sheet.uv[walls].reshape(-1,2))),
            np.concatenate((sheet.triangles[:first],wall_ids)))


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load(args.fields,mmap_mode="r")
    performance=json.loads((Path(args.fields).parent/"manifest.json").read_text())
    frame=round(args.time*performance["fps"])
    if frame<0 or frame>=len(fields):
        raise ValueError("selected state is outside the recorded performance")
    field=fields[frame].astype(np.float32)
    sheet=build_sheet(field,nu=args.mesh_u,nv=args.mesh_v)
    topology=topology_report(sheet)
    if not topology["watertight_edges"] or topology["degenerate_faces"] or not topology["finite"]:
        raise ValueError(f"the source geometry fails export checks: {topology}")
    transform=model_matrix(.55)[:3,:3]
    base=trimesh.Trimesh(vertices=sheet.positions@transform.T,faces=sheet.triangles,process=False)
    bounds=base.bounds
    center=bounds.mean(axis=0)
    scale=.2/np.max(bounds[1]-bounds[0])
    # Export normals are split at the cut walls; topology is checked before this
    # deliberate duplication of coincident vertices for a sharp material edge.
    positions,normals,uv,triangles=hard_boundary_mesh(sheet)
    positions=(positions@transform.T-center)*scale
    normals=normals@transform.T
    texture=pigment(field)
    texture.save(out/"pigment.png")
    # Trimesh uses the conventional bottom-left UV origin and handles glTF's V
    # conversion. Our field rows start at v=0, so flip the authored chart here.
    uv=uv.copy()
    uv[:,0]+=.5/texture.width
    uv[:,1]=1-(uv[:,1]+.5/texture.height)
    material=trimesh.visual.material.PBRMaterial(name="PALIMPSEST / ivory and inscription",
        baseColorTexture=texture,baseColorFactor=[255,255,255,255],
        metallicFactor=.025,roughnessFactor=.68,doubleSided=False,alphaMode="OPAQUE")
    visual=trimesh.visual.texture.TextureVisuals(uv=uv,material=material)
    display=trimesh.Trimesh(vertices=positions,faces=triangles,vertex_normals=normals,
                          visual=visual,process=False)
    display.metadata={"title":"PALIMPSEST","performance_time_seconds":frame/performance["fps"],
                      "author":"Codex","units":"meters","maximum_extent_m":.2,
                      "scope":"Authored material-state sculpture; the fatigue cutouts are a visual mapping."}
    glb=out/"palimpsest.glb"
    glb.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(display),include_normals=True))
    physical=base.copy()
    physical.vertices=(physical.vertices-center)*scale*1000
    physical.export(out/"palimpsest-mm.stl")
    loaded=trimesh.load_scene(glb,process=False)
    imported=next(iter(loaded.geometry.values()))
    glb_error=float(np.max(np.abs(imported.bounds-display.bounds)))
    if len(imported.faces)!=len(display.faces) or glb_error>1e-6:
        raise ValueError("glTF roundtrip changed the triangle count or bounds")
    loaded_stl=trimesh.load_mesh(out/"palimpsest-mm.stl",process=True)
    if not loaded_stl.is_watertight or not loaded_stl.is_winding_consistent:
        raise ValueError("STL roundtrip is not consistently closed")
    components=trimesh.graph.connected_components(base.face_adjacency,nodes=np.arange(len(base.faces)),min_len=1)
    report={"source_sha256":hashes,"performance_manifest_sha256":sha256(Path(args.fields).parent/"manifest.json"),
            "performance_time_seconds":frame/performance["fps"],"mesh":sheet.stats,"topology":topology,
            "disconnected_components":len(components),"component_triangle_counts":sorted([len(c) for c in components],reverse=True),
            "glb":{"bytes":glb.stat().st_size,"sha256":sha256(glb),"units":"meters",
                   "roundtrip_triangles":len(imported.faces),"roundtrip_bounds_max_error_m":glb_error},
            "stl":{"bytes":(out/"palimpsest-mm.stl").stat().st_size,"sha256":sha256(out/"palimpsest-mm.stl"),
                   "coordinate_units":"millimeters","watertight_after_roundtrip":bool(loaded_stl.is_watertight),
                   "consistent_winding_after_roundtrip":bool(loaded_stl.is_winding_consistent)},
            "maximum_extent_mm":200,"scope":"Closed geometry is checked. No physical fabrication, self-intersection proof, structural assessment, or universal printability claim. Later states deliberately contain separate suspended fragments."}
    (out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--fields",default="artifacts/studies/performance-002/fields.npy")
    parser.add_argument("--time",type=float,required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--mesh-u",type=int,default=192)
    parser.add_argument("--mesh-v",type=int,default=384)
    main(parser.parse_args())
