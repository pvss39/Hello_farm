"""
One-time Google Earth Engine authentication.

Run this ONCE:
    python gee_auth.py

It will open a browser window. Log in with the Google account that has
Earth Engine access. After login, a token is saved automatically and
the app uses real satellite imagery from that point on.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

GEE_PROJECT = os.getenv("GEE_PROJECT", "my-spread-sheet-473920")

print("=" * 55)
print("  Hello Farm — Google Earth Engine Setup")
print("=" * 55)
print(f"\n  Project: {GEE_PROJECT}")
print("\n  A browser window will open. Please:")
print("  1. Log in with your Google account")
print("  2. Click 'Allow' to grant Earth Engine access")
print("  3. Come back here — it completes automatically\n")

try:
    import ee

    # Authenticate — opens browser
    ee.Authenticate(auth_mode='localhost')

    # Initialize with project
    ee.Initialize(project=GEE_PROJECT)

    # Quick test — fetch a known NDVI value over Emani Duggirala, AP
    test_point = ee.Geometry.Point([80.7200, 16.3700])
    test_image = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(test_point)
        .filterDate("2025-01-01", "2026-01-01")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
    )

    ndvi = test_image.normalizedDifference(["B8", "B4"])
    value = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=test_point.buffer(100),
        scale=10,
        maxPixels=1e8,
    ).get("NDVI").getInfo()

    print("=" * 55)
    print("  Authentication SUCCESSFUL!")
    print(f"  Test NDVI over Thurpu Polam: {value:.4f}")
    print("  Real satellite imagery is now active.")
    print("=" * 55)

except Exception as e:
    print(f"\n[ERROR] Authentication failed: {e}")
    print("\nTroubleshooting:")
    print("  - Make sure earthengine-api is installed: pip install earthengine-api")
    print(f"  - Make sure project '{GEE_PROJECT}' is registered at code.earthengine.google.com")
    print("  - Check that your Google account has Earth Engine access")
    sys.exit(1)
