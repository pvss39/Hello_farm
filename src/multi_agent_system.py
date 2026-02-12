"""
Agent Coordinator for Multi-Agent System

Orchestrates 4 specialized agents for comprehensive farm analysis.
"""

from typing import Dict, List
from src.agents.satellite_interpreter import SatelliteInterpreterAgent
from src.agents.weather_analyst import WeatherAnalystAgent
from src.agents.crop_health_diagnostic import CropHealthDiagnosticAgent
from src.agents.farmer_communication import FarmerCommunicationAgent


class AgentCoordinator:
    """Coordinates all specialized agents for comprehensive farm analysis."""
    
    def __init__(self):
        """Initialize the multi-agent system."""
        self.satellite_agent = SatelliteInterpreterAgent()
        self.weather_agent = WeatherAnalystAgent()
        self.diagnostic_agent = CropHealthDiagnosticAgent()
        self.communication_agent = FarmerCommunicationAgent()
        
        print("🤖 Multi-Agent System initialized:")
        print("   • Satellite Interpreter")
        print("   • Weather Analyst")
        print("   • Crop Health Diagnostic")
        print("   • Farmer Communication")
    
    def analyze_plot_comprehensive(
        self,
        plot_data: Dict,
        satellite_data: Dict,
        weather_data: Dict,
        forecast_data: List[Dict],
        historical_ndvi: List[float],
        days_since_irrigation: int,
        farmer_language: str = "telugu"
    ) -> Dict:
        """
        Coordinate all agents for comprehensive plot analysis.
        
        Args:
            plot_data: Plot info (name, crop_type_english, etc.)
            satellite_data: Dict with ndvi, cloud_cover
            weather_data: Current weather dict
            forecast_data: Weather forecast list
            historical_ndvi: List of recent NDVI values
            days_since_irrigation: Days since irrigation
            farmer_language: Language for farmer communication
            
        Returns:
            {
                "satellite_analysis": {...},
                "weather_analysis": {...},
                "health_diagnosis": {...},
                "farmer_message": "...",
                "technical_report": "..."
            }
        """
        print("\n🔄 Multi-Agent Analysis Starting...")
        
        # Step 1: Satellite Agent analyzes imagery
        print("   1️⃣ Satellite Interpreter analyzing...")
        satellite_analysis = self.satellite_agent.analyze(
            ndvi=satellite_data['ndvi'],
            cloud_cover=satellite_data['cloud_cover'],
            historical_data=historical_ndvi
        )
        print(f"      → {satellite_analysis.get('interpretation', 'N/A')}")
        
        # Step 2: Weather Agent analyzes conditions
        print("   2️⃣ Weather Analyst analyzing...")
        weather_analysis = self.weather_agent.analyze(
            current_weather=weather_data,
            forecast=forecast_data,
            days_since_irrigation=days_since_irrigation
        )
        print(f"      → {weather_analysis.get('recommendation', 'N/A')}")
        
        # Step 3: Diagnostic Agent combines findings
        print("   3️⃣ Crop Health Diagnostic analyzing...")
        health_diagnosis = self.diagnostic_agent.diagnose(
            satellite_analysis=satellite_analysis,
            weather_analysis=weather_analysis,
            crop_type=plot_data['crop_type_english']
        )
        print(f"      → {health_diagnosis.get('diagnosis', 'N/A')}")
        
        # Step 4: Communication Agent translates for farmer
        print("   4️⃣ Farmer Communication translating...")
        farmer_message = self.communication_agent.translate_to_farmer(
            satellite=satellite_analysis,
            weather=weather_analysis,
            diagnosis=health_diagnosis,
            farmer_language=farmer_language
        )
        print(f"      → Message generated in {farmer_language}")
        
        print("✅ Multi-Agent Analysis Complete\n")
        
        return {
            "satellite_analysis": satellite_analysis,
            "weather_analysis": weather_analysis,
            "health_diagnosis": health_diagnosis,
            "farmer_message": farmer_message,
            "technical_report": self._generate_technical_report(
                satellite_analysis, weather_analysis, health_diagnosis
            )
        }
    
    def _generate_technical_report(self, satellite: Dict, weather: Dict, diagnosis: Dict) -> str:
        """Generate detailed technical report."""
        report = f"""📋 TECHNICAL ANALYSIS REPORT

🛰️ SATELLITE INTERPRETATION:
   Finding: {satellite.get('interpretation', 'N/A')}
   Severity: {satellite.get('severity', 'N/A').upper()}
   Confidence: {int(satellite.get('confidence', 0) * 100)}%

☁️ WEATHER ANALYSIS:
   Recommendation: {weather.get('recommendation', 'N/A').replace('_', ' ').title()}
   Reasoning: {weather.get('reasoning', 'N/A')}
   Confidence: {int(weather.get('confidence', 0) * 100)}%

🌾 HEALTH DIAGNOSIS:
   Diagnosis: {diagnosis.get('diagnosis', 'N/A').replace('_', ' ').title()}
   Urgency: {diagnosis.get('urgency', 'N/A').upper()}
   Recommended Actions:
{chr(10).join(f"   • {action}" for action in diagnosis.get('recommended_actions', []))}
"""
        return report

