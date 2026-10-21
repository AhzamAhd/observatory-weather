"""
Unit tests for the per-band moonless sky (snr_calculator.moon_sky_brightness).

  * V band is identical to the V-only model it replaced (reference values
    computed with the previous snr_calculator.py).
  * The dark sky in each band differs from V by the Patat (2008) colour.
  * A full Moon brightens the sky in every band.

Run:  python -m pytest tests/test_sky_brightness.py
  or: python tests/test_sky_brightness.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airmass_calculator import extinction_coefficient  # noqa: E402
from snr_calculator import (DARK_SKY_COLOUR, PHOTOMETRIC_FILTERS,  # noqa: E402
                            get_sky_brightness)

# (moon %, moon alt, target alt, separation, k_V) -> V sky from the old model.
V_REFERENCE = [
    ((5, -10, 60, 90, 0.116), 21.67),
    ((100, 60, 60, 90, 0.116), 19.05),
    ((50, 30, 45, 40, 0.12), 20.36),
    ((100, 70, 30, 15, 0.15), 16.85),
    ((80, 20, 80, 120, 0.10), 20.41),
    ((20, 5, 20, 60, 0.2), 20.86),
    ((0, -5, 10, 90, 0.13), 20.71),
    ((100, 45, 89, 3, 0.116), 17.25),
]
BANDS = ["U", "B", "V", "R", "I"]
PARANAL_M = 2635


def test_v_band_unchanged():
    for (ph, malt, talt, sep, k), expected in V_REFERENCE:
        assert get_sky_brightness(ph, malt, talt, sep, k_extinction=k) == expected
        assert get_sky_brightness(ph, malt, talt, sep, k_extinction=k,
                                  band="V", k_band=k) == expected


def test_dark_sky_colour_at_zenith():
    # Moon down, target at the zenith (X = 1): the extinction factor is 1, so
    # each band differs from V by exactly the tabulated colour.
    v = get_sky_brightness(0, -10, 90, 90, k_extinction=0.12)
    for band in BANDS:
        sky = get_sky_brightness(0, -10, 90, 90, k_extinction=0.12, band=band,
                                 k_band=extinction_coefficient(PARANAL_M, band))
        assert abs((sky - v) - DARK_SKY_COLOUR[band]) <= 0.011, band
    i_sky = get_sky_brightness(0, -10, 90, 90, k_extinction=0.12, band="I",
                               k_band=0.05)
    assert i_sky < v - 2.0          # I is ~2 mag/arcsec^2 brighter than V


def test_full_moon_brighter_in_every_band():
    k_v = extinction_coefficient(PARANAL_M, "V")
    for band in BANDS:
        kb = extinction_coefficient(PARANAL_M, band)
        dark = get_sky_brightness(5, -10, 60, 90, k_extinction=k_v,
                                  band=band, k_band=kb)
        full = get_sky_brightness(100, 60, 60, 90, k_extinction=k_v,
                                  band=band, k_band=kb)
        assert full < dark, band


def test_narrowband_uses_its_broad_band():
    assert PHOTOMETRIC_FILTERS["Hα (narrowband)"]["band"] == "R"
    assert PHOTOMETRIC_FILTERS["OIII (narrowband)"]["band"] == "V"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
