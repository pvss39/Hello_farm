"""
Google Earth Engine (GEE) NDVI Provider.

Fetches real satellite imagery and computes NDVI for any lat/lon using GEE.

Supported collections:
- COPERNICUS/S2_SR_HARMONIZED  (Sentinel-2A/2B, 10m, surface reflectance)
- LANDSAT/LC08/C02/T1_L2        (Landsat-8, 30m)
- LANDSAT/LC09/C02/T1_L2        (Landsat-9, 30m)

Authentication:
- First run: calls ee.Authenticate() → opens browser → you log in once
- After that: token stored at ~/.config/earthengine/credentials (auto-used)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

GEE_PROJECT  = os.getenv("GEE_PROJECT", "my-spread-sheet-473920")
GEE_KEY_FILE = os.getenv("GEE_KEY_FILE", "gee-key.json")

# GEE collection configs: (collection_id, NIR_band, Red_band, scale_m, cloud_field)
GEE_COLLECTIONS = {
    "Sentinel-2A": (
        "COPERNICUS/S2_SR_HARMONIZED", "B8", "B4", 10, "CLOUDY_PIXEL_PERCENTAGE"
    ),
    "Sentinel-2B": (
        "COPERNICUS/S2_SR_HARMONIZED", "B8", "B4", 10, "CLOUDY_PIXEL_PERCENTAGE"
    ),
    "Landsat-8": (
        "LANDSAT/LC08/C02/T1_L2", "SR_B5", "SR_B4", 30, "CLOUD_COVER"
    ),
    "Landsat-9": (
        "LANDSAT/LC09/C02/T1_L2", "SR_B5", "SR_B4", 30, "CLOUD_COVER"
    ),
}


class GEEProvider:
    """
    Fetches real NDVI data from Google Earth Engine.

    One-time setup: run  gee_auth.py  or call GEEProvider.authenticate() once.
    After auth, all calls work automatically.
    """

    _initialized = False

    def __init__(self):
        self.project   = GEE_PROJECT
        self.key_file  = GEE_KEY_FILE
        self._ee       = None
        self._available = False
        self._init_ee()

    def _init_ee(self):
        """Initialize Earth Engine. Silent fail if not available."""
        try:
            import ee
            self._ee = ee
            # Try to initialize using stored credentials
            try:
                ee.Initialize(project=self.project)
                self._available = True
                GEEProvider._initialized = True
            except Exception:
                # Not yet authenticated — needs browser auth
                self._available = False
        except ImportError:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    @staticmethod
    def authenticate():
        """
        Run one-time browser authentication.
        Opens a Google login page in your browser.
        After login, token is saved and future calls work without browser.
        """
        try:
            import ee
            print("\n[GEE] Opening browser for Google Earth Engine authentication...")
            print("[GEE] Log in with the Google account that has GEE access.\n")
            ee.Authenticate(auth_mode='localhost')
            ee.Initialize(project=GEE_PROJECT)
            GEEProvider._initialized = True
            print("[GEE] Authentication successful!\n")
            return True
        except Exception as e:
            print(f"[GEE] Authentication failed: {e}")
            return False

    def fetch_ndvi(self, lat: float, lon: float,
                   satellite: str = "Sentinel-2A",
                   date: Optional[str] = None,
                   window_days: int = 15,
                   corners: Optional[list] = None) -> Dict:
        """
        Fetch real NDVI for a plot location.

        Searches GEE for the clearest image within `window_days` of `date`.
        Computes NDVI = (NIR - Red) / (NIR + Red) over a 100m radius around the point.

        Args:
            lat: Latitude
            lon: Longitude
            satellite: Which satellite collection to use
            date: Target date (YYYY-MM-DD), defaults to today
            window_days: Look for images within this many days of date

        Returns:
            Dict with ndvi, health_score, cloud_cover, image_date, satellite_source
        """
        if not self._available or self._ee is None:
            return self._unavailable_response(lat, lon, date, satellite)

        ee = self._ee
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        target = datetime.strptime(date, "%Y-%m-%d")
        start  = (target - timedelta(days=window_days)).strftime("%Y-%m-%d")
        end    = (target + timedelta(days=window_days)).strftime("%Y-%m-%d")

        collection_id, nir_band, red_band, scale_m, cloud_field = GEE_COLLECTIONS.get(
            satellite, GEE_COLLECTIONS["Sentinel-2A"]
        )

        try:
            point = ee.Geometry.Point([lon, lat])

            # Use actual plot polygon if corners provided, else 100m buffer
            if corners and len(corners) >= 3:
                ring = [[c['lon'], c['lat']] for c in corners]
                ring.append(ring[0])  # close the ring
                region = ee.Geometry.Polygon([ring])
            else:
                region = point.buffer(100)

            # Get the least cloudy image in the window
            collection = (
                ee.ImageCollection(collection_id)
                .filterBounds(region)
                .filterDate(start, end)
                .filter(ee.Filter.lt(cloud_field, 50))
                .sort(cloud_field)
            )

            image = collection.first()

            # Check if an image was found
            count = collection.size().getInfo()
            if count == 0:
                return self._unavailable_response(lat, lon, date, satellite,
                                                  reason=f"No clear images in {window_days}-day window")

            # Compute NDVI
            ndvi_image = image.normalizedDifference([nir_band, red_band])

            # Sample NDVI over the plot region
            # normalizedDifference() returns band named 'nd' (not 'NDVI')
            ndvi_value = ndvi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=scale_m,
                maxPixels=1e8,
            ).get("nd").getInfo()

            # Cloud cover
            cloud_cover = float(
                image.get(cloud_field).getInfo() or 0
            )

            # Actual image date
            image_date = datetime.fromtimestamp(
                image.get("system:time_start").getInfo() / 1000
            ).strftime("%Y-%m-%d")

            if ndvi_value is None:
                return self._unavailable_response(lat, lon, date, satellite,
                                                  reason="NDVI computation returned None")

            ndvi_value = max(0.0, min(1.0, float(ndvi_value)))
            health     = self._ndvi_to_health(ndvi_value)

            return {
                "date":              image_date,
                "requested_date":    date,
                "latitude":          lat,
                "longitude":         lon,
                "ndvi":              round(ndvi_value, 4),
                "cloud_cover_percent": cloud_cover,
                "health_score":      health,
                "concern":           self._health_concern(health),
                "satellite_source":  satellite,
                "collection":        collection_id,
                "resolution_m":      scale_m,
                "image_available":   True,
                "data_source":       "gee_real",
            }

        except Exception as e:
            print(f"[GEE] Fetch error ({satellite}): {e}")
            return self._unavailable_response(lat, lon, date, satellite,
                                              reason=str(e))

    def fetch_ndvi_timeseries(self, lat: float, lon: float,
                              satellite: str = "Sentinel-2A",
                              days_back: int = 60) -> list:
        """
        Fetch NDVI time series for the past N days.

        Returns list of {date, ndvi, health_score, cloud_cover} dicts,
        one per available image, sorted oldest→newest.
        """
        if not self._available or self._ee is None:
            return []

        ee = self._ee
        end   = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        collection_id, nir_band, red_band, scale_m, cloud_field = GEE_COLLECTIONS.get(
            satellite, GEE_COLLECTIONS["Sentinel-2A"]
        )

        try:
            point = ee.Geometry.Point([lon, lat])

            collection = (
                ee.ImageCollection(collection_id)
                .filterBounds(point)
                .filterDate(start, end)
                .filter(ee.Filter.lt(cloud_field, 40))
                .sort("system:time_start")
            )

            images = collection.toList(collection.size())
            count  = collection.size().getInfo()

            results = []
            for i in range(min(count, 30)):
                try:
                    img   = ee.Image(images.get(i))
                    ndvi  = img.normalizedDifference([nir_band, red_band])
                    val   = ndvi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=point.buffer(100),
                        scale=scale_m,
                        maxPixels=1e8,
                    ).get("nd").getInfo()

                    if val is None:
                        continue

                    img_date = datetime.fromtimestamp(
                        img.get("system:time_start").getInfo() / 1000
                    ).strftime("%Y-%m-%d")

                    cloud = float(img.get(cloud_field).getInfo() or 0)
                    val   = max(0.0, min(1.0, float(val)))

                    results.append({
                        "date":          img_date,
                        "ndvi":          round(val, 4),
                        "health_score":  self._ndvi_to_health(val),
                        "cloud_cover":   cloud,
                        "satellite":     satellite,
                    })
                except Exception:
                    continue

            return results

        except Exception as e:
            print(f"[GEE] Timeseries error: {e}")
            return []

    # ── Helpers ────────────────────────────────────────────────────────────
    def _ndvi_to_health(self, ndvi: float) -> int:
        if ndvi < 0.2:
            return int(ndvi / 0.2 * 30)
        elif ndvi < 0.4:
            return int(30 + (ndvi - 0.2) / 0.2 * 30)
        else:
            return int(60 + min(ndvi - 0.4, 0.4) / 0.4 * 40)

    def _health_concern(self, score: int) -> str:
        if score < 40:
            return "Stress detected - possible water or pest issues"
        elif score < 70:
            return "Monitor closely - vegetation moderate"
        return "Healthy vegetation"

    def _unavailable_response(self, lat: float, lon: float,
                              date: Optional[str], satellite: str,
                              reason: str = "GEE not authenticated") -> Dict:
        return {
            "date":              date or datetime.now().strftime("%Y-%m-%d"),
            "latitude":          lat,
            "longitude":         lon,
            "ndvi":              None,
            "cloud_cover_percent": None,
            "health_score":      None,
            "satellite_source":  satellite,
            "image_available":   False,
            "data_source":       "gee_unavailable",
            "reason":            reason,
        }
