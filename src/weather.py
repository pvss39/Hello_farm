import os
from datetime import datetime
from typing import Dict, List, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()


class WeatherService:

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.last_weather_cache = {}

    def get_current_weather(self, lat: float, lon: float) -> Dict:
        try:
            url = f"{self.base_url}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            weather = {
                'temp_celsius': data['main']['temp'],
                'humidity_percent': data['main']['humidity'],
                'rainfall_mm': data.get('rain', {}).get('1h', 0),
                'conditions': data['weather'][0]['main'],
                'description': data['weather'][0]['description'],
                'timestamp': datetime.now().isoformat()
            }

            self.last_weather_cache[f"{lat},{lon}"] = weather
            return weather

        except Exception as e:
            print(f"⚠️ Weather API error: {e}")
            cached = self.last_weather_cache.get(f"{lat},{lon}")
            if cached:
                return cached
            return {
                'temp_celsius': 30,
                'humidity_percent': 60,
                'rainfall_mm': 0,
                'conditions': 'Unknown',
                'description': 'Unable to fetch weather data'
            }

    def get_forecast_3day(self, lat: float, lon: float) -> List[Dict]:
        try:
            url = f"{self.base_url}/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            forecast = []
            processed_dates = set()

            for item in data['list']:
                date = item['dt_txt'].split()[0]
                if date not in processed_dates and len(forecast) < 3:
                    processed_dates.add(date)
                    forecast.append({
                        'date': date,
                        'temp_high': item['main']['temp_max'],
                        'temp_low': item['main']['temp_min'],
                        'rainfall_mm': item.get('rain', {}).get('3h', 0),
                        'conditions': item['weather'][0]['main'],
                        'humidity_percent': item['main']['humidity']
                    })

            return forecast[:3]

        except Exception as e:
            print(f"⚠️ Forecast API error: {e}")
            return []

    def should_irrigate_today(self, plot_data: Dict, weather: Dict) -> Tuple[bool, str]:
        """Skip irrigation if rain > 5mm expected."""
        try:
            rainfall = weather.get('rainfall_mm', 0)
            if rainfall > 5:
                return (False, f"Rain expected: {rainfall}mm. Skip irrigation.")
            return (True, "Weather suitable for irrigation.")
        except Exception as e:
            print(f"⚠️ Irrigation decision error: {e}")
            return (True, "Unable to determine. Proceed with caution.")

    def format_weather_english(self, weather_data: Dict) -> str:
        try:
            temp = weather_data.get('temp_celsius', 'N/A')
            humidity = weather_data.get('humidity_percent', 'N/A')
            rainfall = weather_data.get('rainfall_mm', 0)
            conditions = weather_data.get('description', 'Unknown conditions')

            message = f"☀️ Weather: {conditions.title()}\n"
            message += f"🌡️ Temperature: {temp}°C\n"
            message += f"💧 Humidity: {humidity}%"
            if rainfall > 0:
                message += f"\n🌧️ Rainfall: {rainfall}mm"
            return message
        except Exception as e:
            print(f"⚠️ Format error: {e}")
            return "Weather data unavailable"

    def format_weather_telugu(self, weather_data: Dict) -> str:
        try:
            temp = weather_data.get('temp_celsius', 'N/A')
            humidity = weather_data.get('humidity_percent', 'N/A')
            rainfall = weather_data.get('rainfall_mm', 0)
            conditions = weather_data.get('description', 'తెలియని పరిస్థితి')

            conditions_te = {
                'clear': '맑음',
                'sunny': 'ఎండ',
                'cloudy': 'మేఘాలు',
                'rainy': 'వర్షం',
                'partly': 'పాక్షిక'
            }

            cond_te = conditions_te.get(conditions.lower(), conditions)
            message = f"☀️ వాతావరణం: {cond_te}\n"
            message += f"🌡️ ఉష్ణోగ్రత: {temp}°C\n"
            message += f"💧 ఆర్ద్రత: {humidity}%"
            if rainfall > 0:
                message += f"\n🌧️ వర్షం: {rainfall}mm"
            return message
        except Exception as e:
            print(f"⚠️ Format error: {e}")
            return "వాతావరణ డేటా అందుబాటులో లేదు"
