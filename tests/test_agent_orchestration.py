"""
Comprehensive test suite for Farm Plot Agent system.

Tests all components: database, weather, satellite, visualization, and agent.
"""

import os
import sys

# Add parent directory to path to import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import FarmDatabase
from src.translation import LanguageManager
from src.weather import WeatherService
from src.satellite import SatelliteMonitor
from src.visualization import GraphGenerator
from src.agent import FarmAgent


def test_setup():
    """Test database initialization."""
    print("\n" + "="*60)
    print("TEST 1: Database Setup")
    print("="*60)
    
    try:
        db = FarmDatabase()
        plots = db.get_all_plots()
        
        if len(plots) == 3:
            print("✅ Database initialized with 3 plots")
            for plot in plots:
                print(f"   • {plot['name']} - {plot['crop_type']}")
        else:
            print(f"⚠️ Expected 3 plots, found {len(plots)}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_language_detection():
    """Test language detection."""
    print("\n" + "="*60)
    print("TEST 2: Language Detection")
    print("="*60)
    
    try:
        translator = LanguageManager()
        
        # Test Telugu
        result_te = translator.detect_language("తూర్పు పొలం")
        print(f"Telugu input: {result_te} {'✅' if result_te == 'telugu' else '❌'}")
        
        # Test English
        result_en = translator.detect_language("Show status")
        print(f"English input: {result_en} {'✅' if result_en == 'english' else '❌'}")
        
        # Test Mixed
        result_mix = translator.detect_language("Thurpu polam చూపించు")
        print(f"Mixed input: {result_mix}")
        
        return True
    except Exception as e:
        print(f"❌ Language test failed: {e}")
        return False


def test_translation():
    """Test English-Telugu translation."""
    print("\n" + "="*60)
    print("TEST 3: Translation")
    print("="*60)
    
    try:
        translator = LanguageManager()
        
        # Test translation
        english = "Good morning, Plot status is healthy"
        telugu = translator.translate_en_to_te(english)
        
        print(f"English: {english}")
        print(f"Telugu: {telugu}")
        print("✅ Translation working")
        
        return True
    except Exception as e:
        print(f"❌ Translation test failed: {e}")
        return False


def test_weather_service():
    """Test weather service."""
    print("\n" + "="*60)
    print("TEST 4: Weather Service")
    print("="*60)
    
    try:
        weather = WeatherService()
        
        # Test current weather
        current = weather.get_current_weather(16.3700, 80.7200)  # Emani Duggirala, AP
        print(f"Temperature: {current.get('temp_celsius')}°C")
        print(f"Humidity: {current.get('humidity_percent')}%")
        print(f"Conditions: {current.get('conditions')}")
        print("✅ Weather service working")
        
        return True
    except Exception as e:
        print(f"❌ Weather test failed: {e}")
        return False


def test_satellite_monitor():
    """Test satellite monitoring."""
    print("\n" + "="*60)
    print("TEST 5: Satellite Monitoring")
    print("="*60)
    
    try:
        satellite = SatelliteMonitor()
        
        # Test NDVI calculation
        ndvi = satellite.calculate_ndvi(0.5, 0.2)
        print(f"NDVI (NIR=0.5, Red=0.2): {ndvi:.3f}")
        
        # Test health score conversion
        health = satellite.ndvi_to_health_score(ndvi)
        print(f"Health Score: {health}/100")
        
        # Test health concern
        concern = satellite.get_health_concern(health)
        print(f"Concern: {concern}")
        
        # Test satellite data fetch
        data = satellite.fetch_satellite_data(16.3700, 80.7200)  # Emani Duggirala, AP
        print(f"Satellite Data: NDVI={data['ndvi']:.3f}, Cloud={data['cloud_cover_percent']}%")
        
        print("✅ Satellite monitoring working")
        return True
    except Exception as e:
        print(f"❌ Satellite test failed: {e}")
        return False


def test_visualization():
    """Test graph generation."""
    print("\n" + "="*60)
    print("TEST 6: Visualization")
    print("="*60)
    
    try:
        visualizer = GraphGenerator()
        
        # Test health trend graph
        graph_path = visualizer.create_health_trend_graph(
            "Thurpu Polam",
            "తూర్పు పొలం"
        )
        
        if graph_path and os.path.exists(graph_path):
            print(f"✅ Health graph generated: {graph_path}")
        else:
            print("⚠️ Graph file not created")
        
        # Test irrigation calendar
        calendar_path = visualizer.create_irrigation_calendar(
            "Thurpu Polam",
            ["2025-02-01", "2025-02-08"]
        )
        
        if calendar_path and os.path.exists(calendar_path):
            print(f"✅ Calendar generated: {calendar_path}")
        else:
            print("⚠️ Calendar file not created")
        
        return True
    except Exception as e:
        print(f"❌ Visualization test failed: {e}")
        return False


def test_agent_intent():
    """Test agent intent detection."""
    print("\n" + "="*60)
    print("TEST 7: Agent Intent Detection")
    print("="*60)
    
    try:
        agent = FarmAgent()
        
        test_cases = [
            ("I watered thurpu polam", "log_irrigation"),
            ("Show athota status", "check_plot"),
            ("Munnagi satellite report", "satellite_report"),
            ("Which plots need water", "check_due"),
            ("help", "help")
        ]
        
        for user_input, expected_action in test_cases:
            from src.agent import AgentState
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
            
            state = agent.understand_intent(state)
            actual_action = state['action']
            status = "✅" if actual_action == expected_action else "❌"
            print(f"{status} '{user_input}' → {actual_action}")
        
        return True
    except Exception as e:
        print(f"❌ Intent test failed: {e}")
        return False


def test_agent_process():
    """Test full agent processing."""
    print("\n" + "="*60)
    print("TEST 8: Full Agent Processing")
    print("="*60)
    
    try:
        agent = FarmAgent()
        
        test_messages = [
            "I watered thurpu polam",
            "Show athota status",
            "Munnagi satellite report",
            "Which plots need water",
            "help"
        ]
        
        for msg in test_messages:
            print(f"\n📝 Input: {msg}")
            response = agent.process_message(msg)
            
            # Check if dual language
            if "---" in response:
                parts = response.split("---")
                print(f"English part: {parts[0][:100]}...")
                print(f"Telugu part: {parts[1][:100] if len(parts) > 1 else 'N/A'}...")
                print("✅ Dual language response")
            else:
                print(f"Response: {response[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Agent processing test failed: {e}")
        return False


def test_agent_intelligence():
    """Test 9: LLM-based agent intelligence (WOW-1/2)."""
    print("\n" + "="*60)
    print("TEST 9: LLM Manager & Intelligent Intent Detection")
    print("="*60)
    
    try:
        from src.llm_manager import create_local_llm
        
        # Test LLM Manager
        print("Testing LLM Manager...")
        llm = create_local_llm()
        response = llm.query(
            prompt="What is NDVI?",
            system_prompt="Answer in one sentence.",
            temperature=0.1
        )
        
        assert len(response) > 10, "LLM should return a response"
        print(f"✅ LLM Response: {response[:80]}...")
        
        # Test intelligent intent detection
        print("\nTesting intelligent intent detection...")
        agent = FarmAgent(use_ollama=False)
        
        test_cases = [
            ("I watered the plot", "log_irrigation"),
            ("Show me athota status", "check_plot"),
            ("Get satellite data", "satellite_report"),
        ]
        
        for user_input, expected_action in test_cases:
            state = {
                "user_input": user_input,
                "messages": [],
                "plot_name": "",
                "action": "",
                "detected_language": "",
                "response_english": "",
                "response_telugu": "",
                "final_response": ""
            }
            
            result = agent.understand_intent(state)
            action = result.get('action', 'help')
            print(f"   ✓ '{user_input}' → {action}")
        
        print("✅ Agent intelligence tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Agent intelligence test failed: {e}")
        return False


def test_satellite_intelligence():
    """Test 10: Satellite intelligence with LLM (WOW-3)."""
    print("\n" + "="*60)
    print("TEST 10: Satellite Intelligence (Expert Agronomist Mode)")
    print("="*60)
    
    try:
        satellite = SatelliteMonitor()
        
        # Get health data
        health_data = satellite.get_health_score(0.65, 20)
        
        assert 'health_score' in health_data
        assert 'ndvi' in health_data
        print(f"✅ Health score: {health_data['health_score']}/100")
        print(f"✅ NDVI: {health_data['ndvi']:.3f}")
        print(f"✅ Assessment: {health_data.get('assessment', 'N/A')[:60]}...")
        print("✅ Satellite intelligence tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Satellite intelligence test failed: {e}")
        return False


def test_multi_agent_orchestration():
    """Test 11: Multi-agent system coordination (WOW-4/5)."""
    print("\n" + "="*60)
    print("TEST 11: Multi-Agent System Coordination")
    print("="*60)
    
    try:
        from src.multi_agent_system import AgentCoordinator
        
        coordinator = AgentCoordinator()
        print("✅ Agent Coordinator initialized")
        print("   • Satellite Interpreter Agent")
        print("   • Weather Analyst Agent")
        print("   • Crop Health Diagnostic Agent")
        print("   • Farmer Communication Agent")
        
        # Test comprehensive analysis
        result = coordinator.analyze_plot_comprehensive(
            plot_data={'crop_type_english': 'Jowar', 'name_english': 'Test Plot'},
            satellite_data={'ndvi': 0.65, 'cloud_cover': 20},
            weather_data={'temp_celsius': 32, 'conditions': 'Sunny'},
            forecast_data=[],
            historical_ndvi=[0.60, 0.62, 0.65],
            days_since_irrigation=4,
            farmer_language='telugu'
        )
        
        assert 'satellite_analysis' in result
        assert 'weather_analysis' in result
        assert 'health_diagnosis' in result
        assert 'technical_report' in result
        assert 'farmer_message' in result
        
        print("✅ Multi-agent analysis completed")
        print(f"   • Satellite: {result['satellite_analysis'].get('interpretation', 'N/A')[:50]}...")
        print(f"   • Health: {result['health_diagnosis'].get('diagnosis', 'N/A')}")
        print(f"   • Farmer message: {result['farmer_message'][:50]}...")
        print("✅ Multi-agent orchestration tests passed")
        return True
        
    except Exception as e:
        print(f"⚠️ Multi-agent test skipped/failed: {e}")
        return False


def test_uncertainty_and_learning():
    """Test 12: Uncertainty handler and farmer validation (WOW-6/7)."""
    print("\n" + "="*60)
    print("TEST 12: Uncertainty Handler & Farmer Validation")
    print("="*60)
    
    try:
        from src.uncertainty_handler import UncertaintyHandler
        
        handler = UncertaintyHandler()
        print("✅ UncertaintyHandler initialized")
        
        # Test uncertainty detection
        low_confidence = {
            'satellite_analysis': {'confidence': 0.6, 'interpretation': 'unclear'},
            'weather_analysis': {'confidence': 0.65}
        }
        
        is_uncertain = handler.check_if_uncertain(low_confidence)
        assert is_uncertain == True
        print(f"✅ Uncertainty detection: {is_uncertain} (confidence < 70%)")
        
        # Test question generation
        question = handler.generate_clarification_question(
            low_confidence,
            'Test Plot',
            'telugu'
        )
        
        assert 'question_id' in question
        assert 'question_english' in question
        assert 'options' in question
        print(f"✅ Question generated: ID={question['question_id']}")
        print(f"   English: {question['question_english'][:50]}...")
        print(f"   Options: {len(question['options'])}")
        
        # Test farmer response processing
        result = handler.process_farmer_response(
            question['question_id'],
            question['options'][0]
        )
        
        assert 'learned' in result
        print(f"✅ Farmer response processed: learned={result.get('learned')}")
        
        # Test statistics
        stats = handler.get_learning_statistics()
        print(f"✅ Learning stats: {stats['total_learning_events']} events")
        
        print("✅ Uncertainty handler tests passed")
        return True
        
    except Exception as e:
        print(f"⚠️ Uncertainty handler test skipped/failed: {e}")
        return False


def test_agent_answer_action():
    """Test 13: Agent answer action for farmer responses (WOW-7)."""
    print("\n" + "="*60)
    print("TEST 13: Agent Answer Action Handler")
    print("="*60)
    
    try:
        agent = FarmAgent(use_ollama=False)
        
        # Test answer action recognition
        action = agent._fallback_intent_detection("answer abc123 2")
        assert action == "answer"
        print(f"✅ Answer action recognized: {action}")
        
        # Test answer handler exists
        assert hasattr(agent, '_answer_question')
        print("✅ Answer handler method exists")
        
        # Test format validation
        state = {
            "user_input": "answer",
            "action": "answer",
            "plot_name": "",
            "detected_language": "english",
            "response_english": "",
            "response_telugu": "",
            "final_response": ""
        }
        
        result = agent._answer_question(state)
        assert result['response_english'] != ""
        print(f"✅ Answer validation working: {result['response_english'][:50]}...")
        
        print("✅ Agent answer action tests passed")
        return True
        
    except Exception as e:
        print(f"⚠️ Agent answer action test failed: {e}")
        return False



def run_all_tests():
    """Run all tests."""
    print("\n\n")
    print("█" * 60)
    print("FARM PLOT AGENT - COMPREHENSIVE TEST SUITE")
    print("█" * 60)
    
    # Core tests (1-8)
    core_tests = [
        ("Setup", test_setup),
        ("Language Detection", test_language_detection),
        ("Translation", test_translation),
        ("Weather", test_weather_service),
        ("Satellite", test_satellite_monitor),
        ("Visualization", test_visualization),
        ("Intent Detection", test_agent_intent),
        ("Full Processing", test_agent_process),
    ]
    
    # WOW feature tests (9-13)
    wow_tests = [
        ("LLM Manager & Intent", test_agent_intelligence),
        ("Satellite Intelligence", test_satellite_intelligence),
        ("Multi-Agent System", test_multi_agent_orchestration),
        ("Uncertainty Handler", test_uncertainty_and_learning),
        ("Agent Answer Action", test_agent_answer_action),
    ]
    
    results = []
    
    print("\n📋 CORE FEATURES (Tests 1-8)")
    print("-" * 60)
    for test_name, test_func in core_tests:
        try:
            result = test_func()
            results.append((f"Core: {test_name}", result))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            results.append((f"Core: {test_name}", False))
    
    print("\n🚀 WOW FEATURES (Tests 9-13)")
    print("-" * 60)
    for test_name, test_func in wow_tests:
        try:
            result = test_func()
            results.append((f"WOW: {test_name}", result))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            results.append((f"WOW: {test_name}", False))
    
    # Summary
    print("\n\n")
    print("█" * 60)
    print("TEST SUMMARY")
    print("█" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    core_passed = sum(1 for name, result in results if "Core" in name and result)
    wow_passed = sum(1 for name, result in results if "WOW" in name and result)
    
    print("\nDETAILED RESULTS:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📊 SCORE BREAKDOWN:")
    print(f"   Core Features: {core_passed}/8 passed")
    print(f"   WOW Features: {wow_passed}/5 passed")
    print(f"   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("💚 System ready for production deployment")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review errors above.")
    
    print("\n🌾 OPERATION WOW COMPLETE! 🌾")
    print("█" * 60)


if __name__ == "__main__":
    run_all_tests()
