import os
from datetime import datetime, timedelta
from typing import List, Dict
import matplotlib.pyplot as plt
import numpy as np


class GraphGenerator:

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        plt.switch_backend('Agg')

    def create_health_trend_graph(self, plot_name: str, plot_name_te: str,
                                   ndvi_history: List[Dict] = None,
                                   days: int = 30) -> str:
        try:
            if ndvi_history is None:
                ndvi_history = self._generate_mock_history(days)

            fig, ax = plt.subplots(figsize=(12, 6), dpi=100)

            dates = [item['date'] for item in ndvi_history]
            health_scores = [item['health_score'] for item in ndvi_history]

            ax.plot(dates, health_scores, color='#2ecc71', linewidth=2.5, marker='o', markersize=6)

            ax.axhspan(0, 40, alpha=0.15, color='red', label='Stress')
            ax.axhspan(40, 70, alpha=0.15, color='yellow', label='Moderate')
            ax.axhspan(70, 100, alpha=0.15, color='green', label='Healthy')

            ax.set_xlabel('తేదీ (Date)', fontsize=12, fontweight='bold')
            ax.set_ylabel('మొక్కల ఆరోగ్యం (Plant Health)', fontsize=12, fontweight='bold')
            ax.set_title(f'{plot_name_te} - గత {days} రోజులు', fontsize=14, fontweight='bold')

            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='lower right')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            filename = f"{plot_name.replace(' ', '_')}_health_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return filepath

        except Exception as e:
            print(f"⚠️ Graph generation error: {e}")
            return None

    def create_irrigation_calendar(self, plot_name: str,
                                   irrigation_dates: List[str] = None,
                                   days: int = 30) -> str:
        try:
            if irrigation_dates is None:
                irrigation_dates = []

            fig, ax = plt.subplots(figsize=(14, 8), dpi=100)
            start_date = datetime.now() - timedelta(days=days)

            calendar_data = []
            current_date = start_date
            while (datetime.now() - current_date).days >= 0:
                date_str = current_date.strftime('%Y-%m-%d')
                if date_str in irrigation_dates:
                    color = '#2ecc71'
                    label = '💧 Watered'
                else:
                    color = '#e74c3c'
                    label = 'Not watered'
                calendar_data.append({'date': date_str, 'color': color, 'label': label})
                current_date += timedelta(days=1)

            dates = [item['date'] for item in calendar_data]
            colors = [item['color'] for item in calendar_data]

            ax.bar(range(len(dates)), [1]*len(dates), color=colors, width=0.8)
            ax.set_xlabel('తేదీ (Date)', fontsize=12, fontweight='bold')
            ax.set_title(f'{plot_name} - నీటిపారుదల క్యాలెండర్ (Irrigation Calendar)',
                        fontsize=14, fontweight='bold')
            ax.set_xticks(range(0, len(dates), 3))
            ax.set_xticklabels([dates[i] for i in range(0, len(dates), 3)], rotation=45, ha='right')
            ax.set_yticks([])
            plt.tight_layout()

            filename = f"{plot_name.replace(' ', '_')}_irrigation_calendar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return filepath

        except Exception as e:
            print(f"⚠️ Calendar generation error: {e}")
            return None

    def _generate_mock_history(self, days: int = 30) -> List[Dict]:
        history = []
        current_date = datetime.now() - timedelta(days=days)
        base_health = 50

        for i in range(days):
            noise = np.random.normal(0, 5)
            trend = i * 0.3
            health_score = max(10, min(95, base_health + trend + noise))
            ndvi = health_score / 100 + np.random.normal(0, 0.05)
            ndvi = max(0.0, min(1.0, ndvi))
            history.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'ndvi': round(ndvi, 3),
                'health_score': int(health_score)
            })
            current_date += timedelta(days=1)

        return history
