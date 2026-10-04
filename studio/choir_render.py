"""A multi-body studio renderer for the original material choir. Run on RunPod."""
from dataclasses import dataclass
import math
from pathlib import Path
import time

import moderngl
import numpy as np

from studio.mesh_geometry import SheetMesh
from studio.mesh_render import SheetRenderer, orthographic, perspective, rotation, set_matrix, view_matrix
from studio.reconstruction import periodic_field


@dataclass
class SceneObject:
    mesh: SheetMesh
    field: np.ndarray
    model: np.ndarray
    kind: int = 0
    palette: int = 0


def transform(position, *, turn=0., tilt=0., lean=0., scale=1.):
    result = rotation(0, 2, turn) @ rotation(1, 2, tilt) @ rotation(0, 1, lean)
    result[:3, :3] *= scale
    result[:3, 3] = position
    return result


def world_point(point, model):
    return (model @ np.r_[point, 1.])[:3]


def floor_object(height=-2.2):
    points = np.array([[-60, height, -60], [-60, height, 60], [60, height, -60], [60, height, 60]], dtype=np.float32)
    normals = np.tile([0., 1., 0.], (4, 1)).astype(np.float32)
    uv = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float32)
    triangles = np.array([[0, 1, 2], [2, 1, 3]], dtype=np.uint32)
    mesh = SheetMesh(points, normals, uv, triangles, 2, {'kind': 'display-floor', 'triangles': 2})
    return SceneObject(mesh, np.zeros((2, 2, 4), dtype=np.float32), np.eye(4), kind=2)


class ChoirRenderer(SheetRenderer):
    def __init__(self, width, height, *, shadow_size=2048):
        super().__init__(width, height, shadow_size=shadow_size)
        root = Path(__file__).parent / 'shaders'
        self.program.release()
        self.program = self.ctx.program(vertex_shader=(root / 'sheet.vert').read_text(),
                                        fragment_shader=(root / 'choir.frag').read_text())
        self.quad.release()
        self.composite.release()
        self.composite = self.ctx.program(vertex_shader=(root / 'fullscreen.vert').read_text(),
                                          fragment_shader=(root / 'choir_composite.frag').read_text())
        self.quad = self.ctx.simple_vertex_array(self.composite, self.quad_buffer, 'position')
        self.program['material_field'].value = 0
        self.program['shadow_key'].value = 1
        self.program['shadow_fill'].value = 2
        self.composite['image'].value = 3
        self.scene = []

    def upload_scene(self, objects):
        for item in self.scene:
            for resource in item['resources']:
                resource.release()
        self.scene = []
        for obj in objects:
            mesh = obj.mesh
            if not len(mesh.triangles):
                continue
            packed = np.column_stack((mesh.positions, mesh.normals, mesh.uv)).astype('f4')
            vertices, indices = self.ctx.buffer(packed.tobytes()), self.ctx.buffer(mesh.triangles.tobytes())
            vao = self.ctx.vertex_array(self.program, [(vertices, '3f 3f 2f', 'position', 'normal', 'chart')], indices)
            depth = self.ctx.vertex_array(self.depth_program, [(vertices, '3f 20x', 'position')], indices)
            field = periodic_field(obj.field, max(256, *obj.field.shape[:2])) if obj.kind == 0 else obj.field
            texture = self.ctx.texture((field.shape[1], field.shape[0]), 4, field.astype('f4').tobytes(), dtype='f4')
            texture.repeat_x = texture.repeat_y = obj.kind == 0
            self.scene.append({'object': obj, 'vao': vao, 'depth': depth, 'texture': texture,
                               'resources': [vao, depth, texture, vertices, indices]})

    def draw_scene(self, objects, *, camera=(11., 8., 13.), target=(0., .2, 0.), samples=32,
                   exposure=1.05, focal_length=1.8, lens_radius=0., focus_distance=None,
                   camera_roll=0., light_angle=.1, shadow_extent=8.5, shadow_softness=1.,
                   backdrop=1, area_shadow=True, bit_depth=8):
        if samples < 1 or bit_depth not in (8, 16):
            raise ValueError('Invalid image sampling or depth')
        began = time.monotonic()
        self.upload_scene(objects)
        lights = [np.array([-8., 12., 9.]), np.array([7., 7., -7.])]
        turn = rotation(0, 2, light_angle)[:3, :3]
        lights = [turn @ point for point in lights]

        def shadows(positions):
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND | moderngl.CULL_FACE)
            for label, frame, point in zip(('key', 'fill'), self.shadow_frames, positions):
                projection = orthographic(shadow_extent, .1, 60) @ view_matrix(point, (0, 0, 0))
                frame.use()
                self.ctx.viewport = (0, 0, self.shadow_size, self.shadow_size)
                frame.clear(depth=1.)
                set_matrix(self.depth_program, 'light_projection', projection)
                for item in self.scene:
                    if item['object'].kind == 2:
                        continue
                    set_matrix(self.depth_program, 'model', item['object'].model)
                    item['depth'].render()
                self.program[label + '_position'].value = tuple(point)
                set_matrix(self.program, label + '_projection', projection)

        if not area_shadow:
            shadows(lights)
        for name, value in {'diagnostic': 0, 'shadow_softness': shadow_softness,
                            'area_shadow': int(area_shadow), 'background_mode': backdrop}.items():
            self.program[name].value = value
        self.composite['exposure'].value = exposure
        self.composite['sample_weight'].value = 1 / samples
        self.composite['backdrop'].value = backdrop
        self.composite['final_pass'].value = 0
        self.shadows[0].use(1)
        self.shadows[1].use(2)
        self.surface.use(3)
        self.accum_frame.use()
        self.accum_frame.clear(0, 0, 0, 0)
        eye, look = np.asarray(camera, dtype=float), np.asarray(target, dtype=float)
        view = view_matrix(eye, look, camera_roll)
        if focus_distance is None:
            focus_distance = np.linalg.norm(eye - look)
        for sample in range(samples):
            if area_shadow:
                positions = []
                for light_index, point in enumerate(lights):
                    light_view = view_matrix(point, (0, 0, 0))
                    radius = math.sqrt(((sample + .5) * .7548776662466927 + light_index * .31) % 1)
                    angle = (sample + .5) * 2.399963229728653 + light_index * 1.7
                    offset = (math.cos(angle) * light_view[0, :3] + math.sin(angle) * light_view[1, :3]) * radius
                    positions.append(point + offset * (2.1 if light_index == 0 else 1.7) * shadow_softness)
                shadows(positions)
            sx, sy = ((sample + .5) * .7548776662466927) % 1 - .5, ((sample + .5) * .5698402909980532) % 1 - .5
            radius = math.sqrt((sample + .5) / samples) * lens_radius
            angle = 2 * math.pi * ((sample + .5) * .618033988749895 % 1)
            dx, dy = radius * math.cos(angle), radius * math.sin(angle)
            moved = eye + dx * view[0, :3] + dy * view[1, :3]
            moved_view = view.copy()
            moved_view[:3, 3] = -moved_view[:3, :3] @ moved
            projection = perspective(focal_length, self.width / self.height, far=100)
            projection[0, 2] = -projection[0, 0] * dx / focus_distance + 2 * sx / self.width
            projection[1, 2] = -projection[1, 1] * dy / focus_distance + 2 * sy / self.height
            set_matrix(self.program, 'view_projection', projection @ moved_view)
            self.program['camera'].value = tuple(moved)
            self.surface_frame.use()
            self.ctx.viewport = (0, 0, self.width, self.height)
            self.surface_frame.clear(0, 0, 0, 0, depth=1.)
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)
            for item in self.scene:
                obj = item['object']
                set_matrix(self.program, 'model', obj.model)
                self.program['first_wall_triangle'].value = obj.mesh.first_wall_triangle
                self.program['surface_kind'].value = obj.kind
                self.program['palette'].value = obj.palette
                item['texture'].use(0)
                item['vao'].render()
            self.accum_frame.use()
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.ONE, moderngl.ONE)
            self.quad.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)
        self.surface_frame.use()
        self.accum.use(3)
        self.composite['final_pass'].value = 1
        self.quad.render(moderngl.TRIANGLE_STRIP)
        raw = self.surface_frame.read(components=3, dtype='f1' if bit_depth == 8 else 'f4', alignment=1)
        image = np.frombuffer(raw, np.uint8 if bit_depth == 8 else np.float32).reshape(self.height, self.width, 3)
        if bit_depth == 16:
            image = np.clip(image * 65535 + .5, 0, 65535).astype('<u2')
        self.last_stats = {'objects': len(objects), 'triangles': sum(len(o.mesh.triangles) for o in objects),
                           'seconds_to_draw': time.monotonic() - began, 'device': self.device,
                           'samples': samples, 'width': self.width, 'height': self.height,
                           'area_shadow': area_shadow, 'frame_bits': bit_depth, 'backdrop': backdrop}
        return np.ascontiguousarray(image[::-1])
