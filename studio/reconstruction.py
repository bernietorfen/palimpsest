"""Periodic reconstruction for rendering, independent of material dynamics."""
from __future__ import annotations

import numpy as np
from scipy.signal import resample


def periodic_field(field: np.ndarray, size: int = 512) -> np.ndarray:
    """Fourier interpolate a periodic sampled field without cubic slope ripples.

    Original samples lie at integer lattice coordinates, including coordinate
    zero. This also preserves even-grid Nyquist modes correctly through SciPy's
    resampler. Rendering may interpolate the reconstructed texels linearly.
    """
    if field.ndim != 3 or field.shape[2] != 4:
        raise ValueError("expected a height x width x 4 material field")
    if size < max(field.shape[:2]):
        raise ValueError("render reconstruction may not downsample the source")
    data = np.asarray(field, dtype=np.float32)
    for axis in (0, 1):
        if data.shape[axis] != size:
            data = resample(data, size, axis=axis)
    return np.ascontiguousarray(data, dtype=np.float32)
