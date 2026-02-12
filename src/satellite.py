"""
Satellite monitoring service with multi-provider support.

Calculates NDVI and crop health scores from satellite imagery.
Supports multiple satellite data providers:
- Google Earth Engine (Sentinel-2A/2B + Landsat-8/9) — PRIMARY, real imagery
- Sentinel Hub (Sentinel-2A/2B) - 10m resolution
- USGS Earth Explorer (Landsat-8/9) - 30m resolution

When GEE is authenticated, ALL satellites use real data automatically.
Without auth, generates realistic mock data for development.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import numpy as np
from dotenv import load_dotenv

from src.satellite_manager import SatelliteManager
from src.gee_provider import GEEProvider

load_dotenv()


class SatelliteMonitor:
    """Monitors crop health using satellite imagery from multiple providers."""

    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialize satellite monitor.

        Automatically detects available API keys and configures providers.
        GEE is tried first (real imagery). Falls back to mock if not authenticated.

        Args:
            client_id: Sentinel Hub Client ID (or from env SENTINEL_CLIENT_ID)
            client_secret: Sentinel Hub Client Secret (or from env SENTINEL_CLIENT_SECRET)
        """
        self.client_id = client_id or os.getenv("SENTINEL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SENTINEL_CLIENT_SECRET")
        self.last_reading_cache = {}

        # Initialize multi-satellite manager
        self.sat_manager = SatelliteManager()

        # Initialize GEE provider (primary real-data source)
        self.gee = GEEProvider()
        if self.gee.available:
            print("[OK] Google Earth Engine initialized — using real satellite imagery")
        else:
            print("[INFO] GEE not authenticated — using mock data. Run: python gee_auth.py")

        # Try to configure Sentinel Hub (secondary)
        self.sentinel_config = None
        if self.client_id and self.client_secret:
            try:
                from sentinelhub.config import SHConfig
                self.sentinel_config = SHConfig()
                self.sentinel_config.sh_client_id = self.client_id
                self.sentinel_config.sh_client_secret = self.client_secret
            except ImportError:
                pass

    def calculate_ndvi(self, nir_band: float, red_band: float) -> float:
        """
        Calculate NDVI (Normalized Difference Vegetation Index).
        Formula: (NIR - Red) / (NIR + Red)

        Args:
            nir_band: Near-infrared band value
            red_band: Red band value

        Returns:
            NDVI value between 0 and 1
        """
        try:
            denominator = nir_band + red_band
            if denominator == 0:
                return 0.0
            ndvi = (nir_band - red_band) / denominator
            return max(0.0, min(1.0, ndvi))
        except Exception as e:
            print(f"[WARN] NDVI calculation error: {e}")
            return 0.5

    def check_cloud_cover(self, cloud_cover_percent: float) -> bool:
        """
        Check if cloud cover is acceptable for analysis.

        Args:
            cloud_cover_percent: Percentage of cloud cover

        Returns:
            True if acceptable (< 30%), False otherwise
        """
        return cloud_cover_percent < 30

    def ndvi_to_health_score(self, ndvi: float) -> int:
        """
        Map NDVI value to 0-100 health score.

        Mapping:
            0.0-0.2 -> 0-30  (Stress/Bare soil)
            0.2-0.4 -> 30-60 (Moderate/Sparse vegetation)
            0.4-0.8 -> 60-100 (Healthy/Dense vegetation)
        """
        try:
            if ndvi < 0.2:
                health = int(ndvi / 0.2 * 30)
            elif ndvi < 0.4:
                health = int(30 + (ndvi - 0.2) / 0.2 * 30)
            else:
                health = int(60 + min(ndvi - 0.4, 0.4) / 0.4 * 40)
            return max(0, min(100, health))
        except Exception as e:
            print(f"[WARN] Health score calculation error: {e}")
            return 50

    def get_health_concern(self, health_score: int) -> str:
        """Get concern message based on health score."""
        if health_score < 40:
            return "Stress detected - possible water or pest issues"
        elif health_score < 70:
            return "Monitor closely - vegetation moderate"
        else:
            return "Healthy vegetation"

    def fetch_satellite_data(self, lat: float, lon: float,
                             date: Optional[str] = None,
                             satellite: Optional[str] = None,
                             corners: Optional[list] = None) -> Dict:
        """
        Fetch satellite data for given coordinates.

        Auto-selects the best available satellite if none specified.
        Uses real API when keys are configured, otherwise uses mock data.

        Args:
            lat: Latitude
            lon: Longitude
            date: Date (YYYY-MM-DD), defaults to today
            satellite: Force a specific satellite, or None for auto-select

        Returns:
            Dictionary with satellite data including ndvi, health_score, etc.
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Auto-select satellite if not specified
        if satellite is None:
            sat_name, _ = self.sat_manager.select_best_satellite()
        else:
            sat_name = satellite

        # Check if we have API keys for this satellite's provider
        provider = self.sat_manager.catalog.get(sat_name, {}).get("api_provider", "")
        has_key = self.sat_manager.available_providers.get(provider, False)

        try:
            # 1st priority: Google Earth Engine (real imagery, all satellites)
            if self.gee.available:
                result = self.gee.fetch_ndvi(lat, lon, satellite=sat_name, date=date, corners=corners)
                if result.get("image_available") and result.get("ndvi") is not None:
                    # Normalize to standard response format
                    return {
                        "date":                result["date"],
                        "latitude":            lat,
                        "longitude":           lon,
                        "ndvi":                result["ndvi"],
                        "cloud_cover_percent": result.get("cloud_cover_percent", 0),
                        "health_score":        result["health_score"],
                        "concern":             result["concern"],
                        "satellite_source":    sat_name,
                        "image_available":     True,
                        "data_source":         "gee_real",
                        "resolution_m":        result.get("resolution_m", 10),
                    }

            # 2nd priority: Sentinel Hub direct API
            if has_key and provider == "sentinel_hub" and self.sentinel_config:
                return self._fetch_sentinel_hub(lat, lon, date, sat_name)

            # 3rd priority: USGS direct API
            elif has_key and provider == "usgs_earth_explorer":
                return self._fetch_usgs(lat, lon, date, sat_name)

            # Fallback: realistic mock data
            return self._fetch_mock(lat, lon, date, sat_name)

        except Exception as e:
            print(f"[WARN] Satellite fetch error ({sat_name}): {e}")
            return self._fetch_mock(lat, lon, date, sat_name)

    def _fetch_sentinel_hub(self, lat: float, lon: float,
                            date: str, sat_name: str) -> Dict:
        """
        Fetch real data from Sentinel Hub API.

        Requires sentinelhub package and valid API keys.
        When implemented, this will:
        1. Create a BBox around the coordinates
        2. Request Sentinel-2 L2A data
        3. Extract NIR and Red bands
        4. Calculate NDVI
        5. Return actual satellite-derived health metrics
        """
        # TODO: Implement real Sentinel Hub API call when keys are valid
        # The structure is ready - just need valid credentials:
        #
        # from sentinelhub import (SHConfig, BBox, CRS, SentinelHubRequest,
        #                          DataCollection, MimeType, bbox_to_dimensions)
        #
        # resolution = 10  # meters
        # bbox = BBox([lon-0.005, lat-0.005, lon+0.005, lat+0.005], crs=CRS.WGS84)
        # size = bbox_to_dimensions(bbox, resolution=resolution)
        #
        # evalscript = '''
        # //VERSION=3
        # function setup() {
        #   return { input: ["B04", "B08"], output: { bands: 2 } };
        # }
        # function evaluatePixel(sample) {
        #   return [sample.B08, sample.B04];
        # }
        # '''
        #
        # request = SentinelHubRequest(
        #     evalscript=evalscript,
        #     input_data=[SentinelHubRequest.input_data(
        #         data_collection=DataCollection.SENTINEL2_L2A,
        #         time_interval=(date, date),
        #     )],
        #     responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        #     bbox=bbox, size=size, config=self.sentinel_config,
        # )
        # data = request.get_data()[0]
        # nir = data[:,:,0].mean()
        # red = data[:,:,1].mean()
        # ndvi = self.calculate_ndvi(nir, red)

        # For now, fall through to mock until credentials are validated
        return self._fetch_mock(lat, lon, date, sat_name)

    def _fetch_usgs(self, lat: float, lon: float,
                    date: str, sat_name: str) -> Dict:
        """
        Fetch real data from USGS Earth Explorer (Landsat).

        TODO: Implement when USGS credentials are provided.
        Uses the USGS M2M API for Landsat-8/9 data.
        """
        return self._fetch_mock(lat, lon, date, sat_name)

    def _fetch_mock(self, lat: float, lon: float,
                    date: str, sat_name: str) -> Dict:
        """
        Generate realistic mock satellite data.

        Produces consistent-per-location values with seasonal variation
        and daily noise to simulate real satellite behavior.
        """
        day_of_year = datetime.strptime(date, "%Y-%m-%d").timetuple().tm_yday

        # Base NDVI from coordinates (consistent per location)
        base = 0.4 + (hash(f"{lat:.4f}_{lon:.4f}") % 30) / 100

        # Seasonal variation (Jowar: Kharif Jun-Oct, Rabi Oct-Feb)
        seasonal = 0.1 * np.sin(2 * np.pi * (day_of_year - 180) / 365)

        # Daily noise
        daily_noise = (hash(f"{day_of_year}_{lat:.4f}") % 10 - 5) / 100

        ndvi = max(0.15, min(0.85, base + seasonal + daily_noise))
        ndvi = round(ndvi, 4)
        cloud_cover = max(0, min(80, (hash(f"cloud_{day_of_year}_{lat:.2f}") % 40)))
        health_score = self.ndvi_to_health_score(ndvi)

        data = {
            "date": date,
            "latitude": lat,
            "longitude": lon,
            "ndvi": ndvi,
            "cloud_cover_percent": float(cloud_cover),
            "health_score": health_score,
            "concern": self.get_health_concern(health_score),
            "satellite_source": sat_name,
            "image_available": True,
            "data_source": "mock",
        }

        self.last_reading_cache[f"{lat},{lon}"] = data
        return data

    def monitor_plot(self, plot_info: Dict) -> Dict:
        """
        Monitor a plot's health using the best available satellite.

        Args:
            plot_info: Plot dict with center_latitude, center_longitude, etc.

        Returns:
            Dictionary with health analysis and recommendation
        """
        try:
            lat = plot_info.get("center_latitude")
            lon = plot_info.get("center_longitude")

            if not lat or not lon:
                return {"error": "Plot coordinates missing"}

            corners = plot_info.get("corners") or []
            satellite_data = self.fetch_satellite_data(lat, lon, corners=corners or None)
            health_score = satellite_data["health_score"]

            if health_score < 40:
                recommendation = "Check for water stress or pests immediately"
            elif health_score < 60:
                recommendation = "Monitor closely, may need intervention soon"
            else:
                recommendation = "Vegetation looking healthy, continue regular maintenance"

            return {
                "plot_name": plot_info.get("name_english", "Unknown"),
                "plot_name_telugu": plot_info.get("name_telugu", ""),
                "crop": plot_info.get("crop_type_english", "Unknown"),
                "ndvi": satellite_data["ndvi"],
                "health_score": health_score,
                "concern": satellite_data["concern"],
                "recommendation": recommendation,
                "cloud_cover": satellite_data["cloud_cover_percent"],
                "satellite_source": satellite_data["satellite_source"],
                "date_checked": satellite_data["date"],
                "acceptable_data": self.check_cloud_cover(
                    satellite_data["cloud_cover_percent"]
                ),
            }

        except Exception as e:
            print(f"[WARN] Plot monitoring error: {e}")
            return {"error": str(e)}
