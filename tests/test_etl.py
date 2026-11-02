import sqlite3

import pandas as pd
import pytest

from src.generate_demo import generate_demo
from src.etl import DataQualityError, transform, build


def fixture_df(tmp_path):
    path = tmp_path / 'demo.csv'
    generate_demo(path, days=2)
    return pd.read_csv(path)


def test_star_schema_and_dwh_reconciliation(tmp_path):
    path = tmp_path / 'demo.csv'
    generate_demo(path, days=2)
    df = pd.read_csv(path)
    tables = transform(df)
    assert len(tables['fact_energy_readings']) == len(df) == 192
    assert len(tables['dim_date']) == 2
    assert len(tables['dim_time']) == 96
    assert len(tables['dim_load_type']) == 3
    db = tmp_path / 'warehouse.sqlite'
    build(path, db, tmp_path / 'exports', 'demo')
    with sqlite3.connect(db) as conn:
        n, kwh, cost = conn.execute('SELECT COUNT(*),SUM(usage_kwh),SUM(estimated_cost_krw) FROM vw_energy_enriched').fetchone()
        assert n == len(df)
        assert kwh == pytest.approx(df['Usage_kWh'].sum())
        assert cost > 0
        assert conn.execute('SELECT COUNT(*) FROM dim_time').fetchone()[0] == 96


def test_duplicate_timestamp_rejected(tmp_path):
    df = fixture_df(tmp_path)
    df.loc[1, 'date'] = df.loc[0, 'date']
    with pytest.raises(DataQualityError, match='Дубли'):
        transform(df)


def test_negative_energy_rejected(tmp_path):
    df = fixture_df(tmp_path)
    df.loc[0, 'Usage_kWh'] = -1
    with pytest.raises(DataQualityError, match='Отрицательное'):
        transform(df)


def test_invalid_load_category_rejected(tmp_path):
    df = fixture_df(tmp_path)
    df.loc[0, 'Load_Type'] = 'Not a load type'
    with pytest.raises(DataQualityError, match='Неизвестный тип'):
        transform(df)


def test_missing_column_rejected(tmp_path):
    df = fixture_df(tmp_path).drop(columns=['NSM'])
    with pytest.raises(DataQualityError, match='Отсутствуют'):
        transform(df)


def test_weekstatus_mismatch_rejected(tmp_path):
    df = fixture_df(tmp_path)
    df.loc[0, 'WeekStatus'] = 'Weekend'
    with pytest.raises(DataQualityError, match='WeekStatus противоречит'):
        transform(df)


def test_idempotent_warehouse_rebuild(tmp_path):
    path = tmp_path / 'demo.csv'
    generate_demo(path, days=1)
    db = tmp_path / 'd.sqlite'
    for _ in range(2):
        build(path, db, tmp_path / 'exports', 'demo')
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM fact_energy_readings').fetchone()[0] == 96


def test_uci_mode_rejects_incomplete_demo(tmp_path):
    path = tmp_path / 'demo.csv'
    generate_demo(path, days=1)
    with pytest.raises(DataQualityError, match='35040'):
        build(path, tmp_path / 'd.sqlite', tmp_path / 'exports', 'uci')
