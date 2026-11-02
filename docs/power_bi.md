# Power BI — подключение DWH и готовые DAX-меры

> `.pbix` не вложен: это проприетарный бинарный формат, который здесь не собирался. Файлы витрин `data/processed/*.csv` и готовые DAX-меры включены, поэтому отчёт можно собрать локально в Power BI Desktop.

## 1. Загрузка

Откройте **Power BI Desktop** → **Get Data / Text CSV** → загрузите следующие файлы:

- `data/processed/dim_date.csv`
- `data/processed/dim_time.csv`
- `data/processed/dim_load_type.csv`
- `data/processed/fact_energy_readings.csv`

Staging-таблица для отчёта не нужна. Проверьте типы (ключи — Whole Number, `full_date` — Date, `usage_kwh` — Decimal Number, `timestamp_local` — Date/Time). Отключите автоматические отношения, если Power BI создаст неверные связи.

## 2. Звезда

Создайте **односторонние** отношения 1:*:

- `dim_date[date_key]` → `fact_energy_readings[date_key]`
- `dim_time[time_key]` → `fact_energy_readings[time_key]`
- `dim_load_type[load_type_key]` → `fact_energy_readings[load_type_key]`

Для сортировки дней недели используйте `dim_date[weekday_num]`; месяц удобнее строить как `year_num` + `month_num`, чтобы не сливались разные годы. Установите правильные числовые форматы и единицы.

## 3. DAX: копируйте в New Measure

```dax
Total Energy (kWh) =
SUM(fact_energy_readings[usage_kwh])

Average 15-min Energy (kWh) =
AVERAGE(fact_energy_readings[usage_kwh])

Peak 15-min Energy (kWh) =
MAX(fact_energy_readings[usage_kwh])

Reading Count =
COUNTROWS(fact_energy_readings)

Illustrative Cost (KRW) =
SUMX(
    fact_energy_readings,
    fact_energy_readings[usage_kwh] *
    RELATED(dim_load_type[demo_tariff_krw_kwh])
)

Energy Share % =
DIVIDE(
    [Total Energy (kWh)],
    CALCULATE(
        [Total Energy (kWh)],
        REMOVEFILTERS(dim_load_type)
    )
)
```

`Energy Share %` показывает долю внутри выбранного периода при снятии только фильтра типа нагрузки; если выбраны сразу несколько типов, знаменатель охватывает все три категории.

## 4. Три страницы отчёта

**Overview:** 4 карточки KPI, line chart `dim_date[full_date]` → Total Energy, bar chart `dim_load_type[load_type]` → Total Energy, slicer Date, slicer Load Type.

**Consumption Profile:** matrix/heatmap `weekday_name` × `hour_num` с мерой Average 15-min Energy, chart по часам, таблица топ интервалов.

**Cost Analytics:** histogram расходов по месяцам, stacked bar по категориям, блок с предупреждением «Модельные тарифы, не бухгалтерский факт».

## 5. Сверка

Сумма KPI в Power BI до фильтров должна совпасть с `SELECT SUM(usage_kwh) FROM fact_energy_readings`. При фильтре по типу аналогично сверить с `sql/01_analytics.sql`.
