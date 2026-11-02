-- Industrial Energy BI: примеры аналитических SQL-запросов.
-- SQLite: подходят для локальной базы data/warehouse/industrial_bi.sqlite.
-- Энергия за 15 минут (кВт·ч) не равна пиковой мощности (кВт).

-- 1. Сводные KPI: агрегация.
SELECT COUNT(*) AS readings,
       ROUND(SUM(usage_kwh), 2) AS total_kwh,
       ROUND(AVG(usage_kwh), 2) AS avg_15min_kwh,
       ROUND(MAX(usage_kwh), 2) AS max_15min_kwh,
       ROUND(SUM(estimated_cost_krw), 2) AS illustrative_cost_krw
FROM vw_energy_enriched;

-- 2. Энергопотребление по месяцам: GROUP BY + LAG (оконная функция).
WITH months AS (
    SELECT year_num, month_num, SUM(usage_kwh) AS energy_kwh
    FROM vw_energy_enriched
    GROUP BY year_num, month_num
), compared AS (
    SELECT *, LAG(energy_kwh) OVER (ORDER BY year_num, month_num) AS prev_month_kwh
    FROM months
)
SELECT year_num, month_num, ROUND(energy_kwh, 2) AS energy_kwh,
       ROUND(prev_month_kwh, 2) AS prev_month_kwh,
       ROUND(100.0 * (energy_kwh - prev_month_kwh) / NULLIF(prev_month_kwh, 0), 2) AS mom_pct
FROM compared ORDER BY year_num, month_num;

-- 3. Сравнение средних интервальных значений по дням недели.
SELECT weekday_num, weekday_name, COUNT(*) AS readings,
       ROUND(AVG(usage_kwh), 2) AS avg_kwh_per_15min,
       ROUND(SUM(usage_kwh), 2) AS total_kwh
FROM vw_energy_enriched
GROUP BY weekday_num, weekday_name ORDER BY weekday_num;

-- 4. Пять самых энергоёмких интервалов: подзапрос + сортировка.
SELECT timestamp_local, load_type, usage_kwh
FROM (
    SELECT timestamp_local, load_type, usage_kwh
    FROM vw_energy_enriched
    WHERE usage_kwh > (SELECT AVG(usage_kwh) FROM fact_energy_readings)
) q
ORDER BY usage_kwh DESC, timestamp_local LIMIT 5;

-- 5. Пиковые значения внутри каждого типа нагрузки: ROW_NUMBER.
WITH ranked AS (
    SELECT load_type, timestamp_local, usage_kwh,
           ROW_NUMBER() OVER (PARTITION BY load_type ORDER BY usage_kwh DESC, timestamp_local) AS rn
    FROM vw_energy_enriched
)
SELECT load_type, timestamp_local, usage_kwh
FROM ranked WHERE rn <= 3 ORDER BY load_type, rn;

-- 6. Стоимость по типу нагрузки: JOIN таблиц DWH.
SELECT l.load_type, COUNT(*) AS readings,
       ROUND(SUM(f.usage_kwh), 2) AS total_kwh,
       l.demo_tariff_krw_kwh,
       ROUND(SUM(f.usage_kwh * l.demo_tariff_krw_kwh), 2) AS estimated_cost_krw
FROM fact_energy_readings f
JOIN dim_load_type l ON l.load_type_key = f.load_type_key
GROUP BY l.load_type, l.demo_tariff_krw_kwh ORDER BY estimated_cost_krw DESC;

-- 7. Контроль качества: сверка staging и витрины.
SELECT (SELECT COUNT(*) FROM stg_energy_readings) AS stg_rows,
       (SELECT COUNT(*) FROM fact_energy_readings) AS fact_rows,
       (SELECT ROUND(SUM(usage_kwh), 2) FROM stg_energy_readings) AS stg_kwh,
       (SELECT ROUND(SUM(usage_kwh), 2) FROM fact_energy_readings) AS fact_kwh;
