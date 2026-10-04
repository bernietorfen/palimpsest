"""Cycles look-development and film renderer for the original phase sculpture.

Run with Blender on the production GPU host. All shapes, lights and materials
are authored here; there are no imported meshes, images or environment maps.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import math
from pathlib import Path
import sys
import time
import shutil

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.river_geometry import (CENTRES, membrane, joining_fibres, phases,
                                   validate_embedding, place_membrane, woven_relations,
                                   woven_internal_relations)


PALETTE = [(0.67, .60, .44, 1), (.36, .12, .035, 1),
           (.035, .11, .13, 1), (.055, .075, .105, 1)]


def material(name, color, *, metal=.05, rough=.38, transmission=.24, emission=0.):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['IOR'].default_value = 1.38
    bsdf.inputs['Transmission Weight'].default_value = transmission
    bsdf.inputs['Coat Weight'].default_value = .18
    bsdf.inputs['Coat Roughness'].default_value = .27
    bsdf.inputs['Sheen Weight'].default_value = .5 if metal < .5 else 0
    bsdf.inputs['Subsurface Weight'].default_value = .13 if metal < .5 else 0
    bsdf.inputs['Subsurface Radius'].default_value = (.11, .055, .025)
    bsdf.inputs['Emission Color'].default_value = color
    bsdf.inputs['Emission Strength'].default_value = emission
    if 'Thin Film Thickness' in bsdf.inputs:
        bsdf.inputs['Thin Film Thickness'].default_value = 340 if metal < .5 else 0
        bsdf.inputs['Thin Film IOR'].default_value = 1.32
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 210.
    noise.inputs['Detail'].default_value = 2.
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .07
    bump.inputs['Distance'].default_value = .005
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def make_mesh(name, grid, uv, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(grid.reshape(-1, 3).tolist(), [], faces.tolist())
    mesh.update()
    mesh.polygons.foreach_set('use_smooth', np.ones(len(mesh.polygons), dtype=bool))
    layer = mesh.uv_layers.new(name='Ribbon')
    vertices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', vertices)
    layer.data.foreach_set('uv', uv.reshape(-1, 2)[vertices].astype(np.float32).ravel())
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    solid = obj.modifiers.new('A fine physical edge', 'SOLIDIFY')
    solid.thickness = .008
    solid.offset = 0
    return obj


def make_curves(name, paths, mat, radius=.006, cyclic=False):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    curve.resolution_u = 1
    for path in paths:
        spline = curve.splines.new('POLY')
        spline.use_cyclic_u = cyclic
        spline.points.add(len(path)-1)
        homogeneous = np.column_stack((path, np.ones(len(path)))).astype(np.float32)
        spline.points.foreach_set('co', homogeneous.ravel())
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def area(name, location, target, color, energy, size, size_y=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.color, data.shape, data.size = energy, color, 'DISK', size
    if size_y:
        data.shape, data.size_y = 'RECTANGLE', size_y
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def build_scene(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    enabled = []
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
        if device.use:
            enabled.append(device.name)
    if not enabled:
        raise RuntimeError('An OptiX GPU is required for this production render')
    print(json.dumps({'gpu': enabled}), flush=True)
    scene.cycles.device = 'GPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .025
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPTIX'
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.render.dither_intensity = 0.
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.65
    world = bpy.data.worlds.new('Unlit room')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.055, .070, .095, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .13
    scene.world = world
    mats = [material(f'Membrane {g}', col) for g, col in enumerate(PALETTE)]
    edges = [material(f'Edge {g}', tuple(min(1.,c*1.35+.05) for c in col[:3])+(1,),
                      metal=.78, rough=.25, transmission=0.) for g, col in enumerate(PALETTE)]
    thread = material('Continuity / copper', (1., .40, .10, 1.), metal=.8,
                      rough=.23, transmission=0., emission=.045)
    reference_thread = thread.copy()
    reference_thread.name = 'Reference continuity / copper'
    state = phases(args.time)
    dynamic = []
    groups = [args.group] if args.group is not None else list(range(4))
    for g in groups:
        for r in range(8):
            grid, uv, faces = membrane(state, g, r, along=args.along,
                                       across=args.across, shape=args.shape)
            if args.choreography and args.shape != 'weave':
                grid = place_membrane(grid, state, g)
            obj = make_mesh(f'Membrane {g}.{r}', grid, uv, faces, mats[g])
            edge = make_curves(f'Edge {g}.{r}', [grid[:,0], grid[:,-1]], edges[g], .004,
                               cyclic=args.shape == 'weave')
            dynamic.append((g, r, obj, edge))
    fibers = []
    if args.group is None:
        for first, second in ((0,1), (1,2), (2,3), (3,0), (0,2)):
            paths = (woven_relations(state, first, second) if args.shape == 'weave' else
                     joining_fibres(state, first, second, placed=args.choreography))
            obj = make_curves(f'Relation {first}.{second}', paths, thread, .004)
            fibers.append(('between', first, second, obj))
    if args.shape == 'weave' and args.group in (None,0):
        for first in range(7):
            obj = make_curves(f'Reference stitch {first}',
                              woven_internal_relations(state,first,first+1),reference_thread,.005)
            fibers.append(('within',first,first+1,obj))
    ground = material('Charcoal ground', (.006,.008,.011,1), metal=.12,
                       rough=.48, transmission=0)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.16))
    bpy.context.object.name = 'Continuous dark ground'
    bpy.context.object.data.materials.append(ground)
    area('Amber softbox', (-5,-1,7), (0,0,2), (1.,.77,.49), 1100, 5.)
    area('Blue rim', (4,4,6), (0,0,2.5), (.43,.74,1.), 1600, 4., 2.)
    area('Narrow white reflection', (-1,5,3.5), (0,0,2), (1.,.93,.83), 650, 1., 6.)
    area('Soft camera fill', (2,-8,4), (0,0,2), (.63,.72,1.), 80, 6.)
    camera_data = bpy.data.cameras.new('Camera')
    camera = bpy.data.objects.new('Camera', camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.lens = 58
    camera.data.clip_start = .03
    camera.data.clip_end = 300
    camera.data.dof.use_dof = True
    camera.data.dof.aperture_fstop = 5.6
    scene.camera = camera
    set_camera(camera, args.shot, args.shape)
    scene.render.film_transparent = False
    return scene, camera, dynamic, fibers


def set_camera(camera, shot, shape='river'):
    if shot == 'wide':
        location, target, lens, fstop = (12,-20,10), (0,0,2.2), 58, 5.6
    elif shot == 'portrait':
        location, target, lens, fstop = (2.6,-10.6,5.9), tuple(CENTRES[0]), 72, 4.
    elif shot == 'macro':
        location, target, lens, fstop = (-.6,-4.3,3.7), (-2.,-1.1,3.), 75, 3.2
    elif shot == 'overhead':
        location, target, lens, fstop = (0,-.01,20), (0,0,2.), 58, 8.
    else:
        raise ValueError(shot)
    if shape == 'weave':
        if shot == 'wide':
            location, target, lens = (8,-17,8), (0,0,3.55), 54
        elif shot == 'portrait':
            location, target, lens = (1,-10,5), (-1,0,4), 68
        elif shot == 'macro':
            location, target, lens = (-4,-3.1,5.8), (-3,.05,5.5), 72
        elif shot == 'overhead':
            location, target, lens = (1,-3,15), (0,0,3.55), 48
    camera.location = location
    aim(camera, target)
    camera.data.lens = lens
    camera.data.dof.aperture_fstop = fstop
    camera.data.dof.focus_distance = (Vector(target)-camera.location).length


def main(args):
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    captured = output.parent/'source'
    captured.mkdir(exist_ok=True)
    source_hashes = {}
    for name in ('river_blender.py','river_geometry.py'):
        source = Path(__file__).with_name(name)
        data = source.read_bytes()
        target = captured/name
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Use a new proof directory for changed source')
        target.write_bytes(data)
        source_hashes[name] = hashlib.sha256(data).hexdigest()
    start = time.monotonic()
    print(json.dumps({'embedding_check': validate_embedding()}), flush=True)
    scene, camera, dynamic, fibers = build_scene(args)
    scene.render.filepath = str(output.resolve())
    bpy.ops.render.render(write_still=True)
    receipt = {'renderer': bpy.app.version_string, 'arguments': vars(args),
               'wall_seconds': time.monotonic()-start, 'source_sha256': source_hashes,
               'gpu': [d.name for d in bpy.context.preferences.addons['cycles'].preferences.devices if d.use],
               'scope': 'Original authored geometry and physical rendering of phase relationships; not a quantum matter image.'}
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--time', type=float, default=.65)
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--along', type=int, default=193)
    parser.add_argument('--across', type=int, default=49)
    parser.add_argument('--group', type=int, choices=range(4))
    parser.add_argument('--choreography', action='store_true')
    parser.add_argument('--shape', choices=['river','bloom','weave'], default='weave')
    parser.add_argument('--shot', choices=['wide','portrait','macro','overhead'], default='wide')
    main(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
