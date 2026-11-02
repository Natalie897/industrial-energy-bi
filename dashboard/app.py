"""Streamlit BI dashboard. Команда: python -m streamlit run dashboard/app.py"""
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'warehouse' / 'industrial_bi.sqlite'
st.set_page_config(page_title='Industrial Energy BI', page_icon='⚡', layout='wide')


@st.cache_data

def load_data(modified_time):
    with sqlite3.connect(DB) as conn:
        df = pd.read_sql_query('SELECT * FROM vw_energy_enriched', conn)
        meta = dict(conn.execute('SELECT key,value FROM project_metadata'))
    df['full_date'] = pd.to_datetime(df['full_date'])
    return df, meta


if not DB.exists():
    st.error('Не найдено хранилище. Запустите: python -m src.generate_demo; python -m src.etl --source demo')
    st.stop()

df, meta = load_data(DB.stat().st_mtime)
st.title('⚡ Industrial Energy Analytics')
st.caption('Учебный BI/DWH-проект: мониторинг энергопотребления, профиль нагрузки и модель затрат')
if meta.get('source_kind') == 'demo':
    st.warning('ДЕМОНСТРАЦИОННЫЕ СИНТЕТИЧЕСКИЕ ДАННЫЕ — не реальные измерения UCI.')
else:
    st.info('Исходный набор: UCI Steel Industry Energy Consumption (CC BY 4.0).')
st.caption('Стоимость рассчитана по условным тарифам и не является фактическими счетами предприятия.')

with st.sidebar:
    st.header('Фильтры')
    min_date, max_date = df['full_date'].min().date(), df['full_date'].max().date()
    selected = st.date_input('Период', (min_date, max_date), min_value=min_date, max_value=max_date)
    load_types = st.multiselect('Тип нагрузки', sorted(df['load_type'].unique()), default=sorted(df['load_type'].unique()))
if isinstance(selected, tuple) and len(selected) == 2:
    df = df[df['full_date'].dt.date.between(selected[0], selected[1])]
df = df[df['load_type'].isin(load_types)]
if df.empty:
    st.warning('Нет данных при выбранных фильтрах.')
    st.stop()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric('Энергопотребление, кВт·ч', f"{df['usage_kwh'].sum():,.0f}")
kpi2.metric('Среднее за 15 мин, кВт·ч', f"{df['usage_kwh'].mean():,.1f}")
kpi3.metric('Максимум за 15 мин, кВт·ч', f"{df['usage_kwh'].max():,.1f}")
kpi4.metric('Модель затрат, ₩', f"{df['estimated_cost_krw'].sum():,.0f}")

tab1, tab2, tab3 = st.tabs(['Обзор', 'Профиль нагрузки', 'Модель затрат'])
with tab1:
    daily = df.groupby('full_date', as_index=False)['usage_kwh'].sum()
    st.plotly_chart(px.line(daily, x='full_date', y='usage_kwh', title='Энергопотребление по дням'), use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.bar(df.groupby('load_type',as_index=False)['usage_kwh'].sum(), x='load_type', y='usage_kwh', title='По типам нагрузки'), use_container_width=True)
    with right:
        week = df.assign(period=df['is_weekend'].map({0:'Рабочий',1:'Выходной'})).groupby('period',as_index=False)['usage_kwh'].mean()
        st.plotly_chart(px.bar(week, x='period', y='usage_kwh', title='Среднее за 15 минут: рабочие / выходные'), use_container_width=True)
with tab2:
    grid = df.groupby(['weekday_num','hour_num'],as_index=False)['usage_kwh'].mean()
    pivot = grid.pivot(index='weekday_num',columns='hour_num',values='usage_kwh')
    st.plotly_chart(px.imshow(pivot, labels={'x':'Час','y':'День недели','color':'кВт·ч'},title='Тепловая карта по часу / дню недели'), use_container_width=True)
    hours = df.groupby('hour_num',as_index=False)['usage_kwh'].mean()
    st.plotly_chart(px.line(hours,x='hour_num',y='usage_kwh',markers=True,title='Средний профиль за 15 минут по часам'),use_container_width=True)
    st.subheader('Топ-10 пиковых интервалов')
    st.dataframe(df.nlargest(10,'usage_kwh')[['timestamp_local','load_type','usage_kwh']],hide_index=True)
with tab3:
    cost_month = df.assign(month=df['full_date'].dt.to_period('M').astype(str)).groupby('month',as_index=False)['estimated_cost_krw'].sum()
    st.plotly_chart(px.bar(cost_month, x='month', y='estimated_cost_krw',title='Условная стоимость по месяцам, KRW'),use_container_width=True)
    st.plotly_chart(px.pie(df.groupby('load_type',as_index=False)['estimated_cost_krw'].sum(),names='load_type',values='estimated_cost_krw',title='Структура условных расходов'),use_container_width=True)
    st.caption('Условные тарифы: Light Load 95 ₩/кВт·ч, Medium Load 125 ₩/кВт·ч, Maximum Load 165 ₩/кВт·ч.')

st.download_button('Скачать отфильтрованные данные CSV', df.to_csv(index=False).encode('utf-8-sig'),file_name='energy_filtered.csv',mime='text/csv')
