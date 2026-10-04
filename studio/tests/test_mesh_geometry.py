"""The authored surface must also exist as coherent closed geometry."""
import numpy as np

from studio.mesh_geometry import build_sheet, topology_report


def test_unwritten_sheet_has_closed_front_back_and_boundary_walls():
    field=np.zeros((32,32,4),np.float32)
    mesh=build_sheet(field,nu=48,nv=96)
    report=topology_report(mesh)
    assert report["watertight_edges"]
    assert report["degenerate_faces"]==0
    assert report["signed_volume"]>.1
    assert report["finite"]
    assert report["max_radius"]<2.4


def test_wear_windows_are_closed_by_new_walls_and_remove_material():
    field=np.zeros((32,32,4),np.float32)
    initial=build_sheet(field,nu=48,nv=96)
    field[:,:,2]=.72
    worn=build_sheet(field,nu=48,nv=96)
    report=topology_report(worn)
    assert report["watertight_edges"]
    assert report["degenerate_faces"]==0
    assert 0<report["signed_volume"]<topology_report(initial)["signed_volume"]
    assert worn.stats["boundary_segments"]>initial.stats["boundary_segments"]
    assert 0<worn.stats["visible_chart_fraction"]<1
