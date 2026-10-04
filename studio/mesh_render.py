"""GPU rasterization of the authored closed sheet; all execution on RunPod."""
from __future__ import annotations

import math
from pathlib import Path
import time

import moderngl
import numpy as np

from studio.mesh_geometry import SheetMesh, build_sheet
from studio.reconstruction import periodic_field


def unit(v):
    v=np.asarray(v,dtype=np.float64)
    return v/np.linalg.norm(v)


def rotation(a,b,angle):
    m=np.eye(4,dtype=np.float64)
    c,s=math.cos(angle),math.sin(angle)
    m[a,a]=m[b,b]=c
    m[a,b]=s
    m[b,a]=-s
    return m


def model_matrix(turn):
    return rotation(0,2,-turn)@rotation(0,1,.31)@rotation(1,2,-.18)


def view_matrix(camera,target,roll=0.):
    eye=np.asarray(camera,dtype=np.float64)
    forward=unit(np.asarray(target)-eye)
    right=unit(np.cross(forward,[0.,1.,0.]))
    up=np.cross(right,forward)
    c,s=math.cos(roll),math.sin(roll)
    right,up=c*right-s*up,s*right+c*up
    m=np.eye(4)
    m[:3,:3]=np.vstack((right,up,-forward))
    m[:3,3]=-m[:3,:3]@eye
    return m


def perspective(focal,aspect,near=.05,far=30.):
    m=np.zeros((4,4))
    m[0,0]=2*focal/aspect
    m[1,1]=2*focal
    m[2,2]=-(far+near)/(far-near)
    m[2,3]=-2*far*near/(far-near)
    m[3,2]=-1
    return m


def orthographic(size,near=.1,far=16.):
    m=np.eye(4)
    m[0,0]=m[1,1]=1/size
    m[2,2]=-2/(far-near)
    m[2,3]=-(far+near)/(far-near)
    return m


def set_matrix(program,name,value):
    program[name].write(np.asarray(value,dtype="f4").T.tobytes())


class SheetRenderer:
    def __init__(self,width,height,shadow_size=2048,nu=192,nv=384):
        self.width,self.height,self.nu,self.nv=width,height,nu,nv
        self.ctx=moderngl.create_standalone_context(backend="egl",require=430)
        self.device=self.ctx.info["GL_RENDERER"]
        if "llvmpipe" in self.device.lower() or "softpipe" in self.device.lower():
            raise RuntimeError("GPU rendering is required")
        root=Path(__file__).parent/"shaders"
        self.program=self.ctx.program(vertex_shader=(root/"sheet.vert").read_text(),
                                      fragment_shader=(root/"sheet.frag").read_text())
        self.depth_program=self.ctx.program(vertex_shader=(root/"sheet_depth.vert").read_text(),
                                            fragment_shader=(root/"sheet_depth.frag").read_text())
        self.composite=self.ctx.program(vertex_shader=(root/"fullscreen.vert").read_text(),
                                        fragment_shader=(root/"sheet_composite.frag").read_text())
        points=np.array([[-1,-1],[1,-1],[-1,1],[1,1]],dtype="f4")
        self.quad_buffer=self.ctx.buffer(points.tobytes())
        self.quad=self.ctx.simple_vertex_array(self.composite,self.quad_buffer,"position")
        self.surface=self.ctx.texture((width,height),4,dtype="f2")
        self.depth=self.ctx.depth_renderbuffer((width,height))
        self.surface_frame=self.ctx.framebuffer([self.surface],self.depth)
        self.accum=self.ctx.texture((width,height),4,dtype="f4")
        self.accum_frame=self.ctx.framebuffer([self.accum])
        self.shadow_size=shadow_size
        self.shadows=[]
        self.shadow_frames=[]
        for _ in range(2):
            texture=self.ctx.depth_texture((shadow_size,shadow_size))
            texture.compare_func=""
            texture.repeat_x=texture.repeat_y=False
            texture.filter=(moderngl.NEAREST,moderngl.NEAREST)
            self.shadows.append(texture)
            self.shadow_frames.append(self.ctx.framebuffer(depth_attachment=texture))
        self.field=None
        self.resources=[]
        self.last_stats={}
        self.program["material_field"].value=0
        self.program["shadow_key"].value=1
        self.program["shadow_fill"].value=2
        self.composite["image"].value=3

    def upload(self,mesh: SheetMesh,field):
        for resource in self.resources:
            resource.release()
        data=np.column_stack((mesh.positions,mesh.normals,mesh.uv)).astype("f4")
        vertices=self.ctx.buffer(data.tobytes())
        indices=self.ctx.buffer(mesh.triangles.tobytes())
        self.vao=self.ctx.vertex_array(self.program,[(vertices,"3f 3f 2f","position","normal","chart")],indices)
        self.depth_vao=self.ctx.vertex_array(self.depth_program,[(vertices,"3f 20x","position")],indices)
        self.resources=[self.vao,self.depth_vao,vertices,indices]
        self.program["first_wall_triangle"].value=mesh.first_wall_triangle
        field=periodic_field(field,max(512,*field.shape[:2]))
        h,w=field.shape[:2]
        if self.field is None or self.field.size!=(w,h):
            if self.field is not None:
                self.field.release()
            self.field=self.ctx.texture((w,h),4,dtype="f4")
            self.field.repeat_x=self.field.repeat_y=True
        self.field.write(field.astype("f4").tobytes())

    def draw(self,field,*,turn=.3,camera=(5.4,3.2,5.6),target=(0.,0.,0.),
             samples=8,light_angle=.25,exposure=1.1,focal_length=2.05,
             focus_distance=None,lens_radius=0.,camera_roll=0.,
             diagnostic=0,palette=0,backdrop=0,shadow_softness=1.,mesh=None,
             area_shadow=False,bit_depth=8):
        if samples<1:
            raise ValueError("at least one camera sample is required")
        if bit_depth not in (8,16):
            raise ValueError("frame storage must be 8 or 16 bits per channel")
        began=time.monotonic()
        mesh=mesh or build_sheet(field,self.nu,self.nv)
        self.upload(mesh,field)
        model=model_matrix(turn)
        set_matrix(self.program,"model",model)
        set_matrix(self.depth_program,"model",model)
        lights=[np.array([-3.5,5.,4.5]),np.array([4.,1.6,-2.8])]
        light_rotation=rotation(0,2,light_angle)[:3,:3]
        lights=[light_rotation@p for p in lights]
        light_projections=[orthographic(2.65)@view_matrix(p,(0,0,0)) for p in lights]
        def shadows(positions,projections):
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)
            self.ctx.disable(moderngl.CULL_FACE)
            for frame,projection in zip(self.shadow_frames,projections):
                frame.use()
                self.ctx.viewport=(0,0,self.shadow_size,self.shadow_size)
                frame.clear(depth=1.)
                set_matrix(self.depth_program,"light_projection",projection)
                self.depth_vao.render()
            for label,p,m in zip(("key","fill"),positions,projections):
                self.program[label+"_position"].value=tuple(p)
                set_matrix(self.program,label+"_projection",m)
        if not area_shadow:
            shadows(lights,light_projections)
        for name,value in {"diagnostic":diagnostic,"palette":palette,"shadow_softness":shadow_softness,
                           "area_shadow":int(area_shadow)}.items():
            self.program[name].value=value
        self.composite["exposure"].value=exposure
        self.composite["sample_weight"].value=1/samples
        self.composite["backdrop"].value=backdrop
        self.composite["final_pass"].value=0
        self.field.use(0)
        self.shadows[0].use(1)
        self.shadows[1].use(2)
        self.surface.use(3)
        self.accum_frame.use()
        self.accum_frame.clear(0.,0.,0.,0.)
        self.ctx.viewport=(0,0,self.width,self.height)
        eye=np.asarray(camera,dtype=np.float64)
        look=np.asarray(target,dtype=np.float64)
        view=view_matrix(eye,look,camera_roll)
        if focus_distance is None:
            focus_distance=np.linalg.norm(eye-look)
        for sample in range(samples):
            if area_shadow:
                positions=[]
                for light_index,p in enumerate(lights):
                    light_view=view_matrix(p,(0.,0.,0.))
                    r=math.sqrt(((sample+.5)*.7548776662466927+light_index*.31)%1.)
                    a=(sample+.5)*2.399963229728653+light_index*1.7
                    offset=(math.cos(a)*light_view[0,:3]+math.sin(a)*light_view[1,:3])*r
                    positions.append(p+offset*(.85 if light_index==0 else .65)*shadow_softness)
                projections=[orthographic(2.65)@view_matrix(p,(0,0,0)) for p in positions]
                shadows(positions,projections)
            sx=((sample+.5)*.7548776662466927)%1.-.5
            sy=((sample+.5)*.5698402909980532)%1.-.5
            radius=math.sqrt((sample+.5)/samples)*lens_radius
            angle=2*math.pi*((sample+.5)*.618033988749895%1.)
            dx,dy=radius*math.cos(angle),radius*math.sin(angle)
            moved=eye+dx*view[0,:3]+dy*view[1,:3]
            moved_view=view.copy()
            moved_view[:3,3]=-moved_view[:3,:3]@moved
            projection=perspective(focal_length,self.width/self.height)
            projection[0,2]=-projection[0,0]*dx/focus_distance+2*sx/self.width
            projection[1,2]=-projection[1,1]*dy/focus_distance+2*sy/self.height
            set_matrix(self.program,"view_projection",projection@moved_view)
            self.program["camera"].value=tuple(moved)
            self.surface_frame.use()
            self.ctx.viewport=(0,0,self.width,self.height)
            self.surface_frame.clear(0.,0.,0.,0.,depth=1.)
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)
            self.vao.render()
            self.accum_frame.use()
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func=(moderngl.ONE,moderngl.ONE)
            self.quad.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)
        self.surface_frame.use()
        self.accum.use(3)
        self.composite["final_pass"].value=1
        self.quad.render(moderngl.TRIANGLE_STRIP)
        raw=self.surface_frame.read(components=3,dtype="f1" if bit_depth==8 else "f4",alignment=1)
        result=np.frombuffer(raw,np.uint8 if bit_depth==8 else np.float32).reshape(self.height,self.width,3)
        if bit_depth==16:
            result=np.clip(result*65535+.5,0,65535).astype("<u2")
        self.last_stats={**mesh.stats,"seconds_to_draw":time.monotonic()-began,
                         "device":self.device,"samples":samples,"width":self.width,"height":self.height,
                         "area_shadow":area_shadow,"frame_bits":bit_depth}
        return np.ascontiguousarray(result[::-1])

    def close(self):
        self.ctx.release()
