"""GPU integration checks for repeat draws and genuine high-precision output."""
import numpy as np

from studio.mesh_render import SheetRenderer


def test_repeated_area_lit_draws_do_not_reuse_an_accumulation_attachment():
    renderer=SheetRenderer(160,100,shadow_size=256,nu=32,nv=64)
    field=np.zeros((32,32,4),np.float32)
    try:
        first=renderer.draw(field,samples=4,area_shadow=True,bit_depth=16)
        second=renderer.draw(field,samples=4,area_shadow=True,bit_depth=16)
        np.testing.assert_array_equal(first,second)
        assert first.dtype==np.uint16
        assert first.shape==(100,160,3)
        assert np.std(first.astype(np.float64))>1000
        # An 8-bit image multiplied by 257 cannot pass this check.
        assert np.count_nonzero(first%257)>first.size*.5
        assert len(np.unique(first))>1000
    finally:
        renderer.close()
