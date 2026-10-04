"""Headless GPU rendering of authored material sculptures. RunPod only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import moderngl
import numpy as np
from PIL import Image
from studio.reconstruction import periodic_field


class SculptureRenderer:
    def __init__(self, width: int, height: int) -> None:
        self.ctx = moderngl.create_standalone_context(backend="egl", require=430)
        renderer = self.ctx.info["GL_RENDERER"]
        if "llvmpipe" in renderer.lower() or "softpipe" in renderer.lower():
            raise RuntimeError(f"Software rendering is not an acceptable GPU fallback: {renderer}")
        print(json.dumps({"renderer": renderer, "opengl": self.ctx.version_code}), flush=True)
        self.width, self.height = width, height
        root = Path(__file__).parent / "shaders"
        self.program = self.ctx.program(vertex_shader=(root / "fullscreen.vert").read_text(),
                                        fragment_shader=(root / "sculpture.frag").read_text())
        points = np.array([[-1,-1],[1,-1],[-1,1],[1,1]], dtype="f4")
        self.buffer = self.ctx.buffer(points.tobytes())
        self.vao = self.ctx.simple_vertex_array(self.program, self.buffer, "position")
        self.output = self.ctx.texture((width, height), 4, dtype="f4")
        self.framebuffer = self.ctx.framebuffer(color_attachments=[self.output])
        self.field = None
        self.program["resolution"].value = (width, height)
        self.program["material_field"].value = 0

    def draw(self, field: np.ndarray, *, turn: float = .4, design: int = 0,
             aperture: float = -.12, memory_gain: float = 1.,
             camera=(4.8,2.8,4.8), target=(0.,0.,0.), samples: int = 4,
             diagnostic: int = 0, style: int = 0, light_angle: float = 0.,
             exposure: float = 1.1, focal_length: float = 2.05,
             focus_distance: float | None = None, lens_radius: float = 0.,
             camera_roll: float = 0., shadow_mode: int = 1,
             march_scale: float = 1., normal_step: float = .00015) -> np.ndarray:
        h, w, channels = field.shape
        assert channels == 4
        data = periodic_field(field, max(512, h, w))
        h,w = data.shape[:2]
        if self.field is None or self.field.size != (w,h):
            if self.field is not None:
                self.field.release()
            self.field = self.ctx.texture((w,h), 4, dtype="f4")
            self.field.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.field.repeat_x = self.field.repeat_y = True
        self.field.write(data.tobytes())
        self.field.use(0)
        if focus_distance is None:
            focus_distance = float(np.linalg.norm(np.asarray(camera)-np.asarray(target)))
        for name, value in {"turn":turn,"design":design,"aperture":aperture,
                            "memory_gain":memory_gain,"camera":camera,"target":target,
                            "diagnostic":diagnostic,"sample_weight":1/samples,
                            "style":style,"light_angle":light_angle,"exposure":exposure,
                            "focal_length":focal_length,"focus_distance":focus_distance,
                            "lens_radius":lens_radius,"camera_roll":camera_roll,
                            "shadow_mode":shadow_mode,"march_scale":march_scale,
                            "normal_step":normal_step}.items():
            self.program[name].value = value
        self.framebuffer.use()
        self.ctx.viewport = (0,0,self.width,self.height)
        self.framebuffer.clear(0.,0.,0.,0.)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        for sample in range(samples):
            self.program["sample_index"].value=sample
            # A deterministic, shifted low-discrepancy camera sample sequence.
            sx=((sample+.5)*.7548776662466927)%1.-.5
            sy=((sample+.5)*.5698402909980532)%1.-.5
            self.program["jitter"].value=(sx,sy)
            radius=math.sqrt((sample+.5)/samples)
            angle=2*math.pi*((sample+.5)*.618033988749895%1.)
            self.program["lens_sample"].value=(radius*math.cos(angle),radius*math.sin(angle))
            self.vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)
        raw=self.framebuffer.read(components=3,dtype="f1",alignment=1)
        result=np.frombuffer(raw,dtype=np.uint8).reshape(self.height,self.width,3)
        return np.ascontiguousarray(np.flipud(result))

    def close(self) -> None:
        self.ctx.release()


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--field", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--width",type=int,default=1600)
    parser.add_argument("--height",type=int,default=1000)
    parser.add_argument("--samples",type=int,default=4)
    parser.add_argument("--design",type=int,default=0)
    parser.add_argument("--turn",type=float,default=.4)
    parser.add_argument("--aperture",type=float,default=-.12)
    parser.add_argument("--diagnostic",type=int,default=0)
    args=parser.parse_args()
    field=np.load(args.field)
    renderer=SculptureRenderer(args.width,args.height)
    start=time.monotonic()
    im=renderer.draw(field,turn=args.turn,design=args.design,aperture=args.aperture,
                     samples=args.samples,diagnostic=args.diagnostic)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(im).save(args.output)
    print(json.dumps({"output":args.output,"seconds":time.monotonic()-start}),flush=True)
    renderer.close()
