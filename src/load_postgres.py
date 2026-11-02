"""COPY подготовленных витрин в PostgreSQL.

Пример: python -m src.load_postgres --dsn "postgresql://postgres:secret@localhost:5432/industrial_bi"
Требуется запущенный PostgreSQL; запуск на реальной БД здесь не тестировался.
"""
import argparse
from pathlib import Path

from src.config import ROOT, PROCESSED

TABLES = ['dim_date','dim_time','dim_load_type','stg_energy_readings','fact_energy_readings']


def load(dsn: str):
    import psycopg
    missing = [str(PROCESSED / f'{t}.csv') for t in TABLES if not (PROCESSED / f'{t}.csv').exists()]
    if missing:
        raise FileNotFoundError(f'Не хватает экспорта; выполните ETL: {missing}')
    ddl = (ROOT / 'sql' / '02_postgresql_schema.sql').read_text(encoding='utf-8')
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            # Явный сброс данных текущего проекта для идемпотентного повторного запуска.
            cur.execute('TRUNCATE TABLE industrial_bi.fact_energy_readings, industrial_bi.stg_energy_readings, industrial_bi.dim_date, industrial_bi.dim_time, industrial_bi.dim_load_type')
            for table in TABLES:
                csv_path = PROCESSED / f'{table}.csv'
                with cur.copy(f'COPY industrial_bi.{table} FROM STDIN WITH (FORMAT CSV, HEADER true)') as copy:
                    with csv_path.open('rb') as f:
                        while chunk := f.read(65536):
                            copy.write(chunk)
                print(f'Загружено в {table}')
            cur.execute('SELECT COUNT(*), SUM(usage_kwh) FROM industrial_bi.fact_energy_readings')
            print('PostgreSQL, строки и суммарное kWh:', cur.fetchone())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', required=True, help='DSN к вашей учебной PostgreSQL БД')
    load(parser.parse_args().dsn)
