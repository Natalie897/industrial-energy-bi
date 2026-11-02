"""Общие константы проекта Industrial Energy BI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'Steel_industry_data.csv'
WAREHOUSE = ROOT / 'data' / 'warehouse' / 'industrial_bi.sqlite'
PROCESSED = ROOT / 'data' / 'processed'
REPORT = ROOT / 'dashboard' / 'report.html'

# Гипотетические тарифы (KRW за кВт·ч), НЕ фактические тарифы предприятия.
DEMO_TARIFF_KRW = {
    'Light Load': 95.0,
    'Medium Load': 125.0,
    'Maximum Load': 165.0,
}
LOAD_ID = {'Light Load': 1, 'Medium Load': 2, 'Maximum Load': 3}
SOURCE_URL = 'https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption'
ARCHIVE_URL = 'https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip'
