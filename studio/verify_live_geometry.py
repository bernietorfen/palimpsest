"""Reopen browser-authored STL files and compare chart coordinates independently."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from studio.mesh_geometry import positions_at,chart_coordinates,field_samples

parser=argparse.ArgumentParser()
parser.add_argument('--input',default='artifacts/analysis/live-geometry-001')
args=parser.parse_args()
root=Path(args.input)
construction=json.loads((root/'construction.json').read_text())
reports=[]
for item in construction['cases']:
    name=item['name']
    field=np.fromfile(root/f'{name}.f32',dtype='<f4').reshape(64,64,4)
    parameters=np.asarray(item['parameters'])
    positions,_=positions_at(parameters,field,1)
    _,theta,phi,uv=chart_coordinates(parameters)
    windows=field_samples(field,uv)[:,2]-.56-.30*np.sin(2*theta+4*phi)-.16*np.cos(5*theta-phi)
    point_error=float(np.max(np.abs(positions-np.asarray(item['positions']))))
    window_error=float(np.max(np.abs(windows-np.asarray(item['windows']))))
    assert point_error<1e-6 and window_error<1e-6,(name,point_error,window_error)
    path=root/f'{name}.stl'
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent,name
    assert np.isfinite(mesh.vertices).all() and (mesh.area_faces>1e-12).all(),name
    assert abs(float(mesh.extents.max())-200)<1e-3,name
    reports.append({'name':name,'time':item['time'],'triangles':len(mesh.faces),
        'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
        'components':len(mesh.split(only_watertight=False)),'minimum_face_area_mm2':float(mesh.area_faces.min()),
        'maximum_extent_mm':float(mesh.extents.max()),'bytes':path.stat().st_size,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'build_ms':item['build_ms'],
        'studio_coordinate_max_error':point_error,'studio_window_max_error':window_error})
report={'created_utc':datetime.now(timezone.utc).isoformat(),'cases':reports,
    'scope':'Four actual JavaScript live-material states, independently reopened with trimesh. Coordinates checked against the original studio chart using the same raw 64-grid fields. No self-intersection or physical-printability claim.'}
(root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
