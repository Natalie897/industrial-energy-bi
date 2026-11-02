"""Генерирует полностью СИНТЕТИЧЕСКИЙ набор данных для офлайн-демонстрации.

Запуск: python -m src.generate_demo
Не является оригинальным датасетом UCI; при загрузке UCI файл заменяется.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from src.config import RAW


def generate_demo(output: Path = RAW, days: int = 90) -> Path:
    if days < 1:
        raise ValueError('days must be >= 1')
    times = pd.date_range('2025-01-01 00:00', periods=days * 96, freq='15min')
    rng = np.random.default_rng(42)
    hour = times.hour.to_numpy() + times.minute.to_numpy() / 60
    weekday = times.dayofweek.to_numpy() < 5
    peak = (hour >= 17) & (hour < 22)
    offpeak = (hour < 6) | (hour >= 22)
    load = np.select([peak, offpeak], ['Maximum Load', 'Light Load'], default='Medium Load')
    activity = np.where(weekday, 1, 0.72)
    seasonal = 1 + 0.10 * np.sin(np.arange(len(times)) * 2 * np.pi / (96 * 28))
    base = 35 + 25 * (hour >= 7) * (hour < 19) + 42 * peak
    noise = rng.normal(0, 7.0, len(times))
    usage = np.maximum(5, (base * activity * seasonal + noise)).round(2)
    anomaly_idx = rng.choice(len(usage), size=max(1, days // 7), replace=False)
    usage[anomaly_idx] *= 1.65
    usage = usage.round(2)
    co2 = (usage * 0.00043).round(4)  # учебная модель, а не измерения выбросов
    frame = pd.DataFrame({
        'date': times.strftime('%d/%m/%Y %H:%M'),
        'Usage_kWh': usage,
        'Lagging_Current_Reactive.Power_kVarh': (usage * rng.uniform(0.08, 0.3, len(times))).round(3),
        'Leading_Current_Reactive_Power_kVarh': (usage * rng.uniform(0.03, 0.12, len(times))).round(3),
        'CO2(tCO2)': co2,
        'Lagging_Current_Power_Factor': rng.uniform(74, 98, len(times)).round(2),
        'Leading_Current_Power_Factor': rng.uniform(76, 99, len(times)).round(2),
        'NSM': (times.hour * 3600 + times.minute * 60).astype(int),
        'WeekStatus': np.where(weekday, 'Weekday', 'Weekend'),
        'Day_of_week': times.day_name(),
        'Load_Type': load,
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f'Синтетические данные: {len(frame):,} строк -> {output}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=RAW)
    parser.add_argument('--days', type=int, default=90)
    args = parser.parse_args()
    generate_demo(args.output, args.days)
