"""ETL: raw CSV -> проверки -> staging + dimensional model SQLite + CSV exports.

Поддерживаются оригинальная схема UCI и синтетическая демо-версия.
Команда: python -m src.etl --source demo
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import RAW, WAREHOUSE, PROCESSED, DEMO_TARIFF_KRW, LOAD_ID

REQUIRED = [
    'date', 'Usage_kWh', 'Lagging_Current_Reactive.Power_kVarh',
    'Leading_Current_Reactive_Power_kVarh', 'CO2(tCO2)',
    'Lagging_Current_Power_Factor', 'Leading_Current_Power_Factor',
    'NSM', 'WeekStatus', 'Day_of_week', 'Load_Type',
]
NUMERIC = [x for x in REQUIRED if x not in ('date', 'WeekStatus', 'Day_of_week', 'Load_Type')]


class DataQualityError(ValueError):
    pass


def normalize_load_type(value: str) -> str:
    candidate = str(value).strip().lower().replace('_', ' ').replace('-', ' ')
    candidate = ' '.join(candidate.split())
    mapping = {'light load': 'Light Load', 'medium load': 'Medium Load', 'maximum load': 'Maximum Load'}
    if candidate not in mapping:
        raise DataQualityError(f'Неизвестный тип нагрузки: {value}')
    return mapping[candidate]


def transform(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    missing = [col for col in REQUIRED if col not in raw.columns]
    if missing:
        raise DataQualityError(f'Отсутствуют обязательные столбцы: {missing}')
    if raw.empty:
        raise DataQualityError('CSV пустой')
    df = raw[REQUIRED].copy()
    parsed = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    if parsed.isna().any():
        raise DataQualityError(f'Некорректные timestamp: {int(parsed.isna().sum())}')
    if parsed.duplicated().any():
        raise DataQualityError(f'Дубли timestamp: {int(parsed.duplicated().sum())}')
    if not parsed.is_monotonic_increasing:
        df = df.iloc[parsed.argsort()].reset_index(drop=True)
        parsed = parsed.sort_values().reset_index(drop=True)
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isna().any():
            raise DataQualityError(f'Пустое/нечисловое значение в {col}')
        if not (df[col] >= 0).all():
            raise DataQualityError(f'Отрицательное значение в {col}')
    for col in ('Lagging_Current_Power_Factor','Leading_Current_Power_Factor'):
        if (df[col] > 100).any():
            raise DataQualityError(f'{col} больше 100%')
    if ((df['NSM'] != parsed.dt.hour * 3600 + parsed.dt.minute * 60)).any():
        raise DataQualityError('NSM не совпадает со временем timestamp')
    df['load_type'] = df['Load_Type'].map(normalize_load_type)
    df['week_status'] = df['WeekStatus'].astype(str).str.strip().str.lower()
    if not df['week_status'].isin(['weekday', 'weekend']).all():
        raise DataQualityError('Неизвестный WeekStatus')
    if (df['week_status'] != pd.Series(parsed.dt.dayofweek >= 5).map({True:'weekend',False:'weekday'}).to_numpy()).any():
        raise DataQualityError('WeekStatus противоречит календарю')
    if (df['Day_of_week'].astype(str).str.strip().str.lower() != parsed.dt.day_name().str.lower()).any():
        raise DataQualityError('Day_of_week противоречит timestamp')
    if (parsed.dt.minute % 15 != 0).any() or (parsed.dt.second != 0).any():
        raise DataQualityError('Ожидается 15-минутный шаг')

    stg = pd.DataFrame({
        'timestamp_local': parsed.dt.strftime('%Y-%m-%d %H:%M:%S'),
        'usage_kwh': df['Usage_kWh'].round(6),
        'lagging_reactive_kvarh': df['Lagging_Current_Reactive.Power_kVarh'].round(6),
        'leading_reactive_kvarh': df['Leading_Current_Reactive_Power_kVarh'].round(6),
        'co2_source_value': df['CO2(tCO2)'].round(6),
        'lagging_power_factor_pct': df['Lagging_Current_Power_Factor'].round(6),
        'leading_power_factor_pct': df['Leading_Current_Power_Factor'].round(6),
        'seconds_from_midnight': df['NSM'].astype('int64'),
        'week_status': df['week_status'],
        'load_type': df['load_type'],
    })
    dates = pd.Series(parsed.dt.normalize().drop_duplicates().sort_values()).reset_index(drop=True)
    dim_date = pd.DataFrame({
        'date_key': dates.dt.strftime('%Y%m%d').astype(int),
        'full_date': dates.dt.strftime('%Y-%m-%d'),
        'year_num': dates.dt.year,
        'quarter_num': dates.dt.quarter,
        'month_num': dates.dt.month,
        'day_num': dates.dt.day,
        'weekday_num': dates.dt.dayofweek + 1,
        'weekday_name': dates.dt.day_name(),
        'is_weekend': (dates.dt.dayofweek >= 5).astype(int),
    })
    minutes = sorted((parsed.dt.hour * 60 + parsed.dt.minute).unique().tolist())
    dim_time = pd.DataFrame({
        'time_key': minutes,
        'hour_num': [n // 60 for n in minutes],
        'minute_num': [n % 60 for n in minutes],
        'time_label': [f'{n//60:02}:{n%60:02}' for n in minutes],
    })
    dim_load_type = pd.DataFrame({
        'load_type_key': list(LOAD_ID.values()),
        'load_type': list(LOAD_ID.keys()),
        'demo_tariff_krw_kwh': list(DEMO_TARIFF_KRW.values()),
    })
    fact = pd.DataFrame({
        'reading_id': range(1, len(df) + 1),
        'timestamp_local': stg['timestamp_local'],
        'date_key': parsed.dt.strftime('%Y%m%d').astype(int),
        'time_key': (parsed.dt.hour * 60 + parsed.dt.minute).astype(int),
        'load_type_key': df['load_type'].map(LOAD_ID).astype(int),
        'usage_kwh': stg['usage_kwh'],
        'lagging_reactive_kvarh': stg['lagging_reactive_kvarh'],
        'leading_reactive_kvarh': stg['leading_reactive_kvarh'],
        'co2_source_value': stg['co2_source_value'],
        'lagging_power_factor_pct': stg['lagging_power_factor_pct'],
        'leading_power_factor_pct': stg['leading_power_factor_pct'],
    })
    # Контроль баланса до записи в БД.
    if abs(fact['usage_kwh'].sum() - stg['usage_kwh'].sum()) > 1e-5:
        raise DataQualityError('Расхождение total kWh после преобразования')
    return {
        'stg_energy_readings': stg,
        'dim_date': dim_date,
        'dim_time': dim_time,
        'dim_load_type': dim_load_type,
        'fact_energy_readings': fact,
    }


def build(input_csv: Path = RAW, database: Path = WAREHOUSE, exports: Path = PROCESSED, source: str = 'demo') -> dict:
    if source not in ('demo', 'uci'):
        raise ValueError('source must be demo or uci')
    if not input_csv.exists():
        raise FileNotFoundError(f'CSV не найден: {input_csv}')
    raw = pd.read_csv(input_csv)
    if source == 'uci' and len(raw) != 35040:
        raise DataQualityError('Режим UCI: ожидается 35040 записей; проверьте источник')
    tables = transform(raw)
    database.parent.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    temporary = database.with_suffix('.new.sqlite')
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript('''
        CREATE TABLE project_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE stg_energy_readings (
            timestamp_local TEXT NOT NULL, usage_kwh REAL NOT NULL CHECK(usage_kwh>=0),
            lagging_reactive_kvarh REAL NOT NULL, leading_reactive_kvarh REAL NOT NULL,
            co2_source_value REAL NOT NULL, lagging_power_factor_pct REAL NOT NULL,
            leading_power_factor_pct REAL NOT NULL, seconds_from_midnight INTEGER NOT NULL,
            week_status TEXT NOT NULL, load_type TEXT NOT NULL
        );
        CREATE TABLE dim_date (
            date_key INTEGER PRIMARY KEY, full_date TEXT NOT NULL UNIQUE,
            year_num INTEGER NOT NULL, quarter_num INTEGER NOT NULL,
            month_num INTEGER NOT NULL, day_num INTEGER NOT NULL,
            weekday_num INTEGER NOT NULL, weekday_name TEXT NOT NULL,
            is_weekend INTEGER NOT NULL CHECK(is_weekend IN(0,1))
        );
        CREATE TABLE dim_time (
            time_key INTEGER PRIMARY KEY, hour_num INTEGER NOT NULL,
            minute_num INTEGER NOT NULL, time_label TEXT NOT NULL
        );
        CREATE TABLE dim_load_type (
            load_type_key INTEGER PRIMARY KEY, load_type TEXT NOT NULL UNIQUE,
            demo_tariff_krw_kwh REAL NOT NULL CHECK(demo_tariff_krw_kwh >= 0)
        );
        CREATE TABLE fact_energy_readings (
            reading_id INTEGER PRIMARY KEY,
            timestamp_local TEXT NOT NULL UNIQUE,
            date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
            time_key INTEGER NOT NULL REFERENCES dim_time(time_key),
            load_type_key INTEGER NOT NULL REFERENCES dim_load_type(load_type_key),
            usage_kwh REAL NOT NULL CHECK(usage_kwh>=0),
            lagging_reactive_kvarh REAL NOT NULL,
            leading_reactive_kvarh REAL NOT NULL,
            co2_source_value REAL NOT NULL,
            lagging_power_factor_pct REAL NOT NULL,
            leading_power_factor_pct REAL NOT NULL
        );
        ''')
        for table in ['stg_energy_readings','dim_date','dim_time','dim_load_type','fact_energy_readings']:
            tables[table].to_sql(table, connection, if_exists='append', index=False)
        invalid_fk = connection.execute('PRAGMA foreign_key_check').fetchall()
        if invalid_fk:
            raise DataQualityError(f'Нарушение внешних ключей: {invalid_fk[:5]}')
        connection.execute('CREATE INDEX idx_fact_date ON fact_energy_readings(date_key)')
        connection.execute('CREATE INDEX idx_fact_load ON fact_energy_readings(load_type_key)')
        connection.executescript('''
        CREATE VIEW vw_energy_enriched AS
        SELECT f.reading_id, f.timestamp_local, d.full_date, d.year_num, d.quarter_num,
          d.month_num, d.weekday_num, d.weekday_name, d.is_weekend, t.hour_num,
          t.minute_num, l.load_type, l.demo_tariff_krw_kwh,
          f.usage_kwh, f.lagging_reactive_kvarh, f.leading_reactive_kvarh,
          f.co2_source_value, f.lagging_power_factor_pct,
          f.leading_power_factor_pct,
          ROUND(f.usage_kwh * l.demo_tariff_krw_kwh, 2) AS estimated_cost_krw
        FROM fact_energy_readings f
        JOIN dim_date d ON d.date_key = f.date_key
        JOIN dim_time t ON t.time_key = f.time_key
        JOIN dim_load_type l ON l.load_type_key = f.load_type_key;
        ''')
        connection.executemany('INSERT INTO project_metadata(key,value) VALUES (?,?)', [
            ('source_kind', source),
            ('source_url', 'UCI Steel Industry Energy Consumption' if source == 'uci' else 'SYNTHETIC DEMO. NOT UCI DATA'),
            ('tariff_kind', 'ILLUSTRATIVE SYNTHETIC KRW rates, not real invoices'),
            ('record_count', str(len(raw))),
        ])
        connection.commit()
        count, total = connection.execute('SELECT COUNT(*), SUM(usage_kwh) FROM fact_energy_readings').fetchone()
        if count != len(raw) or abs(total - raw['Usage_kWh'].sum()) > 1e-4:
            raise DataQualityError('Контрольная сверка источника с DWH не прошла')
    finally:
        connection.close()
    temporary.replace(database)
    for table, df in tables.items():
        df.to_csv(exports / f'{table}.csv', index=False)
    (exports / 'SOURCE_KIND.txt').write_text(source.upper() + '\n', encoding='utf-8')
    result = {'rows': len(raw), 'days': len(tables['dim_date']), 'total_kwh': float(raw['Usage_kWh'].sum()), 'source': source}
    print(f"ETL готов: {result['rows']:,} строк, {result['days']} дней, {result['total_kwh']:,.2f} кВт·ч; режим {source}")
    print(f'Хранилище: {database}')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=RAW)
    parser.add_argument('--db', type=Path, default=WAREHOUSE)
    parser.add_argument('--exports', type=Path, default=PROCESSED)
    parser.add_argument('--source', choices=['demo','uci'], default='demo')
    args = parser.parse_args()
    build(args.input, args.db, args.exports, args.source)
