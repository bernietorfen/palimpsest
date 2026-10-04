"""Regression for the observed smooth-field shading bands. RunPod only."""
import numpy as np

from studio.reconstruction import periodic_field


def test_periodic_reconstruction_matches_analytic_field_between_samples():
    def signal(n):
        y, x = np.meshgrid(np.arange(n)*2*np.pi/n, np.arange(n)*2*np.pi/n, indexing="ij")
        return np.stack((np.sin(3*x+y), np.cos(2*x-2*y),
                         .2+.1*np.sin(x+5*y), np.cos(7*x-3*y)), axis=-1)
    result = periodic_field(signal(32), 256)
    np.testing.assert_allclose(result, signal(256), atol=6e-7, rtol=2e-6)
    np.testing.assert_allclose(result[::8, ::8], signal(32), atol=4e-7, rtol=2e-6)


def test_even_grid_nyquist_components_keep_original_samples_and_mean():
    y, x = np.meshgrid(np.arange(32), np.arange(32), indexing="ij")
    a = np.stack(((-1.)**x, (-1.)**y, (-1.)**(x+y), np.ones_like(x)*.25), axis=-1)
    result = periodic_field(a, 256)
    np.testing.assert_allclose(result[::8, ::8], a, atol=3e-7)
    np.testing.assert_allclose(result.mean(axis=(0,1)), a.mean(axis=(0,1)), atol=2e-7)
