"""Генерация статичной иллюстрации отчёта из демоданных.

Внимание: это не браузерный скриншот Streamlit/HTML; иллюстрация для README.
"""
from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/warehouse/industrial_bi.sqlite'
OUT = ROOT / 'assets/dashboard_preview.png'


def make():
    with sqlite3.connect(DB) as conn:
        df = pd.read_sql('SELECT * FROM vw_energy_enriched', conn)
    daily = df.groupby('full_date')['usage_kwh'].sum()
    types = df.groupby('load_type')['usage_kwh'].sum().reindex(['Light Load','Medium Load','Maximum Load'])
    hours = df.groupby('hour_num')['usage_kwh'].mean()
    total = df['usage_kwh'].sum()
    peak = df['usage_kwh'].max()
    estimated = df['estimated_cost_krw'].sum()

    fig = plt.figure(figsize=(16,9),dpi=130,facecolor='#f3f6fb')
    ax = fig.add_axes([0,0,1,1]);ax.axis('off')
    # Левое меню.
    ax.add_patch(FancyBboxPatch((0,0),.22,1,boxstyle='square,pad=0',facecolor='#12213f',edgecolor='none'))
    fig.text(.035,.923,'INDUSTRIAL / BI',color='white',fontsize=19,weight='bold')
    fig.text(.035,.885,'ENERGY INTELLIGENCE',color='#86b5d1',fontsize=9,weight='bold')
    for i,item in enumerate(['▣   Обзор','◷   Профиль нагрузки','▥   Модель затрат']):
        fig.text(.035,.76-i*.075,item,color='white' if i==0 else '#a9bcda',fontsize=13)
    fig.text(.035,.08,'PORTFOLIO DEMO',color='#849ec1',fontsize=10)
    fig.text(.035,.05,'СИНТЕТИЧЕСКИЕ ДАННЫЕ',color='#849ec1',fontsize=8)

    fig.text(.258,.916,'Industrial Energy Analytics',color='#17243d',fontsize=23,weight='bold')
    fig.text(.258,.878,'Мониторинг энергопотребления · Демо 2025 · Синтетические данные',color='#7a889d',fontsize=11)
    start=.26; w=.167; gap=.013; y=.69
    cards=[('Энергопотребление',f'{total:,.0f} кВт·ч'),('Среднее за 15 мин',f"{df['usage_kwh'].mean():,.1f} кВт·ч"),('Максимальный интервал',f'{peak:,.1f} кВт·ч'),('Модель затрат',f'₩ {estimated/1e6:.2f} млн')]
    for i,(label,val) in enumerate(cards):
        x=start+i*(w+gap)
        ax.add_patch(FancyBboxPatch((x,y),w,.14,boxstyle='round,pad=.008,rounding_size=.012',facecolor='white',edgecolor='#e1e9f3'))
        fig.text(x+.012,y+.101,label,color='#7b879b',fontsize=10)
        fig.text(x+.012,y+.042,val,color='#1e2d47',fontsize=16,weight='bold')
    ax.add_patch(FancyBboxPatch((.26,.367),.705,.292,boxstyle='round,pad=.007,rounding_size=.012',facecolor='white',edgecolor='#e1e9f3'))
    fig.text(.279,.615,'Динамика потребления',fontsize=14,weight='bold',color='#17243d')
    a1=fig.add_axes([.285,.412,.65,.16]);a1.set_facecolor('white')
    x=pd.to_datetime(daily.index)
    a1.fill_between(x,daily.values,alpha=.09,color='#4666d7')
    a1.plot(x,daily.values,color='#4165d6',linewidth=2)
    a1.spines[['top','right','left']].set_visible(False);a1.spines['bottom'].set_color('#e1e9f3')
    a1.tick_params(axis='both',labelsize=8,colors='#7a889d',length=0,pad=7)
    a1.grid(axis='y',alpha=.13)
    a1.set_xlim(x.min(),x.max())
    ax.add_patch(FancyBboxPatch((.26,.05),.336,.285,boxstyle='round,pad=.007,rounding_size=.012',facecolor='white',edgecolor='#e1e9f3'))
    ax.add_patch(FancyBboxPatch((.617,.05),.348,.285,boxstyle='round,pad=.007,rounding_size=.012',facecolor='white',edgecolor='#e1e9f3'))
    fig.text(.279,.287,'Типы нагрузки',fontsize=14,weight='bold',color='#17243d')
    fig.text(.635,.287,'Суточный профиль',fontsize=14,weight='bold',color='#17243d')
    a2=fig.add_axes([.285,.11,.28,.14]);a2.bar(['Light','Medium','Maximum'],types.values/1000,color=['#516cdf','#0ca0ac','#ef6f87'],width=.55)
    a2.set_ylabel('тыс. кВт·ч',fontsize=8,color='#77879f');a2.tick_params(labelsize=9,colors='#77879f',length=0)
    a2.spines[['top','right','left']].set_visible(False);a2.spines['bottom'].set_color('#e1e9f3');a2.grid(axis='y',alpha=.12)
    a3=fig.add_axes([.64,.11,.29,.14]);a3.plot(hours.index,hours.values,color='#0ca0ac',linewidth=2.5)
    a3.fill_between(hours.index,hours.values,alpha=.09,color='#0ca0ac')
    a3.set_xlim(0,23);a3.tick_params(labelsize=9,colors='#77879f',length=0)
    a3.set_xlabel('Час',fontsize=8,color='#77879f')
    a3.spines[['top','right','left']].set_visible(False);a3.spines['bottom'].set_color('#e1e9f3');a3.grid(axis='y',alpha=.12)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT,facecolor=fig.get_facecolor(),bbox_inches='tight',pad_inches=0)
    plt.close(fig)
    print(OUT)


if __name__=='__main__': make()
