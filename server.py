from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pytz
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.database import FarmDatabase
from src.satellite_multi import MultiSatelliteManager
from src.visualization import GraphGenerator
from src.weather import WeatherService
from src.whatsapp import WhatsAppService

print("Initialising Hello Farm Push Server...")

db        = FarmDatabase()
db.init_database()

multi_sat = MultiSatelliteManager()
graphs    = GraphGenerator()
weather   = WeatherService()
whatsapp  = WhatsAppService()

IST = pytz.timezone("Asia/Kolkata")

# Recipients — father + observer
RECIPIENTS: List[str] = [
    r for r in [
        os.getenv("FATHER_WHATSAPP", ""),
        os.getenv("OBSERVER_WHATSAPP", ""),
    ]
    if r.strip()
]

app = FastAPI(
    title="Hello Farm Push Server",
    description="Automated WhatsApp crop-monitoring notifications",
    version="1.0.0",
)


@app.get("/")
async def health_check() -> Dict:
    return {
        "status":        "ok",
        "service":       "Hello Farm Push Server",
        "gee":           multi_sat.initialized,
        "whatsapp_mode": whatsapp.mode,
        "recipients":    len(RECIPIENTS),
        "time_ist":      datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
    }


@app.get("/trigger/morning")
async def trigger_morning() -> Dict:
    send_morning_update()
    return {"status": "triggered", "job": "morning_update"}


@app.get("/trigger/satellite")
async def trigger_satellite() -> Dict:
    check_satellite_updates()
    return {"status": "triggered", "job": "satellite_check"}


@app.get("/trigger/weekly")
async def trigger_weekly() -> Dict:
    send_weekly_summary()
    return {"status": "triggered", "job": "weekly_summary"}


def send_morning_update() -> None:
    print(f"\n{'='*60}")
    print(f"MORNING UPDATE  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    try:
        plots = db.get_all_plots()
        if not plots:
            print("No plots in database — skipping")
            return

        te = "శుభోదయం! 🌅\n\n"
        en = "Good morning! 🌅\n\n"

        # Irrigation check
        due = db.check_irrigation_needed()
        if due:
            te += "💧 ఈరోజు నీరు పోయాల్సిన పొలాలు:\n"
            en += "💧 Plots needing water today:\n"
            for p in due:
                te += f"  • {_telugu_name(plots, p['name'])} "
                te += f"({p['days_overdue']}d overdue)\n"
                en += f"  • {p['name']} — {p['days_overdue']} days overdue\n"
        else:
            te += "✅ అన్ని పొలాలు బాగున్నాయి\n"
            en += "✅ All plots are on schedule\n"

        te += "\n"
        en += "\n"

        # Weather for first plot
        try:
            p0 = plots[0]
            w  = weather.get_current_weather(
                p0["center_latitude"], p0["center_longitude"]
            )
            rain = w.get("rainfall_mm", 0) or 0
            te += (f"☀️ వాతావరణం: {w.get('conditions','N/A')}, "
                   f"{w.get('temp_celsius','?')}°C\n")
            en += (f"☀️ Weather: {w.get('conditions','N/A')}, "
                   f"{w.get('temp_celsius','?')}°C\n")
            if rain > 0:
                te += f"🌧️ వర్షం: {rain}mm\n"
                en += f"🌧️ Rainfall: {rain}mm\n"
        except Exception as exc:
            print(f"  Weather fetch error: {exc}")

        message = te + "\n---\n\n" + en
        _broadcast(message)
        print("Morning update sent")

    except Exception as exc:
        print(f"Morning update failed: {exc}")


def check_satellite_updates() -> None:
    print(f"\n{'='*60}")
    print(f"SATELLITE CHECK  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    try:
        plots = db.get_all_plots()

        for plot in plots:
            print(f"\nChecking {plot['name_english']}…")

            sat = multi_sat.get_latest_ndvi(
                latitude=plot["center_latitude"],
                longitude=plot["center_longitude"],
                days_lookback=7,
            )

            if not sat:
                print("  No imagery found")
                continue

            already_sent = db.has_sent_notification_for_date(
                plot["id"], sat["date"]
            )
            if already_sent:
                print(f"  Already notified for {sat['date']}")
                continue

            # New data — build and send notification
            print(f"  New data from {sat['satellite']} ({sat['date']})")
            _send_satellite_notification(plot, sat)

    except Exception as exc:
        print(f"Satellite check failed: {exc}")


def _send_satellite_notification(plot: Dict, sat: Dict) -> None:
    try:
        ndvi         = sat["ndvi"]
        health_score = _ndvi_to_health(ndvi)

        # Trend comparison
        history = db.get_satellite_history(plot["name_english"], days=30)
        trend_te, trend_en, trend_emoji = _compute_trend(ndvi, history)

        # Generate graph (passes telugu name as required by GraphGenerator)
        graph_path: Optional[str] = None
        try:
            graph_path = graphs.create_health_trend_graph(
                plot_name=plot["name_english"],
                plot_name_te=plot.get("name_telugu", ""),
                ndvi_history=_history_to_graph_format(history),
                days=30,
            )
        except Exception as exc:
            print(f"  Graph generation error: {exc}")

        message = (
            f"🛰️ {sat['satellite']} నివేదిక\n\n"
            f"{plot['name_telugu']}:\n"
            f"{trend_emoji} ఆరోగ్యం: {health_score}/100 ({trend_te})\n"
            f"📸 NDVI: {ndvi:.3f}\n"
            f"📅 తేదీ: {sat['date']} ({sat['age_days']} రోజుల క్రితం)\n"
            f"☁️ మేఘాలు: {sat['cloud_cover']:.0f}%\n\n"
            f"---\n\n"
            f"🛰️ {sat['satellite']} Report\n\n"
            f"{plot['name_english']}:\n"
            f"{trend_emoji} Health: {health_score}/100 ({trend_en})\n"
            f"📸 NDVI: {ndvi:.3f}\n"
            f"📅 Date: {sat['date']} ({sat['age_days']} days ago)\n"
            f"☁️ Clouds: {sat['cloud_cover']:.0f}%"
        )

        _broadcast(message, graph_path)

        # Save reading to satellite_history
        db.save_satellite_reading(
            plot_id=plot["id"],
            date=sat["date"],
            source=sat["satellite"],
            ndvi=ndvi,
            cloud_cover=sat["cloud_cover"],
            health_score=float(health_score),
        )

        # Mark notification as sent (prevents re-sending)
        db.record_satellite_notification(
            plot_id=plot["id"],
            satellite_date=sat["date"],
            satellite_name=sat["satellite"],
            ndvi=ndvi,
        )

        print(f"  Notification sent for {plot['name_english']}")

    except Exception as exc:
        print(f"  Notification send failed: {exc}")


def send_weekly_summary() -> None:
    print(f"\n{'='*60}")
    print(f"WEEKLY SUMMARY  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    try:
        plots = db.get_all_plots()
        if not plots:
            print("No plots — skipping weekly summary")
            return

        te = "📊 వారపు సారాంశం 📊\n\n"
        en = "📊 Weekly Summary 📊\n\n"

        for plot in plots:
            history = db.get_satellite_history(plot["name_english"], days=7)

            if len(history) >= 2:
                old_ndvi   = history[-1].get("ndvi_value", 0.5)
                new_ndvi   = history[0].get("ndvi_value", 0.5)
                _, trend_en, emoji = _compute_trend(new_ndvi,
                                                    history[1:])
                te += f"{emoji} {plot['name_telugu']}: {trend_en}\n"
                en += f"{emoji} {plot['name_english']}: {trend_en}\n"
            else:
                te += f"📊 {plot['name_telugu']}: పోలిక లేదు\n"
                en += f"📊 {plot['name_english']}: not enough data yet\n"

        message = te + "\n---\n\n" + en
        _broadcast(message)
        print("Weekly summary sent")

    except Exception as exc:
        print(f"Weekly summary failed: {exc}")


def _broadcast(message: str, image_path: Optional[str] = None) -> None:
    if not RECIPIENTS:
        print("  No recipients configured — printing to console")
        whatsapp._send_mock("console", message, image_path)
        return

    results = whatsapp.send_to_multiple(message, RECIPIENTS, image_path)
    for r in results:
        print(f"  → {r.get('number','?')}: {r.get('status','?')}")


def _ndvi_to_health(ndvi: float) -> int:
    return min(100, max(0, int((ndvi + 0.2) * 100)))


def _compute_trend(
    current_ndvi: float,
    history: List[Dict],
) -> tuple[str, str, str]:
    if len(history) < 1:
        return "తనిఖీ చేయబడింది", "checked", "📊"

    prev = history[0].get("ndvi_value", current_ndvi)
    delta = current_ndvi - prev

    if delta > 0.05:
        return "మెరుగుపడింది", "improving", "📈"
    elif delta < -0.05:
        return "తగ్గింది",      "declining", "📉"
    else:
        return "స్థిరంగా ఉంది", "stable",    "➡️"


def _telugu_name(plots: List[Dict], english_name: str) -> str:
    for p in plots:
        if p.get("name_english", "") == english_name:
            return p.get("name_telugu", english_name)
    return english_name


def _history_to_graph_format(history: List[Dict]) -> List[Dict]:
    result = []
    for row in reversed(history):  # oldest first
        result.append({
            "date":         row.get("check_date", ""),
            "ndvi":         row.get("ndvi_value", 0.5),
            "health_score": row.get("health_score", 50),
        })
    return result


scheduler = BackgroundScheduler(timezone=IST)

scheduler.add_job(
    send_morning_update,
    CronTrigger(hour=7, minute=0, timezone=IST),
    id="daily_morning",
    name="Daily 7 AM morning update",
    replace_existing=True,
)

scheduler.add_job(
    check_satellite_updates,
    CronTrigger(hour="*/6", timezone=IST),
    id="satellite_check",
    name="Satellite check every 6 hours",
    replace_existing=True,
)

scheduler.add_job(
    send_weekly_summary,
    CronTrigger(day_of_week="sun", hour=8, minute=0, timezone=IST),
    id="weekly_summary",
    name="Sunday 8 AM weekly summary",
    replace_existing=True,
)


@app.on_event("startup")
async def startup() -> None:
    scheduler.start()
    print("\n" + "=" * 60)
    print("HELLO FARM PUSH SERVER STARTED")
    print("=" * 60)
    print(f"  GEE         : {'connected' if multi_sat.initialized else 'fallback mode'}")
    print(f"  WhatsApp    : {whatsapp.mode}")
    print(f"  Recipients  : {len(RECIPIENTS)} ({', '.join(RECIPIENTS) or 'none'})")
    print(f"  Schedules   :")
    print(f"    - Daily update  : 7:00 AM IST")
    print(f"    - Satellite check: every 6 hours")
    print(f"    - Weekly summary : Sundays 8:00 AM IST")
    print(f"  Endpoints   :")
    print(f"    GET /                  health check")
    print(f"    GET /trigger/morning   manual morning send")
    print(f"    GET /trigger/satellite manual satellite check")
    print(f"    GET /trigger/weekly    manual weekly send")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler.shutdown()
    print("Push server stopped")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
