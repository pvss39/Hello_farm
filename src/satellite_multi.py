from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

# earthengine-api is imported lazily so the module loads even without auth


class MultiSatelliteManager:
    """
    Pulls NDVI from 4 satellites — Sentinel-2A/2B (10m) + Landsat-8/9 (30m).
    Scores candidates by recency, cloud cover, resolution. Falls back to
    Sentinel Hub if GEE is not authenticated.
    """

    _COLLECTIONS = {
        "Sentinel-2A": {
            "id":         "COPERNICUS/S2_SR_HARMONIZED",
            "nir":        "B8",
            "red":        "B4",
            "cloud_prop": "CLOUDY_PIXEL_PERCENTAGE",
            "scale_m":    10,
        },
        "Sentinel-2B": {
            "id":         "COPERNICUS/S2_SR_HARMONIZED",
            "nir":        "B8",
            "red":        "B4",
            "cloud_prop": "CLOUDY_PIXEL_PERCENTAGE",
            "scale_m":    10,
        },
        "Landsat-8": {
            "id":         "LANDSAT/LC08/C02/T1_L2",
            "nir":        "SR_B5",
            "red":        "SR_B4",
            "cloud_prop": "CLOUD_COVER",
            "scale_m":    30,
        },
        "Landsat-9": {
            "id":         "LANDSAT/LC09/C02/T1_L2",
            "nir":        "SR_B5",
            "red":        "SR_B4",
            "cloud_prop": "CLOUD_COVER",
            "scale_m":    30,
        },
    }

    def __init__(self) -> None:
        self.initialized = self._init_gee()

    def get_latest_ndvi(
        self,
        latitude: float,
        longitude: float,
        days_lookback: int = 7,
        buffer_meters: int = 50,
    ) -> Optional[Dict]:
        if not self.initialized:
            return self._fallback(latitude, longitude)

        import ee  # type: ignore[import-untyped]

        end_date   = datetime.now()
        start_date = end_date - timedelta(days=days_lookback)
        date_range = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

        point    = ee.Geometry.Point([longitude, latitude])
        geometry = point.buffer(buffer_meters)

        print(f"\n[MultiSat] Searching {latitude:.4f}, {longitude:.4f} "
              f"| {date_range[0]} → {date_range[1]}")

        candidates: List[Dict] = []

        s2 = self._query_collection(geometry, date_range, "Sentinel-2A")
        if s2:
            candidates.append(s2)
            print(f"  Sentinel-2: {s2['date']} NDVI={s2['ndvi']:.3f} clouds={s2['cloud_cover']:.0f}%")

        l8 = self._query_collection(geometry, date_range, "Landsat-8")
        if l8:
            candidates.append(l8)
            print(f"  Landsat-8 : {l8['date']} NDVI={l8['ndvi']:.3f} clouds={l8['cloud_cover']:.0f}%")

        l9 = self._query_collection(geometry, date_range, "Landsat-9")
        if l9:
            candidates.append(l9)
            print(f"  Landsat-9 : {l9['date']} NDVI={l9['ndvi']:.3f} clouds={l9['cloud_cover']:.0f}%")

        if not candidates:
            print("  No recent imagery found — trying fallback")
            return self._fallback(latitude, longitude)

        best = self._select_best(candidates)
        print(f"[MultiSat] Selected: {best['satellite']} "
              f"| NDVI={best['ndvi']:.3f} | confidence={best['confidence']:.0%}")
        return best

    def _query_collection(self, geometry, date_range: List[str], satellite_name: str) -> Optional[Dict]:
        try:
            import ee  # type: ignore[import-untyped]

            spec = self._COLLECTIONS[satellite_name]
            collection = (
                ee.ImageCollection(spec["id"])
                .filterBounds(geometry)
                .filterDate(date_range[0], date_range[1])
                .filter(ee.Filter.lt(spec["cloud_prop"], 50))
            )

            if collection.size().getInfo() == 0:
                return None

            image    = collection.sort("system:time_start", False).first()
            ndvi_img = image.normalizedDifference([spec["nir"], spec["red"]])

            stats = ndvi_img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=spec["scale_m"],
                maxPixels=int(1e9),
            ).getInfo()

            ndvi_val = stats.get("nd")
            if ndvi_val is None:
                return None

            props     = image.getInfo()["properties"]
            timestamp = props["system:time_start"] / 1000
            date_str  = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            age_days  = (datetime.now() - datetime.strptime(date_str, "%Y-%m-%d")).days

            spacecraft   = props.get("SPACECRAFT_NAME", satellite_name)
            display_name = spacecraft if satellite_name.startswith("Sentinel") and spacecraft else satellite_name

            return {
                "ndvi":         round(float(ndvi_val), 4),
                "date":         date_str,
                "satellite":    display_name,
                "cloud_cover":  float(props.get(spec["cloud_prop"], 0)),
                "resolution_m": spec["scale_m"],
                "source":       "GEE",
                "age_days":     age_days,
            }

        except Exception as exc:
            print(f"  [MultiSat] {satellite_name} query error: {exc}")
            return None

    def _select_best(self, candidates: List[Dict]) -> Dict:
        # 50% recency, 30% cloud-free, 20% resolution
        scored = []
        for img in candidates:
            recency    = max(0, 100 - img["age_days"] * 10)
            clouds     = 100 - img["cloud_cover"]
            resolution = (10 / img["resolution_m"]) * 100
            score = recency * 0.5 + clouds * 0.3 + resolution * 0.2
            scored.append({**img, "score": score, "confidence": round(min(1.0, score / 100), 2)})

        return max(scored, key=lambda x: x["score"])

    def get_ndvi_image(
        self,
        latitude: float,
        longitude: float,
        corners: Optional[list] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a false-color NDVI heatmap image for the plot.

        Uses GEE's getThumbURL — returns a local JPEG file path, or None if
        GEE is not available / no recent image found.

        Palette: red (stressed, NDVI≈0) → yellow → green (healthy, NDVI≈0.8)
        """
        if not self.initialized:
            print("[MultiSat] GEE not initialized — cannot generate NDVI image")
            return None

        try:
            import ee          # type: ignore[import-untyped]
            import requests
            from pathlib import Path

            # Build geometry — polygon from corners if available, else 200m buffer
            if corners and len(corners) >= 3:
                ring = [[c["lon"], c["lat"]] for c in corners]
                ring.append(ring[0])   # close polygon
                geometry = ee.Geometry.Polygon([ring])
            else:
                geometry = ee.Geometry.Point([longitude, latitude]).buffer(200)

            end_date   = datetime.now()
            start_date = end_date - timedelta(days=30)

            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geometry)
                .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )

            if collection.size().getInfo() == 0:
                print("[MultiSat] No cloud-free S2 image in last 30 days — no thumbnail")
                return None

            image    = collection.first()
            ndvi_img = image.normalizedDifference(["B8", "B4"])

            viz_params = {
                "min":        0.0,
                "max":        0.8,
                "palette":    ["#d73027", "#f46d43", "#fdae61", "#fee08b", "#a6d96a", "#1a9850"],
                "region":     geometry.getInfo(),
                "format":     "jpg",
                "dimensions": 512,
            }

            url      = ndvi_img.getThumbURL(viz_params)
            response = requests.get(url, timeout=45)

            if response.status_code != 200:
                print(f"[MultiSat] Thumbnail download failed: HTTP {response.status_code}")
                return None

            # Save to data/images/
            if output_path is None:
                img_dir = Path("data") / "images"
                img_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(img_dir / f"ndvi_{ts}.jpg")

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as fh:
                fh.write(response.content)

            print(f"[MultiSat] NDVI image saved: {output_path}")
            return output_path

        except Exception as exc:
            print(f"[MultiSat] Image generation error: {exc}")
            return None

    def _fallback(self, latitude: float, longitude: float) -> Optional[Dict]:
        try:
            from src.satellite import SatelliteMonitor

            monitor = SatelliteMonitor()
            result  = monitor.monitor_plot(
                {"center_latitude": latitude, "center_longitude": longitude, "name_english": "fallback"}
            )

            if result and result.get("ndvi") is not None:
                return {
                    "ndvi":         round(float(result["ndvi"]), 4),
                    "date":         datetime.now().strftime("%Y-%m-%d"),
                    "satellite":    result.get("satellite_name", "Sentinel Hub"),
                    "cloud_cover":  float(result.get("cloud_cover_percent", 0)),
                    "resolution_m": 10,
                    "source":       "fallback",
                    "age_days":     0,
                    "confidence":   0.6,
                }
        except Exception as exc:
            print(f"[MultiSat] Fallback error: {exc}")

        return None

    def _init_gee(self) -> bool:
        try:
            import ee  # type: ignore[import-untyped]
            import os
            import pathlib

            creds = pathlib.Path.home() / ".config" / "earthengine" / "credentials"
            if not creds.exists():
                print("[MultiSat] GEE credentials not found — run: earthengine authenticate")
                return False

            project = os.getenv("GEE_PROJECT", "my-spread-sheet-473920")
            ee.Initialize(project=project)
            print("[MultiSat] Google Earth Engine: connected")
            return True

        except ImportError:
            print("[MultiSat] earthengine-api not installed — run: pip install earthengine-api")
            return False
        except Exception as exc:
            print(f"[MultiSat] GEE init failed: {exc}")
            return False
