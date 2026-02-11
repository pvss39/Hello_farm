from typing import TypedDict, List, Optional
from datetime import datetime
import os
import json
import re
from dotenv import load_dotenv

from src.database import FarmDatabase
from src.translation import LanguageManager
from src.weather import WeatherService
from src.satellite import SatelliteMonitor
from src.visualization import GraphGenerator
from src.whatsapp import WhatsAppService
from src.local_llm import OllamaLLM, OllamaIntegration
from src.llm_manager import create_local_llm
from src.multi_agent_system import AgentCoordinator
from src.uncertainty_handler import UncertaintyHandler

load_dotenv()


class AgentState(TypedDict):
    messages: List
    user_input: str
    detected_language: str
    plot_name: str
    action: str
    response_english: str
    response_telugu: str
    final_response: str


class FarmAgent:

    def __init__(self, database: FarmDatabase = None,
                 weather_service: WeatherService = None,
                 satellite_monitor: SatelliteMonitor = None,
                 use_ollama: bool = True):
        self.database = database or FarmDatabase()
        self.weather = weather_service or WeatherService()
        self.satellite = satellite_monitor or SatelliteMonitor()
        self.translator = LanguageManager()
        self.visualizer = GraphGenerator()
        self.whatsapp = WhatsAppService()

        self.ollama: Optional[OllamaLLM] = None
        if use_ollama:
            self.ollama = OllamaIntegration.get_or_init_ollama()
            if self.ollama:
                print("✅ Ollama LLM initialized (llama3.2:3b)")
            else:
                print("ℹ️  Ollama not available - using rule-based detection")

        self.log_irrigation_keywords = [
            "watered", "irrigated", "నీరు పోశాను", "పారుదల",
            "నీరు", "పోయాను", "పోసాను"
        ]
        self.check_plot_keywords = [
            "status", "check", "show", "చూపించు", "స్థితి",
            "ఎలా", "చెప్పు", "తెలుపు"
        ]
        self.satellite_keywords = [
            "satellite", "health", "report", "ఆరోగ్యం",
            "రిపోర్ట్", "చిత్రం", "చూపించు"
        ]
        self.check_due_keywords = [
            "due", "need water", "ready", "నీరు కావాలా",
            "అవసరమా", "ఏ", "ఎ"
        ]
        self.help_keywords = ["help", "commands", "సహాయం", "ఆదేశ"]

        self.uncertainty_handler = UncertaintyHandler()

    def detect_language(self, state: AgentState) -> AgentState:
        detected = self.translator.detect_language(state['user_input'])
        state['detected_language'] = detected
        return state

    def understand_intent(self, state: AgentState) -> AgentState:
        user_input = state['user_input']

        try:
            llm = create_local_llm()

            system_prompt = """You are an AI assistant for Telugu farmers. Analyze the farmer's message and identify their intent.

Available intents:
- log_irrigation: Farmer says they watered a plot
- check_plot: Farmer wants plot status/info
- satellite_report: Farmer wants satellite health data
- check_due: Farmer asks which plots need water
- answer: Farmer responding to agent's question (format: answer <id> <number>)
- help: Farmer needs help/commands

Also extract:
- plot_name (if mentioned): thurpu, athota, munnagi, or unknown
- detected_language: english, telugu, or mixed

Respond ONLY with valid JSON (no explanation):
{
  "action": "log_irrigation",
  "plot_name": "thurpu",
  "detected_language": "telugu",
  "confidence": 0.95
}"""

            prompt = f'Farmer\'s message: "{user_input}"'
            llm_response = llm.query(prompt, system_prompt, temperature=0.1)

            try:
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    state["action"] = result.get("action", "help")
                    detected_plot = result.get("plot_name", "").lower()
                    state["detected_language"] = result.get("detected_language", "english")
                    print(f"🤖 LLM detected: {result}")

                    plot_mapping = {
                        'thurpu': 'Thurpu Polam',
                        'athota': 'Athota Road Polam',
                        'munnagi': 'Munnagi Road Polam'
                    }
                    if detected_plot in plot_mapping:
                        state['plot_name'] = plot_mapping[detected_plot]
                else:
                    state["action"] = self._fallback_intent_detection(user_input)
                    print("⚠️ LLM response not JSON, using fallback")
            except Exception as e:
                print(f"⚠️ LLM parsing failed: {e}, using fallback")
                state["action"] = self._fallback_intent_detection(user_input)

        except Exception as e:
            print(f"⚠️ LLM initialization failed: {e}, using fallback")
            state["action"] = self._fallback_intent_detection(user_input)

        return state

    def _fallback_intent_detection(self, user_input: str) -> str:
        user_input_lower = user_input.lower()

        if user_input_lower.startswith("answer"):
            return "answer"
        elif any(word in user_input_lower for word in ["watered", "irrigated", "నీరు పోశాను", "పారుదల", "నీరు", "పోయాను", "పోసాను"]):
            return "log_irrigation"
        elif any(word in user_input_lower for word in ["status", "check", "show", "చూపించు", "స్థితి", "ఎలా", "చెప్పు", "తెలుపు"]):
            return "check_plot"
        elif any(word in user_input_lower for word in ["satellite", "health", "report", "ఆరోగ్యం", "రిపోర్ట్", "చిత్రం", "చూపించు"]):
            return "satellite_report"
        elif any(word in user_input_lower for word in ["due", "need water", "ready", "నీరు కావాలా", "అవసరమా", "ఏ", "ఎ"]):
            return "check_due"
        elif any(word in user_input_lower for word in ["help", "commands", "సహాయం", "ఆదేశ"]):
            return "help"
        else:
            return "help"

    def execute_action(self, state: AgentState) -> AgentState:
        action = state['action']

        if action == 'log_irrigation':
            state = self._log_irrigation(state)
        elif action == 'check_plot':
            state = self._check_plot(state)
        elif action == 'satellite_report':
            state = self._satellite_report(state)
        elif action == 'check_due':
            state = self._check_due(state)
        elif action == 'answer':
            state = self._answer_question(state)
        else:
            state = self._help(state)

        return state

    def _log_irrigation(self, state: AgentState) -> AgentState:
        try:
            plot_name = state.get('plot_name', '')

            if not plot_name:
                state['response_english'] = "❌ Please specify which plot (Thurpu/Athota/Munnagi)"
                return state

            self.database.log_irrigation(plot_name)
            plot_info = self.database.get_plot_info(plot_name)

            if plot_info:
                next_due = plot_info['irrigation_frequency_days']
                response = (
                    f"✅ Irrigation logged successfully\n\n"
                    f"Plot: {plot_info['name']}\n"
                    f"Crop: {plot_info['crop_type']}\n"
                    f"Size: {plot_info['size_acres']} acres\n"
                    f"Watered: {datetime.now().strftime('%Y-%m-%d')}\n"
                    f"Next irrigation due: In {next_due} days"
                )
            else:
                response = "✅ Irrigation logged, but plot info not found"

            state['response_english'] = response
        except Exception as e:
            state['response_english'] = f"❌ Error logging irrigation: {e}"

        return state

    def _check_plot(self, state: AgentState) -> AgentState:
        try:
            plot_name = state.get('plot_name', '')

            if not plot_name:
                state['response_english'] = "❌ Please specify which plot"
                return state

            plot_info = self.database.get_plot_info(plot_name)

            if plot_info:
                response = (
                    f"📊 Plot Status: {plot_info['name']}\n\n"
                    f"Crop: {plot_info['crop_type']}\n"
                    f"Size: {plot_info['size_acres']} acres\n"
                    f"Last irrigated: {plot_info['last_irrigated'] or 'Never'}\n"
                    f"Irrigation frequency: Every {plot_info['irrigation_frequency_days']} days\n"
                    f"Notes: {plot_info['notes'] or 'None'}"
                )
            else:
                response = f"❌ Plot '{plot_name}' not found"

            state['response_english'] = response
        except Exception as e:
            state['response_english'] = f"❌ Error checking plot: {e}"

        return state

    def _satellite_report(self, state: AgentState) -> AgentState:
        try:
            plot_name = state.get('plot_name', '')

            if not plot_name:
                state['response_english'] = "❌ Please specify which plot"
                return state

            plot_info = self.database.get_plot_info(plot_name)

            if not plot_info:
                state['response_english'] = f"❌ Plot '{plot_name}' not found"
                return state

            satellite_data = self.satellite.monitor_plot(plot_info)

            weather = self.weather.get_current_weather(
                plot_info['center_latitude'],
                plot_info['center_longitude']
            )

            forecast = self.weather.get_forecast_3day(
                plot_info['center_latitude'],
                plot_info['center_longitude']
            ) if hasattr(self.weather, 'get_forecast_3day') else []

            historical_ndvi_records = self.database.get_satellite_history(plot_name, days=30) \
                if hasattr(self.database, 'get_satellite_history') else []
            historical_ndvi = [h['ndvi_value'] for h in historical_ndvi_records if h.get('ndvi_value')]

            last_irrigation = self.database.get_last_irrigation(plot_name) \
                if hasattr(self.database, 'get_last_irrigation') else None
            days_since = (datetime.now() - last_irrigation).days if last_irrigation else 0

            coordinator = AgentCoordinator()
            analysis = coordinator.analyze_plot_comprehensive(
                plot_data=plot_info,
                satellite_data=satellite_data,
                weather_data=weather,
                forecast_data=forecast,
                historical_ndvi=historical_ndvi if historical_ndvi else [satellite_data.get('ndvi', 0)],
                days_since_irrigation=days_since,
                farmer_language="telugu"
            )

            is_uncertain = self.uncertainty_handler.check_if_uncertain(analysis)

            if is_uncertain:
                question = self.uncertainty_handler.generate_clarification_question(
                    analysis,
                    plot_info['name_english'],
                    language="telugu"
                )

                options_text = '\n'.join(
                    f"{i+1}. {opt}"
                    for i, opt in enumerate(question['options'])
                )

                response_english = f"""🤔 I need your help to understand better

{question['question_english']}

---

🤔 మీ సహాయం కావాలి

{question['question_telugu']}

Please choose:
{options_text}

(Type: answer {question['question_id']} <number>)"""

                state['response_english'] = response_english
                state['pending_question_id'] = question['question_id']
                return state

            graph_path = self.visualizer.create_health_trend_graph(
                plot_info.get('name_english', plot_info['name']),
                plot_info.get('name_telugu', '')
            )

            response = (
                f"🌾 {plot_info['name_english']} - Multi-Agent Analysis\n\n"
                f"📊 Plant Health: {satellite_data['health_score']}/100\n"
                f"📈 NDVI: {satellite_data['ndvi']:.3f}\n"
                f"☁️ Cloud Cover: {satellite_data['cloud_cover']}%\n\n"
                f"{analysis['technical_report']}\n"
                f"💬 Farmer Guidance:\n{analysis['farmer_message']}"
            )

            if graph_path:
                response += f"\n\n📸 Trend Graph: {graph_path}"

            state['response_english'] = response
        except Exception as e:
            state['response_english'] = f"❌ Error generating satellite report: {e}"

        return state

    def _check_due(self, state: AgentState) -> AgentState:
        try:
            due_plots = self.database.check_irrigation_needed()

            if not due_plots:
                state['response_english'] = "✅ All plots are up to date with irrigation"
                return state

            response = "💧 Plots needing irrigation:\n\n"
            for plot in due_plots:
                response += f"• {plot['name']} ({plot['crop']})\n"
                response += f"  {plot['days_overdue']} days overdue\n"
                response += f"  Last watered: {plot['last_irrigated']}\n\n"

            state['response_english'] = response
        except Exception as e:
            state['response_english'] = f"❌ Error checking due plots: {e}"

        return state

    def _answer_question(self, state: AgentState) -> AgentState:
        """Handle farmer's answer to an uncertainty question (format: answer <id> <number>)."""
        try:
            parts = state["user_input"].split()

            if len(parts) < 3:
                state["response_english"] = "❌ Format: answer <question_id> <option_number>\n\nExample: answer d39f13b7 2"
                return state

            question_id = parts[1]
            try:
                answer_num = int(parts[2]) - 1
            except ValueError:
                state["response_english"] = "❌ Option number must be a number\n\nExample: answer d39f13b7 2"
                return state

            if question_id not in self.uncertainty_handler.pending_questions:
                state["response_english"] = "❌ Question ID not found or expired\n\nPlease get a new satellite report to answer"
                return state

            context = self.uncertainty_handler.pending_questions[question_id]
            temp_question = self.uncertainty_handler.generate_clarification_question(
                context['analysis'],
                context['plot_name'],
                'telugu'
            )

            if 0 <= answer_num < len(temp_question['options']):
                farmer_answer = temp_question['options'][answer_num]
                result = self.uncertainty_handler.process_farmer_response(question_id, farmer_answer)

                diagnosis_display = result.get('updated_diagnosis', 'unknown').replace('_', ' ').title()

                state["response_english"] = f"""✅ Thank you! I learned from your answer.

Updated diagnosis: {diagnosis_display}
Confidence now: {int(result.get('confidence_now', 0.5) * 100)}%

What I learned: {result.get('what_we_learned', 'N/A')}

---

✅ ధన్యవాదాలు! మీ సమాధానం నుండి నేర్చుకున్నాను.

నవీకరించబడిన నిర్ధారణ: {diagnosis_display}
నమ్మకం ఇప్పుడు: {int(result.get('confidence_now', 0.5) * 100)}%

నేను నేర్చుకున్నది: {result.get('what_we_learned', 'తెలియదు')}"""
            else:
                state["response_english"] = f"❌ Invalid option number. Please choose 1-{len(temp_question['options'])}\n\nExample: answer {question_id} 1"

        except Exception as e:
            state["response_english"] = f"❌ Error processing answer: {e}"

        return state

    def _help(self, state: AgentState) -> AgentState:
        state['response_english'] = (
            "ℹ️ Available Commands:\n\n"
            "1️⃣ Log Irrigation:\n"
            "   'I watered [plot]' or 'నీరు పోశాను [plot]'\n\n"
            "2️⃣ Check Plot Status:\n"
            "   'Show [plot] status' or '[plot] చూపించు'\n\n"
            "3️⃣ Satellite Report:\n"
            "   '[plot] satellite report' or 'ఆరోగ్యం [plot]'\n\n"
            "4️⃣ Check Due Plots:\n"
            "   'What plots need water?' or 'నీరు కావాలా?'\n\n"
            "5️⃣ Help:\n"
            "   'help' or 'సహాయం'"
        )
        return state

    def translate_response(self, state: AgentState) -> AgentState:
        try:
            english = state['response_english']

            if self.ollama:
                telugu = self.ollama.translate_enhanced(english, target_language="telugu")
                if telugu:
                    state['response_telugu'] = telugu
                    return state

            telugu = self.translator.translate_en_to_te(english)
            state['response_telugu'] = telugu
        except Exception as e:
            print(f"⚠️ Translation error: {e}")
            state['response_telugu'] = state['response_english']

        return state

    def generate_response(self, state: AgentState) -> AgentState:
        try:
            final = f"{state['response_english']}\n\n---\n\n{state['response_telugu']}"
            state['final_response'] = final
        except Exception as e:
            print(f"⚠️ Response generation error: {e}")
            state['final_response'] = state['response_english']

        return state

    def process_message(self, user_input: str) -> str:
        state: AgentState = {
            'messages': [],
            'user_input': user_input,
            'detected_language': '',
            'plot_name': '',
            'action': '',
            'response_english': '',
            'response_telugu': '',
            'final_response': ''
        }

        state = self.detect_language(state)
        state = self.understand_intent(state)
        state = self.execute_action(state)
        state = self.translate_response(state)
        state = self.generate_response(state)

        return state['final_response']
