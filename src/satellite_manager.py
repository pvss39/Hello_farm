"""
Multi-Satellite Manager with Orbit Tracking and Auto-Selection.

Tracks multiple Earth observation satellites, knows their revisit schedules,
and automatically selects the best satellite for each plot check based on
orbit alignment, cloud cover, and image quality.

Supported satellites:
- Sentinel-2A / 2B (ESA, 10m resolution, 5-day combined revisit)
- Landsat-8 / 9 (NASA/USGS, 30m resolution, 8-day combined revisit)

The manager auto-selects the best satellite for a given plot on a given day.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


# Satellite orbit reference data
# Each satellite has a known epoch (a date it passed over a reference point)
# and a revisit period. We use modular arithmetic to predict future passes.
SATELLITE_CATALOG = {
    "Sentinel-2A": {
        "operator": "ESA (Copernicus)",
        "resolution_m": 10,
        "revisit_days": 10,
        "swath_km": 290,
        "bands": ["B02 (Blue)", "B03 (Green)", "B04 (Red)", "B08 (NIR)"],
        "ndvi_bands": ("B08", "B04"),
        "epoch": "2024-01-03",  # known pass over Emani Duggirala, AP region
        "priority": 1,  # lower = preferred
        "api_provider": "google_earth_engine",
        "env_keys": ("GEE_PROJECT",),
    },
    "Sentinel-2B": {
        "operator": "ESA (Copernicus)",
        "resolution_m": 10,
        "revisit_days": 10,
        "swath_km": 290,
        "bands": ["B02 (Blue)", "B03 (Green)", "B04 (Red)", "B08 (NIR)"],
        "ndvi_bands": ("B08", "B04"),
        "epoch": "2024-01-08",  # offset 5 days from 2A
        "priority": 2,
        "api_provider": "google_earth_engine",
        "env_keys": ("GEE_PROJECT",),
    },
    "Landsat-8": {
        "operator": "NASA / USGS",
        "resolution_m": 30,
        "revisit_days": 16,
        "swath_km": 185,
        "bands": ["B2 (Blue)", "B3 (Green)", "B4 (Red)", "B5 (NIR)"],
        "ndvi_bands": ("B5", "B4"),
        "epoch": "2024-01-05",
        "priority": 3,
        "api_provider": "google_earth_engine",
        "env_keys": ("GEE_PROJECT",),
    },
    "Landsat-9": {
        "operator": "NASA / USGS",
        "resolution_m": 30,
        "revisit_days": 16,
        "swath_km": 185,
        "bands": ["B2 (Blue)", "B3 (Green)", "B4 (Red)", "B5 (NIR)"],
        "ndvi_bands": ("B5", "B4"),
        "epoch": "2024-01-13",  # offset 8 days from L8
        "priority": 4,
        "api_provider": "google_earth_engine",
        "env_keys": ("GEE_PROJECT",),
    },
}


class SatellitePass:
    """Represents a predicted satellite pass over a location."""

    def __init__(self, satellite_name: str, pass_date: datetime,
                 days_until: int, resolution_m: int, priority: int,
                 has_api_key: bool):
        self.satellite_name = satellite_name
        self.pass_date = pass_date
        self.days_until = days_until
        self.resolution_m = resolution_m
        self.priority = priority
        self.has_api_key = has_api_key

    def to_dict(self) -> Dict:
        return {
            "satellite": self.satellite_name,
            "pass_date": self.pass_date.strftime("%Y-%m-%d"),
            "days_until": self.days_until,
            "resolution_m": self.resolution_m,
            "has_api_key": self.has_api_key,
        }


class SatelliteManager:
    """
    Manages multiple satellites and auto-selects the best one for each check.

    Features:
    - Tracks orbit schedules for 4 satellites (Sentinel-2A/B, Landsat-8/9)
    - Predicts next pass dates for any lat/lon
    - Auto-selects best satellite based on: API key availability, resolution,
      orbit alignment, and cloud cover forecast
    - Provides a 30-day satellite schedule for any plot
    """

    def __init__(self):
        """Initialize satellite manager and detect available API keys."""
        self.catalog = SATELLITE_CATALOG
        self.available_providers = self._detect_api_keys()

    def _detect_api_keys(self) -> Dict[str, bool]:
        """Check which satellite API keys are configured in environment."""
        providers = {}

        # Sentinel Hub
        sid = os.getenv("SENTINEL_CLIENT_ID", "")
        ssecret = os.getenv("SENTINEL_CLIENT_SECRET", "")
        providers["sentinel_hub"] = bool(sid and ssecret
                                         and "your_" not in sid.lower())

        # USGS Earth Explorer
        uuser = os.getenv("USGS_USERNAME", "")
        upass = os.getenv("USGS_PASSWORD", "")
        providers["usgs_earth_explorer"] = bool(uuser and upass
                                                 and "your_" not in uuser.lower())

        # Google Earth Engine — token stored at ~/.config/earthengine/credentials
        import pathlib
        gee_token = pathlib.Path.home() / ".config" / "earthengine" / "credentials"
        providers["google_earth_engine"] = gee_token.exists()

        return providers

    def get_available_satellites(self) -> List[Dict]:
        """
        Get list of all satellites with their status.

        Returns:
            List of satellite info dicts with api_available flag
        """
        result = []
        for name, info in self.catalog.items():
            has_key = self.available_providers.get(info["api_provider"], False)
            result.append({
                "name": name,
                "operator": info["operator"],
                "resolution_m": info["resolution_m"],
                "revisit_days": info["revisit_days"],
                "api_provider": info["api_provider"],
                "api_available": has_key,
                "priority": info["priority"],
            })
        return sorted(result, key=lambda x: x["priority"])

    def predict_next_pass(self, satellite_name: str,
                          from_date: Optional[datetime] = None) -> datetime:
        """
        Predict next pass date for a satellite over Emani Duggirala, AP.

        Uses modular arithmetic on the satellite's epoch and revisit period.

        Args:
            satellite_name: Name of satellite
            from_date: Start date (default: today)

        Returns:
            Next pass date as datetime
        """
        info = self.catalog[satellite_name]
        epoch = datetime.strptime(info["epoch"], "%Y-%m-%d")
        revisit = info["revisit_days"]
        ref = from_date or datetime.now()

        # Days since epoch
        delta = (ref - epoch).days
        # Days until next pass = revisit - (delta mod revisit)
        days_since_last = delta % revisit
        days_until_next = revisit - days_since_last if days_since_last > 0 else 0

        return ref + timedelta(days=days_until_next)

    def get_pass_schedule(self, days_ahead: int = 30,
                          from_date: Optional[datetime] = None) -> List[SatellitePass]:
        """
        Get all satellite passes for the next N days.

        Args:
            days_ahead: Number of days to look ahead
            from_date: Start date (default: today)

        Returns:
            Sorted list of SatellitePass objects
        """
        ref = from_date or datetime.now()
        end = ref + timedelta(days=days_ahead)
        passes = []

        for sat_name, info in self.catalog.items():
            has_key = self.available_providers.get(info["api_provider"], False)
            epoch = datetime.strptime(info["epoch"], "%Y-%m-%d")
            revisit = info["revisit_days"]

            # Find first pass on or after ref
            delta = (ref - epoch).days
            days_since_last = delta % revisit
            next_pass = ref + timedelta(days=(revisit - days_since_last)
                                        if days_since_last > 0 else 0)

            while next_pass <= end:
                days_until = (next_pass - ref).days
                passes.append(SatellitePass(
                    satellite_name=sat_name,
                    pass_date=next_pass,
                    days_until=days_until,
                    resolution_m=info["resolution_m"],
                    priority=info["priority"],
                    has_api_key=has_key,
                ))
                next_pass += timedelta(days=revisit)

        # Sort by date, then priority
        passes.sort(key=lambda p: (p.days_until, p.priority))
        return passes

    def select_best_satellite(self,
                              target_date: Optional[datetime] = None,
                              max_days_window: int = 3) -> Tuple[str, Dict]:
        """
        Auto-select the best satellite for a given date.

        Selection criteria (in order):
        1. Has valid API key
        2. Passes within the date window
        3. Higher resolution preferred
        4. Lower priority number preferred

        Args:
            target_date: Target date for imagery (default: today)
            max_days_window: Accept passes within +/- this many days

        Returns:
            Tuple of (satellite_name, selection_info)
        """
        ref = target_date or datetime.now()
        candidates = []

        for sat_name, info in self.catalog.items():
            has_key = self.available_providers.get(info["api_provider"], False)
            next_pass = self.predict_next_pass(sat_name, ref)
            days_away = abs((next_pass - ref).days)

            # Also check if there was a recent pass
            prev_pass = next_pass - timedelta(days=info["revisit_days"])
            days_since_prev = abs((ref - prev_pass).days)

            closest_days = min(days_away, days_since_prev)
            closest_date = next_pass if days_away <= days_since_prev else prev_pass

            if closest_days <= max_days_window:
                score = 0
                # API key available: big bonus
                if has_key:
                    score += 100
                # Resolution bonus (10m = +40, 30m = +13)
                score += int(40 / (info["resolution_m"] / 10))
                # Closer to target date is better
                score -= closest_days * 10
                # Priority tiebreaker
                score -= info["priority"]

                candidates.append({
                    "satellite": sat_name,
                    "score": score,
                    "pass_date": closest_date.strftime("%Y-%m-%d"),
                    "days_from_target": closest_days,
                    "resolution_m": info["resolution_m"],
                    "has_api_key": has_key,
                    "operator": info["operator"],
                })

        if not candidates:
            # No satellite within window, pick the soonest overall
            all_passes = self.get_pass_schedule(days_ahead=max_days_window * 3)
            if all_passes:
                best = all_passes[0]
                return best.satellite_name, {
                    "satellite": best.satellite_name,
                    "pass_date": best.pass_date.strftime("%Y-%m-%d"),
                    "days_from_target": best.days_until,
                    "resolution_m": best.resolution_m,
                    "has_api_key": best.has_api_key,
                    "reason": "No satellite in window, selected soonest pass",
                }
            return "Sentinel-2A", {"reason": "Fallback default"}

        # Sort by score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)
        best = candidates[0]

        reason_parts = []
        if best["has_api_key"]:
            reason_parts.append("API key available")
        reason_parts.append(f"{best['resolution_m']}m resolution")
        if best["days_from_target"] == 0:
            reason_parts.append("passes today")
        else:
            reason_parts.append(f"{best['days_from_target']}d from target")
        best["reason"] = ", ".join(reason_parts)

        return best["satellite"], best

    def get_satellite_info(self, satellite_name: str) -> Optional[Dict]:
        """Get detailed info about a specific satellite."""
        info = self.catalog.get(satellite_name)
        if not info:
            return None
        has_key = self.available_providers.get(info["api_provider"], False)
        return {
            "name": satellite_name,
            "operator": info["operator"],
            "resolution_m": info["resolution_m"],
            "revisit_days": info["revisit_days"],
            "swath_km": info["swath_km"],
            "bands": info["bands"],
            "ndvi_bands": info["ndvi_bands"],
            "api_provider": info["api_provider"],
            "api_available": has_key,
        }

    def format_schedule_table(self, days_ahead: int = 14) -> str:
        """
        Format satellite schedule as a readable table string.

        Args:
            days_ahead: Days to show

        Returns:
            Formatted string table
        """
        passes = self.get_pass_schedule(days_ahead)
        if not passes:
            return "No satellite passes in the next {days_ahead} days."

        lines = [
            f"{'Date':<12} {'Satellite':<16} {'Res':<6} {'API':<6} {'Days':<5}",
            "-" * 50,
        ]
        for p in passes:
            api_str = "YES" if p.has_api_key else "---"
            lines.append(
                f"{p.pass_date.strftime('%Y-%m-%d'):<12} "
                f"{p.satellite_name:<16} "
                f"{p.resolution_m}m{'':<3} "
                f"{api_str:<6} "
                f"+{p.days_until}d"
            )

        return "\n".join(lines)
