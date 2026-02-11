# Hello Farm | హెలో ఫార్మ్

**AI-Powered Crop Monitoring for Telugu Farmers**

An intelligent agricultural system that monitors 3 Jowar (sorghum) plots in Andhra using satellite imagery, weather data, and multi-agent AI - all in English and Telugu.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Edit .env with your Sentinel Hub and OpenWeather credentials

# 3. Initialize database (first time only)
python setup_plots.py

# 4. Launch the app
streamlit run app.py
```

## Features

- **Satellite Health Monitoring** - NDVI-based crop health scoring (0-100)
- **Weather-Aware Irrigation** - Recommendations based on 3-day forecasts
- **Dual Language** - Full English + Telugu support with auto-detection
- **Multi-Agent Analysis** - 4 specialized AI agents coordinate decisions
- **Uncertainty Handling** - Asks the farmer when confidence is low
- **Health Trend Graphs** - 30-day visual health tracking per plot
- **Local LLM Support** - Works with Ollama (llama3.2) for offline AI

## Architecture

```
User (Streamlit UI)
       |
  FarmAgent (LangGraph 5-node workflow)
       |
  detect_language -> understand_intent -> execute_action -> translate -> respond
       |                    |                   |
  LanguageManager     LLM/Keywords      [Database, Weather, Satellite, Viz]
                                               |
                                    Multi-Agent Coordinator
                                    (4 specialized agents)
```

## Project Structure

```
Hello_Farm/
├── app.py                  # Streamlit web UI (main entry point)
├── setup_plots.py          # Initialize database with 3 plots
├── requirements.txt        # Python dependencies
├── .env.example            # API key template
├── src/
│   ├── agent.py            # LangGraph orchestration engine
│   ├── database.py         # SQLite persistence layer
│   ├── translation.py      # English <-> Telugu translation
│   ├── weather.py          # OpenWeather API integration
│   ├── satellite.py        # NDVI calculation & health scoring
│   ├── visualization.py    # Matplotlib graph generation
│   ├── whatsapp.py         # WhatsApp messaging (Twilio-ready stub)
│   ├── ollama_llm.py       # Local Ollama LLM integration
│   ├── llm_manager.py      # Unified LLM interface (local/cloud)
│   ├── satellite_analyzer.py # LLM-powered satellite analysis
│   ├── multi_agent_system.py # 4-agent coordinator
│   ├── uncertainty_handler.py # Ask farmer when unsure
│   └── agents/             # Specialized agents
│       ├── satellite_interpreter.py
│       ├── weather_analyst.py
│       ├── crop_health_diagnostic.py
│       └── farmer_communication.py
├── data/
│   └── farm.db             # SQLite database
├── outputs/                # Generated graphs (auto-cleaned)
└── tests/                  # Test suite (8/8 passing)
```

## Farm Plots

| Plot | Telugu | Acres | Location |
|------|--------|-------|----------|
| Thurpu Polam | తూర్పు పొలం | 1.75 | Emani Duggirala, AP (update with actual GPS) |
| Athota Road Polam | ఆత్తోట రోడ్ పొలం | 1.0 | Emani Duggirala, AP (update with actual GPS) |
| Munnagi Road Polam | ముణగి రోడ్ పొలం | 0.8 | Emani Duggirala, AP (update with actual GPS) |

All plots: Jowar (జొన్న), 7-day irrigation cycle, Emani Duggirala Mandal, Andhra Pradesh

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| Agent Framework | LangGraph |
| Database | SQLite |
| Satellite Data | Sentinel-2 (mock for MVP) |
| Weather | OpenWeather API |
| Visualization | Matplotlib |
| LLM | Ollama (local) / Claude API (cloud) |
| Language | Python 3.10+ |

## NDVI Health Scoring

| NDVI Range | Health Score | Status |
|-----------|-------------|--------|
| 0.0 - 0.2 | 0 - 30 | Stress (needs attention) |
| 0.2 - 0.4 | 30 - 60 | Moderate (monitor closely) |
| 0.4 - 0.8 | 60 - 100 | Healthy (good growth) |

## Optional: Ollama Setup (Local AI)

```bash
# Install Ollama from https://ollama.com
ollama pull llama3.2:3b
ollama serve
```

The system auto-detects Ollama. If unavailable, it falls back to keyword-based detection.

## API Keys

| Service | Purpose | Get It |
|---------|---------|--------|
| OpenWeather | Weather + forecasts | [openweathermap.org/api](https://openweathermap.org/api) |
| Sentinel Hub | Satellite imagery | [sentinel-hub.com](https://www.sentinel-hub.com/) |
| Claude API | Cloud LLM (optional) | [console.anthropic.com](https://console.anthropic.com/) |

## Tests

```bash
python -m pytest tests/ -v
```

8/8 tests passing: Database, Language Detection, Translation, Weather, Satellite, Visualization, Intent Detection, Full Pipeline.

---

*రైతులకు AI శక్తి | Empowering farmers with AI*
