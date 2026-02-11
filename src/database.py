import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any


class FarmDatabase:

    def __init__(self, db_path: str = "data/farm.db") -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def init_database(self) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_english TEXT UNIQUE NOT NULL,
                    name_telugu TEXT NOT NULL,
                    crop_type_english TEXT NOT NULL,
                    crop_type_telugu TEXT NOT NULL,
                    size_acres REAL NOT NULL,
                    center_latitude REAL NOT NULL,
                    center_longitude REAL NOT NULL,
                    irrigation_frequency_days INTEGER NOT NULL,
                    last_irrigated TIMESTAMP,
                    notes TEXT,
                    boundary_geojson TEXT,
                    whatsapp_number TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # add new columns to existing databases without breaking them
            for col in ["ALTER TABLE plots ADD COLUMN boundary_geojson TEXT",
                        "ALTER TABLE plots ADD COLUMN whatsapp_number TEXT"]:
                try:
                    cursor.execute(col)
                except sqlite3.OperationalError:
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS irrigation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plot_id INTEGER NOT NULL,
                    irrigated_date TIMESTAMP NOT NULL,
                    ndvi_reading REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plot_id) REFERENCES plots(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS satellite_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plot_id INTEGER NOT NULL,
                    check_date TIMESTAMP NOT NULL,
                    satellite_source TEXT NOT NULL,
                    ndvi_value REAL NOT NULL,
                    cloud_cover_percent REAL,
                    health_score REAL,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plot_id) REFERENCES plots(id)
                )
            """)

            # tracks which dates we already sent WhatsApp for — no duplicate alerts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS satellite_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plot_id INTEGER NOT NULL,
                    satellite_date TEXT NOT NULL,
                    satellite_name TEXT,
                    ndvi REAL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(plot_id, satellite_date),
                    FOREIGN KEY (plot_id) REFERENCES plots(id)
                )
            """)

            conn.commit()
            print("[OK] Database tables initialized")
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def add_plot(
        self,
        name_en: str,
        name_te: str,
        crop_en: str,
        crop_te: str,
        size: float,
        lat: float,
        lon: float,
        freq: int,
        corners: Optional[List[Dict]] = None,
        whatsapp_number: Optional[str] = None,
    ) -> Optional[int]:
        # compute center from corners if given
        if corners and len(corners) >= 3:
            lat = sum(c["lat"] for c in corners) / len(corners)
            lon = sum(c["lon"] for c in corners) / len(corners)

        boundary_json = json.dumps(corners) if corners else None
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO plots (
                    name_english, name_telugu, crop_type_english, crop_type_telugu,
                    size_acres, center_latitude, center_longitude, irrigation_frequency_days,
                    boundary_geojson, whatsapp_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name_en, name_te, crop_en, crop_te, size, lat, lon, freq,
                 boundary_json, whatsapp_number or None),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"[ERROR] Plot '{name_en}' already exists")
            raise
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def log_irrigation(
        self, plot_name: str, date: Optional[str] = None, ndvi: Optional[float] = None, notes: str = ""
    ) -> Optional[int]:
        conn = None
        try:
            plot_info = self.get_plot_info(plot_name)
            if not plot_info:
                raise ValueError(f"Plot '{plot_name}' not found")

            plot_id = plot_info["id"]
            irrigated_date = date or datetime.now().isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE plots SET last_irrigated = ? WHERE id = ?",
                (irrigated_date, plot_id),
            )
            cursor.execute(
                """
                INSERT INTO irrigation_log (plot_id, irrigated_date, ndvi_reading, notes)
                VALUES (?, ?, ?, ?)
                """,
                (plot_id, irrigated_date, ndvi, notes),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_plot_info(self, plot_name: str) -> Optional[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            def _enrich(d, name):
                d['name'] = d.get('name_english', name)
                d['crop_type'] = d.get('crop_type_english', '')
                raw = d.get('boundary_geojson')
                d['corners'] = json.loads(raw) if raw else []
                return d

            cursor.execute(
                "SELECT * FROM plots WHERE LOWER(name_english) = LOWER(?)", (plot_name,)
            )
            row = cursor.fetchone()
            if row:
                return _enrich(dict(row), plot_name)

            cursor.execute(
                "SELECT * FROM plots WHERE LOWER(name_telugu) = LOWER(?)", (plot_name,)
            )
            row = cursor.fetchone()
            if row:
                return _enrich(dict(row), plot_name)

            return None
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_all_plots(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plots ORDER BY id")
            plots = []
            for row in cursor.fetchall():
                p = dict(row)
                p['name'] = p.get('name_english', '')
                p['crop_type'] = p.get('crop_type_english', '')
                raw = p.get('boundary_geojson')
                p['corners'] = json.loads(raw) if raw else []
                plots.append(p)
            return plots
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def check_irrigation_needed(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plots")
            plots_raw = [dict(row) for row in cursor.fetchall()]

            needs_irrigation = []
            for plot in plots_raw:
                if plot["last_irrigated"] is None:
                    days_overdue = plot["irrigation_frequency_days"]
                else:
                    last_date = datetime.fromisoformat(plot["last_irrigated"])
                    days_since = (datetime.now() - last_date).days
                    days_overdue = days_since - plot["irrigation_frequency_days"]

                if days_overdue >= 0:
                    needs_irrigation.append({
                        'name': plot.get('name_english', ''),
                        'crop': plot.get('crop_type_english', ''),
                        'days_overdue': days_overdue,
                        'last_irrigated': plot.get('last_irrigated', 'Never'),
                    })

            return needs_irrigation
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_satellite_history(self, plot_name: str, days: int = 30) -> List[Dict[str, Any]]:
        conn = None
        try:
            plot_info = self.get_plot_info(plot_name)
            if not plot_info:
                raise ValueError(f"Plot '{plot_name}' not found")

            plot_id = plot_info["id"]
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM satellite_history
                WHERE plot_id = ? AND check_date >= ?
                ORDER BY check_date DESC
                """,
                (plot_id, cutoff_date),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def save_satellite_reading(
        self,
        plot_id: int,
        date: str,
        source: str,
        ndvi: float,
        cloud_cover: float,
        health_score: float,
        image_url: Optional[str] = None,
    ) -> Optional[int]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO satellite_history (
                    plot_id, check_date, satellite_source, ndvi_value,
                    cloud_cover_percent, health_score, image_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (plot_id, date, source, ndvi, cloud_cover, health_score, image_url),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def delete_plot(self, plot_name: str) -> bool:
        conn = None
        try:
            plot_info = self.get_plot_info(plot_name)
            if not plot_info:
                return False

            plot_id = plot_info["id"]
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM satellite_history WHERE plot_id = ?", (plot_id,))
            cursor.execute("DELETE FROM irrigation_log WHERE plot_id = ?", (plot_id,))
            cursor.execute("DELETE FROM plots WHERE id = ?", (plot_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_satellite_reading_count(self, plot_name: str) -> int:
        conn = None
        try:
            plot_info = self.get_plot_info(plot_name)
            if not plot_info:
                return 0
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM satellite_history WHERE plot_id = ?",
                (plot_info["id"],),
            )
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    # ── satellite notification tracking ──────────────────────────────────

    def has_sent_notification_for_date(self, plot_id: int, satellite_date: str) -> bool:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM satellite_notifications "
                "WHERE plot_id = ? AND satellite_date = ?",
                (plot_id, satellite_date),
            )
            return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def record_satellite_notification(
        self, plot_id: int, satellite_date: str, satellite_name: str, ndvi: float,
    ) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR REPLACE INTO satellite_notifications "
                "(plot_id, satellite_date, satellite_name, ndvi) "
                "VALUES (?, ?, ?, ?)",
                (plot_id, satellite_date, satellite_name, ndvi),
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
        finally:
            if conn:
                conn.close()

    def get_last_satellite_notification(self, plot_id: int) -> Optional[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT satellite_date, satellite_name, ndvi, sent_at "
                "FROM satellite_notifications "
                "WHERE plot_id = ? ORDER BY sent_at DESC LIMIT 1",
                (plot_id,),
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"[ERROR] Database error: {e}")
            return None
        finally:
            if conn:
                conn.close()
