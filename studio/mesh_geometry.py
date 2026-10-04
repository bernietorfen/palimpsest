"""An explicit, closed mesh of PALIMPSEST's authored folded sheet.

The same state and chart equations used by the study ray marcher are evaluated
here. Wear clips triangles in the chart; front, back, and every boundary wall
form a closed surface. No external mesh or procedural asset is imported.
"""
from __future__ import annotations

from dataclasses import dataclass
import functools
import time

import numpy as np

from studio.reconstruction import periodic_field


@dataclass
class SheetMesh:
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    triangles: np.ndarray
    first_wall_triangle: int
    stats: dict


@functools.lru_cache(maxsize=8)
def chart_grid(nu: int, nv: int):
    v,u=np.meshgrid(np.linspace(-np.pi,3*np.pi,nv),np.linspace(-1,1,nu),indexing="ij")
    parameters=np.column_stack((u.ravel(),v.ravel()))
    corners=np.arange(nu*nv,dtype=np.int64).reshape(nv,nu)[:-1,:-1].ravel()
    a=np.column_stack((corners,corners+1,corners+nu))
    b=np.column_stack((corners+1,corners+nu+1,corners+nu))
    return parameters,np.concatenate((a,b))


def field_samples(field: np.ndarray, uv: np.ndarray) -> np.ndarray:
    h,w=field.shape[:2]
    p=np.mod(uv,1)*np.array([w,h])
    cell=np.floor(p).astype(np.int64)
    fraction=(p-cell).astype(np.float32)
    x0,y0=cell[:,0]%w,cell[:,1]%h
    x1,y1=(x0+1)%w,(y0+1)%h
    a=field[y0,x0]*(1-fraction[:,0,None])+field[y0,x1]*fraction[:,0,None]
    b=field[y1,x0]*(1-fraction[:,0,None])+field[y1,x1]*fraction[:,0,None]
    return a*(1-fraction[:,1,None])+b*fraction[:,1,None]


def chart_coordinates(parameters: np.ndarray):
    s,phi=parameters.T
    x=s*(1.34+.055*np.sin(2*phi))
    theta=x*(2*np.pi/2.8)
    uv=np.column_stack((x/2.8+.5,phi/(4*np.pi)+.5))
    return x,theta,phi,uv


def positions_at(parameters: np.ndarray, field: np.ndarray, side: float):
    x,theta,phi,uv=chart_coordinates(parameters)
    f=field_samples(field,uv)
    radius=.55+.072*phi+.048*np.sin(3*phi+theta)+.038*np.cos(4*theta+phi)
    radius+=.085*np.tanh(f[:,0]*1.6)+.13*np.tanh(f[:,1]*2.1)+side*.013
    y=.22*np.sin(1.8*x)+radius*np.sin(phi)
    z=.13*np.sin(2.2*x+.4)+radius*np.cos(phi)
    return np.column_stack((x,y,z)).astype(np.float32),uv.astype(np.float32)


def unit(a: np.ndarray):
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)


def grid_normals(positions: np.ndarray, nu: int, nv: int):
    grid=positions.reshape(nv,nu,3)
    dv,du=np.gradient(grid,axis=(0,1),edge_order=2)
    return unit(np.cross(du,dv)).reshape(-1,3)


def clipped_chart(parameters: np.ndarray, faces: np.ndarray, values: np.ndarray):
    inside=values[faces]<=0
    counts=inside.sum(axis=1)
    complete=faces[counts==3]
    one=faces[counts==1]
    two=faces[counts==2]
    def rotated(triangles, flags):
        if not len(triangles):
            return np.empty((0,3),np.int64)
        start=np.argmax(flags,axis=1)
        return np.take_along_axis(triangles,(start[:,None]+np.arange(3)[None,:])%3,axis=1)
    one=rotated(one,inside[counts==1])
    two=rotated(two,~inside[counts==2])
    starts=np.concatenate((one,two))
    if len(starts)==0:
        return parameters,complete,np.empty((0,2),np.int64),np.empty(0)
    edges=np.concatenate((starts[:,[0,1]],starts[:,[0,2]]))
    edges.sort(axis=1)
    n=len(parameters)
    keys=edges[:,0]*n+edges[:,1]
    unique_keys=np.unique(keys)
    unique_edges=np.column_stack((unique_keys//n,unique_keys%n))
    va,vb=values[unique_edges[:,0]],values[unique_edges[:,1]]
    fraction=va/(va-vb)
    new_parameters=parameters[unique_edges[:,0]]*(1-fraction[:,None])+parameters[unique_edges[:,1]]*fraction[:,None]
    new_ids=np.arange(len(unique_edges),dtype=np.int64)+n
    def intersection(a,b):
        return new_ids[np.searchsorted(unique_keys,np.minimum(a,b)*n+np.maximum(a,b))]
    additions=[]
    if len(one):
        a,b,c=one.T
        additions.append(np.column_stack((a,intersection(a,b),intersection(a,c))))
    if len(two):
        a,b,c=two.T
        ab,ac=intersection(a,b),intersection(a,c)
        additions.extend((np.column_stack((ab,b,c)),np.column_stack((ab,c,ac))))
    result=np.concatenate((complete,*additions))
    return np.concatenate((parameters,new_parameters)),result,unique_edges,fraction


def boundary_edges(faces: np.ndarray, vertices: int):
    directed=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    low=np.min(directed,axis=1);high=np.max(directed,axis=1)
    keys=low.astype(np.int64)*vertices+high
    _,first,counts=np.unique(keys,return_index=True,return_counts=True)
    if np.any(counts>2):
        raise ValueError("the clipped chart has a nonmanifold edge")
    return directed[first[counts==1]]


def build_sheet(field: np.ndarray, nu: int=192, nv: int=384) -> SheetMesh:
    began=time.monotonic()
    if nu<8 or nv<8:
        raise ValueError("mesh chart resolution must be at least 8 by 8")
    field=periodic_field(field,max(512,*field.shape[:2]))
    parameters,faces=chart_grid(nu,nv)
    x,theta,phi,uv=chart_coordinates(parameters)
    f=field_samples(field,uv)
    window=f[:,2]-.56-.30*np.sin(2*theta+4*phi)-.16*np.cos(5*theta-phi)
    clipped,front,edges,fraction=clipped_chart(parameters,faces,window)
    if len(front)==0:
        raise ValueError("this state has no visible sheet at the selected chart resolution")
    outer,texture_uv=positions_at(clipped,field,1.)
    inner,_=positions_at(clipped,field,-1.)
    original_count=len(parameters)
    outer_normals=grid_normals(outer[:original_count],nu,nv)
    inner_normals=-grid_normals(inner[:original_count],nu,nv)
    if len(edges):
        outer_normals=np.concatenate((outer_normals,unit(outer_normals[edges[:,0]]*(1-fraction[:,None])+outer_normals[edges[:,1]]*fraction[:,None])))
        inner_normals=np.concatenate((inner_normals,unit(inner_normals[edges[:,0]]*(1-fraction[:,None])+inner_normals[edges[:,1]]*fraction[:,None])))
    used,inverse=np.unique(front.ravel(),return_inverse=True)
    front=inverse.reshape(-1,3)
    outer,inner=outer[used],inner[used]
    outer_normals,inner_normals=outer_normals[used],inner_normals[used]
    texture_uv=texture_uv[used]
    count=len(used)
    boundary=boundary_edges(front,count)
    a,b=boundary.T
    back=front[:,::-1]+count
    walls=np.concatenate((np.column_stack((b,a,a+count)),np.column_stack((b,a+count,b+count))))
    triangles=np.concatenate((front,back,walls)).astype(np.uint32)
    positions=np.concatenate((outer,inner)).astype(np.float32)
    normals=np.concatenate((outer_normals,inner_normals)).astype(np.float32)
    uvs=np.concatenate((texture_uv,texture_uv)).astype(np.float32)
    stats={"nu":nu,"nv":nv,"vertices":len(positions),"triangles":len(triangles),
           "boundary_segments":len(boundary),"visible_chart_fraction":float((window<=0).mean()),
           "seconds_to_build":time.monotonic()-began}
    return SheetMesh(positions,normals,uvs,triangles,2*len(front),stats)


def topology_report(mesh: SheetMesh) -> dict:
    faces=mesh.triangles.astype(np.int64)
    edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    edges.sort(axis=1)
    keys=edges[:,0]*len(mesh.positions)+edges[:,1]
    _,counts=np.unique(keys,return_counts=True)
    tri=mesh.positions[faces].astype(np.float64)
    cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    areas=np.linalg.norm(cross,axis=1)*.5
    volume=np.sum(np.einsum("ij,ij->i",tri[:,0],np.cross(tri[:,1],tri[:,2])))/6
    return {"watertight_edges":bool(np.all(counts==2)),"boundary_edges":int(np.sum(counts==1)),
            "nonmanifold_edges":int(np.sum(counts>2)),"degenerate_faces":int(np.sum(areas<1e-12)),
            "signed_volume":float(volume),"surface_area":float(areas.sum()),
            "finite":bool(np.isfinite(mesh.positions).all() and np.isfinite(mesh.normals).all()),
            "max_radius":float(np.linalg.norm(mesh.positions,axis=1).max())}
