"""
Satellite Intelligence Analysis using LLM

Intelligent NDVI interpretation acting like an expert agronomist.
"""

from typing import Dict, List
from src.llm_manager import create_local_llm, create_cloud_llm
import json
import re


class SatelliteAnalyzer:
    """Intelligent satellite data analyzer using LLM expertise."""
    
    def __init__(self, use_cloud: bool = False):
        """
        Initialize analyzer with LLM backend.
        
        Args:
            use_cloud: If True, use Cloud LLM API. If False, use Ollama (default)
            
        Example:
            analyzer = SatelliteAnalyzer(use_cloud=False)  # Local Ollama
            analyzer = SatelliteAnalyzer(use_cloud=True)   # Cloud LLM API
        """
        if use_cloud:
            self.llm = create_cloud_llm()
            self.mode = "cloud"
        else:
            self.llm = create_local_llm()
            self.mode = "local"
        
        print(f"🌾 SatelliteAnalyzer initialized in {self.mode.upper()} mode")
    
    def analyze_health(
        self, 
        plot_name: str, 
        current_ndvi: float, 
        historical_ndvi: List[float], 
        weather_data: Dict, 
        days_since_irrigation: int
    ) -> Dict:
        """
        Analyze satellite data with LLM intelligence.
        
        Args:
            plot_name: Name of the plot
            current_ndvi: Current NDVI value (0.0-1.0)
            historical_ndvi: List of recent NDVI values
            weather_data: Dictionary with weather info (temp_celsius, rainfall_mm_today)
            days_since_irrigation: Days since last irrigation
            
        Returns:
            {
                "health_assessment": "one-sentence summary",
                "concerns": ["concern1", "concern2"],
                "recommendations": ["action1", "action2"],
                "confidence": 0.85
            }
            
        Example:
            result = analyzer.analyze_health(
                plot_name="Thurpu Polam",
                current_ndvi=0.65,
                historical_ndvi=[0.60, 0.62, 0.64, 0.65],
                weather_data={"temp_celsius": 32, "rainfall_mm_today": 0},
                days_since_irrigation=5
            )
        """
        try:
            # Calculate trend
            if len(historical_ndvi) >= 3:
                recent_avg = sum(historical_ndvi[-3:]) / 3
                if current_ndvi > recent_avg:
                    trend = "improving"
                elif current_ndvi < recent_avg - 0.1:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient data"
            
            # System prompt for agronomist expertise
            system_prompt = """You are an expert agronomist analyzing satellite data for Jowar (sorghum) in India.

Your task: Analyze NDVI (vegetation health) data and provide actionable insights.

NDVI meanings:
- 0.0-0.2: Bare soil or severe stress
- 0.2-0.4: Sparse vegetation or moderate stress
- 0.4-0.6: Moderate vegetation health
- 0.6-0.8: Healthy, dense vegetation
- 0.8+: Very healthy (peak growth)

Consider:
- Seasonal patterns for Jowar in Emani Duggirala, AP
- Water stress indicators
- Pest and disease risks
- Optimal harvest timing

Respond ONLY with valid JSON:
{
  "health_assessment": "one-sentence summary",
  "concerns": ["concern 1", "concern 2"],
  "recommendations": ["action 1", "action 2"],
  "confidence": 0.85
}"""
            
            # User prompt with data
            user_prompt = f"""Plot: {plot_name}
Current NDVI: {current_ndvi:.3f}
Historical NDVI (last 7): {[round(x, 3) for x in historical_ndvi[-7:]]}
Trend: {trend}
Days since last irrigation: {days_since_irrigation}
Temperature: {weather_data.get('temp_celsius', 'unknown')}°C
Rainfall (last 24h): {weather_data.get('rainfall_mm_today', 0)}mm

Analyze the situation and provide your expert assessment."""
            
            # Query LLM with temperature 0.2 (focused analysis)
            llm_response = self.llm.query(
                user_prompt, 
                system_prompt, 
                temperature=0.2
            )
            
            # Parse JSON response
            try:
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    print(f"🤖 LLM Analysis: {result['health_assessment']}")
                    return result
                else:
                    print(f"⚠️ LLM response not JSON format, using rule-based fallback")
                    return self._create_rule_based_analysis(
                        current_ndvi, trend, days_since_irrigation
                    )
            except Exception as e:
                print(f"⚠️ LLM parsing failed: {e}, using rule-based fallback")
                return self._create_rule_based_analysis(
                    current_ndvi, trend, days_since_irrigation
                )
        
        except Exception as e:
            print(f"⚠️ Analysis failed: {e}, using rule-based fallback")
            return self._create_rule_based_analysis(
                current_ndvi, trend, days_since_irrigation
            )
    
    def _create_rule_based_analysis(
        self, 
        ndvi: float, 
        trend: str, 
        days_since_irrigation: int
    ) -> Dict:
        """
        Fallback rule-based analysis when LLM unavailable.
        
        Args:
            ndvi: Current NDVI value
            trend: Trend direction (improving, stable, declining)
            days_since_irrigation: Days since irrigation
            
        Returns:
            Analysis dictionary with fallback values
        """
        if ndvi < 0.3:
            assessment = "Vegetation shows signs of stress - immediate attention needed"
            concerns = [
                "Low NDVI indicates possible water stress",
                "May require immediate irrigation"
            ]
            recommendations = [
                "Check irrigation system functionality",
                "Inspect for pest damage",
                "Schedule irrigation within 2 days"
            ]
        elif ndvi < 0.5:
            assessment = "Moderate vegetation health - monitoring recommended"
            concerns = [
                "Monitor closely for changes",
                f"Trend is {trend}"
            ]
            recommendations = [
                "Maintain current irrigation schedule",
                "Check soil moisture in 3-4 days",
                "Monitor weather forecast for rainfall"
            ]
        else:
            assessment = "Healthy vegetation detected - plants growing well"
            concerns = []
            recommendations = [
                "Continue current practices",
                "Monitor for any changes in vegetation",
                "Plan irrigation in 7-10 days if no rain"
            ]
        
        return {
            "health_assessment": assessment,
            "concerns": concerns,
            "recommendations": recommendations,
            "confidence": 0.7
        }
    
    def batch_analyze(
        self,
        plots_data: List[Dict]
    ) -> List[Dict]:
        """
        Analyze multiple plots at once.
        
        Args:
            plots_data: List of plot data dictionaries, each containing:
                - plot_name
                - current_ndvi
                - historical_ndvi
                - weather_data
                - days_since_irrigation
                
        Returns:
            List of analysis results
            
        Example:
            results = analyzer.batch_analyze([
                {
                    "plot_name": "Thurpu Polam",
                    "current_ndvi": 0.65,
                    "historical_ndvi": [0.60, 0.62, 0.64, 0.65],
                    "weather_data": {"temp_celsius": 32, "rainfall_mm_today": 0},
                    "days_since_irrigation": 5
                },
                ...
            ])
        """
        results = []
        for plot in plots_data:
            result = self.analyze_health(
                plot_name=plot["plot_name"],
                current_ndvi=plot["current_ndvi"],
                historical_ndvi=plot["historical_ndvi"],
                weather_data=plot["weather_data"],
                days_since_irrigation=plot["days_since_irrigation"]
            )
            results.append({
                "plot_name": plot["plot_name"],
                "analysis": result
            })
        
        return results
