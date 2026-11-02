"""Генерирует полностью автономный интерактивный HTML-дэшборд из SQLite.

Команда: python -m src.build_report
"""
import json
import sqlite3
from html import escape
from pathlib import Path

import pandas as pd
from plotly.offline.offline import get_plotlyjs

from src.config import WAREHOUSE, REPORT


def build_report(db: Path = WAREHOUSE, output: Path = REPORT) -> Path:
    if not db.exists():
        raise FileNotFoundError('Сначала выполните: python -m src.etl --source demo')
    with sqlite3.connect(db) as conn:
        source = dict(conn.execute('SELECT key,value FROM project_metadata'))
        data = pd.read_sql_query('''SELECT full_date, hour_num, minute_num, weekday_num,
                    is_weekend, load_type, usage_kwh, estimated_cost_krw
                    FROM vw_energy_enriched ORDER BY timestamp_local''', conn)
    # Сокращаем объём встроенного JSON: формат [дата, час, минута, день недели, выходной, тип, кВт·ч, KRW]
    load_id = {'Light Load': 0, 'Medium Load': 1, 'Maximum Load': 2}
    data['load_num'] = data['load_type'].map(load_id)
    records = [[str(day), int(h), int(m), int(wd), int(w), int(l), float(kwh), float(cost)]
               for day,h,m,wd,w,l,kwh,cost in data[['full_date','hour_num','minute_num','weekday_num','is_weekend','load_num','usage_kwh','estimated_cost_krw']].itertuples(index=False, name=None)]
    js_rows = json.dumps(records, separators=(',', ':'), ensure_ascii=False)
    months = sorted({r[0][:7] for r in records})
    opts = ''.join(f'<option value="{escape(m)}">{escape(m)}</option>' for m in months)
    source_kind = source.get('source_kind','unknown')
    subtitle = 'СИНТЕТИЧЕСКИЕ ДАННЫЕ · учебная демонстрация' if source_kind == 'demo' else 'РЕАЛЬНЫЕ ИЗМЕРЕНИЯ UCI · 2018 год'
    html = r'''<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Industrial Energy BI · Portfolio Demo</title>
<style>
:root {--ink:#17233f;--muted:#718098;--bg:#f4f7fc;--card:#fff;--line:#e5ebf4;--accent:#3659d6;--cyan:#0e9fa9;--pink:#f06b80}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;margin:0}
.shell{display:grid;grid-template-columns:235px 1fr;min-height:100vh}.side{background:#111f3e;color:#d9e4ff;padding:29px 19px;display:flex;flex-direction:column;gap:30px}
.logo{font-weight:850;letter-spacing:-.8px;font-size:20px;color:white;line-height:1.12}.logo span{color:#69d4dd}.caption{font-size:11px;letter-spacing:1.6px;font-weight:700;color:#92a7c6;margin-top:8px}
.nav{display:flex;flex-direction:column;gap:7px}.nav button{font:inherit;font-size:14px;text-align:left;border:0;color:#a9bbd8;background:transparent;padding:13px 14px;border-radius:10px;cursor:pointer}.nav button.active,.nav button:hover{background:#293c65;color:#fff}
.sidefoot{margin-top:auto;font-size:11px;line-height:1.7;color:#9db0d0}.content{padding:30px 40px 60px;min-width:0;max-width:1550px;width:100%;margin:auto}
.header{display:flex;gap:20px;align-items:flex-start;justify-content:space-between;margin-bottom:23px}h1{font-size:30px;letter-spacing:-.8px;margin:0 0 8px}p.subtitle{font-size:13px;color:var(--muted);margin:0}
.tag{border:1px solid #d7dff6;color:#3652a0;background:#edf2ff;border-radius:30px;padding:8px 13px;font-weight:750;font-size:11px;white-space:normal;max-width:300px;line-height:1.5}
.filters{padding:14px 18px;display:flex;flex-wrap:wrap;gap:20px;align-items:end;background:white;border:1px solid var(--line);border-radius:14px;margin-bottom:22px}
.filters label{display:flex;flex-direction:column;gap:7px;font-size:12px;color:#60728b;font-weight:650}.filters select{font:inherit;font-size:14px;border:1px solid #dce4f1;border-radius:9px;background:#fff;color:var(--ink);padding:10px 16px;min-width:170px}.fine{margin-left:auto;color:#75849d;font-size:12px;align-self:center}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:17px;margin-bottom:21px}.kpi{padding:23px;background:var(--card);border:1px solid var(--line);border-radius:15px;box-shadow:0 3px 13px rgba(38,60,97,.025)}
.kpi .label{font-size:12px;color:var(--muted);margin-bottom:15px}.kpi .value{font-weight:780;font-size:28px;letter-spacing:-.8px}.kpi .hint{font-size:11px;color:#9aa7ba;margin-top:11px}
.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:17px}.tile{background:white;border:1px solid var(--line);border-radius:15px;padding:21px 20px 10px;min-width:0}.tile.wide{grid-column:1/-1}
.tile h2{font-size:16px;letter-spacing:-.2px;margin:0 0 3px}.tile p{font-size:12px;color:var(--muted);margin:0 0 8px}.plot{height:315px}.plot.tall{height:370px}
.view{display:none}.view.active{display:block}.notice{margin-top:20px;padding:17px 19px;background:#eaf0ff;border:1px solid #dce6ff;color:#526b9c;font-size:12px;line-height:1.7;border-radius:11px}
@media(max-width:1040px){.shell{grid-template-columns:1fr}.side{padding:17px;gap:9px}.sidefoot{display:none}.nav{flex-direction:row;flex-wrap:wrap}.content{padding:25px}.kpis{grid-template-columns:repeat(2,1fr)}}
@media(max-width:660px){.content{padding:15px}.grid{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr;gap:9px}.kpi{padding:16px}.kpi .value{font-size:21px}.tile.wide{grid-column:auto}.header{flex-wrap:wrap}h1{font-size:24px}.filters{gap:10px}.filters select{min-width:125px}}
</style>
</head><body><div class="shell"><aside class="side"><div><div class="logo">INDUSTRIAL<span> / BI</span></div><div class="caption">ENERGY INTELLIGENCE</div></div>
<nav class="nav"><button class="active" data-tab="overview">◫ &nbsp; Обзор</button><button data-tab="profile">◷ &nbsp; Профиль нагрузки</button><button data-tab="costs">▥ &nbsp; Модель затрат</button></nav>
<div class="sidefoot">Portfolio project · BI / DWH / ETL<br/>PostgreSQL-ready schema · SQL · Python<br/>Тарифы — учебные сценарии</div></aside>
<main class="content"><div class="header"><div><h1>Industrial Energy Analytics</h1><p class="subtitle">Мониторинг энергопотребления металлургического предприятия · Данные с интервалом 15 минут</p></div><div class="tag">__SUBTITLE__</div></div>
<section class="filters"><label>Период<select id="month"><option value="all">Все месяцы</option>__OPTIONS__</select></label>
<label>Тип нагрузки<select id="load"><option value="all">Все типы</option><option value="0">Light Load</option><option value="1">Medium Load</option><option value="2">Maximum Load</option></select></label>
<div class="fine" id="filterCount"></div></section>
<section class="kpis"><div class="kpi"><div class="label">Энергопотребление</div><div class="value" id="total">—</div><div class="hint">Сумма интервальных кВт·ч</div></div>
<div class="kpi"><div class="label">Среднее за 15 минут</div><div class="value" id="avg">—</div><div class="hint">Среднее потребление на интервал</div></div>
<div class="kpi"><div class="label">Максимум за 15 минут</div><div class="value" id="peak">—</div><div class="hint">Это энергия за интервал, не мощность кВт</div></div>
<div class="kpi"><div class="label">Расчётные затраты</div><div class="value" id="cost">—</div><div class="hint">₩ · синтетические тарифы</div></div></section>
<section id="overview" class="view active"><div class="grid">
<div class="tile wide"><h2>Динамика энергопотребления</h2><p>Объём потребления по дням, кВт·ч</p><div class="plot tall" id="daily"></div></div>
<div class="tile"><h2>Распределение по типам нагрузки</h2><p>Энергия за выбранный период, кВт·ч</p><div class="plot" id="loadBars"></div></div>
<div class="tile"><h2>Рабочие и выходные</h2><p>Среднее за 15-минутный интервал, кВт·ч</p><div class="plot" id="weekBars"></div></div></div></section>
<section id="profile" class="view"><div class="grid"><div class="tile wide"><h2>Тепловая карта энергопотребления</h2><p>Среднее кВт·ч на 15-минутный интервал · день недели × час</p><div class="plot tall" id="heatmap"></div></div>
<div class="tile"><h2>Средний суточный профиль</h2><p>Среднее на 15-минутный интервал по часам</p><div class="plot" id="hourChart"></div></div>
<div class="tile"><h2>Пиковые интервалы</h2><p>Пять временных отметок с наибольшим энергопотреблением</p><div class="plot" id="peaks"></div></div></div></section>
<section id="costs" class="view"><div class="grid"><div class="tile wide"><h2>Оценка расходов по месяцам</h2><p>Условная тарификация · в корейских вонах (KRW)</p><div class="plot tall" id="costMonths"></div></div>
<div class="tile"><h2>Структура модельных расходов</h2><p>По типам нагрузки · KRW</p><div class="plot" id="costBars"></div></div>
<div class="tile"><h2>Допущения тарификации</h2><p>Фиксированные учебные тарифы (не счета предприятия)</p><div style="padding:30px 8px;line-height:2.5;font-size:15px"><b>Light Load</b> — ₩95 / кВт·ч<br/><b>Medium Load</b> — ₩125 / кВт·ч<br/><b>Maximum Load</b> — ₩165 / кВт·ч</div></div></div></section>
<div class="notice">Источник: __SOURCE_DETAIL__. Гранулярность — 1 измерение / 15 минут. Отображение стоимости — исключительно учебный расчёт, а не подтверждённые расходы. При загрузке UCI-датасета отчёт пересоздаётся командой <code>python -m src.build_report</code>.</div>
</main></div>
<script>__PLOTLY_JS__</script>
<script>
'use strict';
const ROWS = __ROWS__;
const typeNames = ['Light Load','Medium Load','Maximum Load'];
const colors = ['#3659d6','#0e9fa9','#f06b80'];
const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
const baseLayout = {font:{family:'Inter, Segoe UI, sans-serif',size:12,color:'#66748d'},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',margin:{l:50,r:18,t:18,b:46},showlegend:false,hoverlabel:{bgcolor:'#1c2e4e'},xaxis:{showgrid:false,linecolor:'#dde5ef'},yaxis:{gridcolor:'#e9eef6',zeroline:false}};
const cfg = {responsive:true,displayModeBar:false};
const fmt = x => Math.round(x).toLocaleString('ru-RU');
const fmt1 = x => (Math.round(x*10)/10).toLocaleString('ru-RU');
function plot(id,data,changes={}) { Plotly.react(id,data,{...baseLayout,...changes},cfg); }
function regroup(rows,key, valueIndex=6) {const x=new Map(); for (const r of rows){const k=key(r);x.set(k,(x.get(k)||0)+r[valueIndex]);} return x;}
function redraw(){
 const month=document.getElementById('month').value, load=document.getElementById('load').value;
 const filtered=ROWS.filter(r=>(month==='all'||r[0].startsWith(month)) && (load==='all'||r[5]===Number(load)));
 document.getElementById('filterCount').textContent=fmt(filtered.length)+' интервалов';
 const total=filtered.reduce((a,r)=>a+r[6],0), cost=filtered.reduce((a,r)=>a+r[7],0), peak=Math.max(0,...filtered.map(r=>r[6]));
 document.getElementById('total').textContent=fmt(total)+' кВт·ч';
 document.getElementById('avg').textContent=fmt1(total/Math.max(1,filtered.length))+' кВт·ч';
 document.getElementById('peak').textContent=fmt1(peak)+' кВт·ч';
 document.getElementById('cost').textContent='₩'+fmt(cost);
 const daily=regroup(filtered,r=>r[0]); const sortedDays=[...daily.keys()].sort();
 plot('daily',[{x:sortedDays,y:sortedDays.map(k=>daily.get(k)),type:'scatter',mode:'lines',line:{color:colors[0],width:3},fill:'tozeroy',fillcolor:'rgba(54,89,214,.09)',hovertemplate:'%{x}<br>%{y:,.1f} кВт·ч<extra></extra>'}],{xaxis:{type:'date',showgrid:false},yaxis:{gridcolor:'#e9eef6',title:'кВт·ч'}});
 const byLoad=regroup(filtered,r=>r[5]); plot('loadBars',[{x:typeNames,y:[0,1,2].map(k=>byLoad.get(k)||0),type:'bar',marker:{color:colors},hovertemplate:'%{x}<br>%{y:,.1f} кВт·ч<extra></extra>'}],{margin:{l:55,r:20,t:15,b:70},yaxis:{gridcolor:'#e9eef6',title:'кВт·ч'}});
 const week=[0,1].map(w=>filtered.filter(r=>r[4]===w)); plot('weekBars',[{x:['Рабочие','Выходные'],y:week.map(g=>g.reduce((a,r)=>a+r[6],0)/Math.max(1,g.length)),type:'bar',marker:{color:['#3659d6','#0e9fa9']}}],{yaxis:{gridcolor:'#e9eef6',title:'кВт·ч'}});
 const z=Array.from({length:7},()=>Array.from({length:24},()=>0)),n=Array.from({length:7},()=>Array.from({length:24},()=>0));
 filtered.forEach(r=>{z[r[3]-1][r[1]]+=r[6];n[r[3]-1][r[1]]++});
 plot('heatmap',[{z:z.map((a,i)=>a.map((v,h)=>n[i][h]?v/n[i][h]:null)),x:Array.from({length:24},(_,i)=>String(i).padStart(2,'0')+':00'),y:days,type:'heatmap',colorscale:[[0,'#eaf3fd'],[.5,'#77b9da'],[1,'#3659d6']],hovertemplate:'%{y} %{x}<br>%{z:.1f} кВт·ч<extra></extra>',colorbar:{title:'кВт·ч',thickness:12}}],{margin:{l:45,r:25,t:15,b:53}});
 const hourly=Array.from({length:24},(_,h)=>filtered.filter(r=>r[1]===h));
 plot('hourChart',[{x:hourly.map((_,h)=>String(h).padStart(2,'0')),y:hourly.map(g=>g.reduce((s,r)=>s+r[6],0)/Math.max(1,g.length)),type:'scatter',mode:'lines+markers',line:{color:colors[1],width:3}}],{yaxis:{gridcolor:'#e9eef6',title:'кВт·ч'},xaxis:{title:'Час'}});
 const top=[...filtered].sort((a,b)=>b[6]-a[6]).slice(0,5).reverse();
 plot('peaks',[{y:top.map(r=>r[0]+' '+String(r[1]).padStart(2,'0')+':'+String(r[2]).padStart(2,'0')),x:top.map(r=>r[6]),orientation:'h',type:'bar',marker:{color:colors[2]}}],{margin:{l:120,r:20,t:15,b:40},xaxis:{title:'кВт·ч'}});
 const costMonth=regroup(filtered,r=>r[0].slice(0,7),7);const cm=[...costMonth.keys()].sort();
 plot('costMonths',[{x:cm,y:cm.map(k=>costMonth.get(k)),type:'bar',marker:{color:'#3659d6'},hovertemplate:'%{x}: ₩%{y:,.0f}<extra></extra>'}],{yaxis:{gridcolor:'#e9eef6',title:'₩'},xaxis:{type:'category'}});
 const costType=regroup(filtered,r=>r[5],7);
 plot('costBars',[{x:typeNames,y:[0,1,2].map(k=>costType.get(k)||0),type:'bar',marker:{color:colors}}],{margin:{l:55,r:20,t:15,b:70},yaxis:{gridcolor:'#e9eef6',title:'₩'}});
}
for (const id of ['month','load']) document.getElementById(id).addEventListener('change',redraw);
document.querySelectorAll('[data-tab]').forEach(btn=>btn.addEventListener('click',()=>{
 document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===btn));
 document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active',el.id===btn.dataset.tab));
 for (const chart of document.querySelectorAll('.view.active .plot')) Plotly.Plots.resize(chart);
}));
redraw();
</script></body></html>'''
    html = html.replace('__SUBTITLE__', escape(subtitle)).replace('__SOURCE_DETAIL__', escape(source.get('source_url', '?')))
    html = html.replace('__OPTIONS__', opts).replace('__PLOTLY_JS__', get_plotlyjs()).replace('__ROWS__', js_rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    print(f'Автономный интерактивный отчёт: {output} ({output.stat().st_size / 1024**2:.1f} MB)')
    return output


if __name__ == '__main__':
    build_report()
