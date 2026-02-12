# Hello Farm | హెలో ఫార్మ్

**AI-Powered Crop Monitoring for  Farmers**

---

## Why This Exists

My father farms 3.5 acres of Jowar in our village, Andhra Pradesh. He makes every irrigation and pest decision with his eyes and memory — no data, no forecast, no external input.

He's good at it. But he's working with incomplete information every single day.

I built Hello Farm so satellite data, weather forecasts, and crop health scores reach him the only way they will — a WhatsApp message, in Telugu, every morning. No app to install. No dashboard. No learning curve.

This is an MVP. There's a long way to go.

---

## What It Does

Satellite imagery → NDVI crop health score → weather-aware irrigation recommendation → WhatsApp message in Telugu + English, every morning at 7AM. Alert within 6 hours if health drops.

---

## How I Used AI & Agents

A LangGraph 5-node workflow orchestrates 4 specialized agents (Satellite Interpreter, Weather Analyst, Crop Health Diagnostic, Farmer Communication) — each handling one domain, handing off to a coordinator that writes the final advisory in Telugu and English. Satellite selection is orbit-aware; uncertainty is flagged, not guessed.

---

## What You Receive

| When | What |
|------|------|
| 7:00 AM daily | Health score for all 3 plots + irrigation call |
| Every 6 hours | Satellite pass check — alert if NDVI drops |
| Sunday 8:00 AM | Week-in-review with trend |

All messages in Telugu + English. NDVI heatmap image attached when fresh data is available.

---

## Present and Future

**Right now:** My father uses this. One farmer. Three plots. The system works — messages arrive, NDVI is real, the advisory is crop-stage aware. But the satellite data is still partially mocked pending full GEE authentication, the GPS coordinates on two plots are estimates, and the AI advisory engine is rule-based, not model-trained. It's functional. It is not finished.

**The real problem this is pointing at:** Agriculture is at a demographic breaking point. The farmers who hold decades of field knowledge — soil feel, pest timing, rain patterns — are aging out. Their children are educated, often urban, and lack that embodied experience. Meanwhile global food demand keeps climbing and small farms (under 2 acres, which is most of Indian agriculture) still make decisions the way they did 30 years ago — by eye, by memory, by asking the neighbor.

Precision agriculture tools exist. They are built for large commercial farms in the US and Europe. They are not built for a 1.75-acre Jowar plot in Andhra Pradesh where the farmer reads Telugu and doesn't own a laptop.

Hello Farm is not solving that problem yet. It is one attempt at a much smaller version of it — make the data that already exists (Sentinel-2 is free, OpenWeather is free) actually reach the person who needs it, in the form they can use.

The gap between what's possible technically and what actually reaches farmers in India is enormous. This project is one step in that direction, with a lot more steps remaining.

---

## NDVI Health Reference

| NDVI | Score | Status |
|------|-------|--------|
| 0.0 – 0.2 | 0–30 | Stress — needs attention |
| 0.2 – 0.4 | 30–60 | Moderate — monitor closely |
| 0.4 – 0.8 | 60–100 | Healthy — good growth |
