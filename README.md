# ⚡ Industrial Energy BI — аналитическая система для производства

**Учебный pet-проект для стажировки BI / Big Data аналитика:** сбор требований → анализ источника → DWH (звезда) → ETL → SQL → интерактивный отчёт → тестирование и документация.

> **Статус:** рабочий end-to-end прототип. Готовый автономный HTML-отчёт, SQLite-хранилище и CSV-витрины уже включены в архив. Для настоящих измерений предусмотрен загрузчик UCI. Файл Power BI `.pbix` не включён; DAX и инструкция по сборке Power BI-отчёта приведены отдельно.

![Иллюстрация дашборда на демонстрационных данных](assets/dashboard_preview.png)

*Иллюстрация интерфейса, построенная по синтетическим измерениям; не скриншот браузера.*

## 🚀 Посмотреть результат за 10 секунд

1. Распакуйте архив.
2. Откройте **`dashboard/report.html` двойным щелчком** — браузер покажет интерактивный отчёт **без Python, интернета и установки зависимостей**.
3. В отчёте работают фильтры по месяцу и типу нагрузки, 3 аналитические страницы, KPI и графики.

**Важное уточнение:** прилагаемые данные **синтетические** (8 640 измерений, 90 дней 2025 года). Они нужны, чтобы отчёт работал сразу. Это *не* исходный набор UCI. Все условные тарифы (₩95/125/165 за кВт·ч) придуманы для расчётного сценария и не отражают реальные затраты компании. Для реальных данных — инструкция ниже.

## 🧩 Что реализовано

- **Бизнес-анализ:** BRD с требованиями, ролями, бизнес-вопросами, критериями приёмки и допущениями; отдельное ТЗ, постановка задач разработчику.
- **ETL:** типизация, очистка категорий, проверка пропусков, дублей, согласованности дня недели, 15-минутной дискретности, негативных показателей и сверка сумм.
- **DWH:** измерения `dim_date`, `dim_time`, `dim_load_type` и факты `fact_energy_readings`; staging, витрина `vw_energy_enriched`.
- **SQL:** агрегации, JOIN, подзапрос, CTE, `LAG()`, `ROW_NUMBER()`, проверочные запросы.
- **BI:** автономный Plotly-HTML + опциональный Streamlit; 3 вкладки («Обзор», «Профиль нагрузки», «Модель затрат»).
- **Тестирование:** 8 pytest-тестов, контроль итоговых показателей, ручные чек-листы.
- **PostgreSQL:** DDL с FK/PK и COPY-загрузчик. SQLite работает без внешнего сервера и нужен для моментального демо.
- **Power BI:** пять готовых CSV-таблиц, DAX-меры, руководство по настройке отношений и отчёта (в `docs/power_bi.md`).

## 📁 Структура проекта

```text
industrial-energy-bi/
├── dashboard/
│   ├── report.html              # ГОТОВЫЙ автономный BI-отчёт: откройте в браузере
│   └── app.py                   # интерактивное приложение Streamlit
├── data/
│   ├── raw/Steel_industry_data.csv     # СИНТЕТИЧЕСКОЕ демо; можно заменить на UCI
│   ├── processed/               # CSV-витрины для Power BI и PostgreSQL
│   └── warehouse/industrial_bi.sqlite  # ГОТОВОЕ локальное DWH
├── src/
│   ├── generate_demo.py         # генератор демо-данных
│   ├── download_uci.py          # загрузка настоящего датасета
│   ├── etl.py                   # очистка, DWH, экспорт витрин
│   ├── load_postgres.py         # загрузка в PostgreSQL
│   ├── build_report.py          # генерация автономного отчёта
│   └── config.py
├── sql/
│   ├── 01_analytics.sql         # аналитические и проверочные запросы
│   └── 02_postgresql_schema.sql # модель DWH PostgreSQL
├── docs/                       # требования, ТЗ, словарь, тесты, DAX и т.д.
├── tests/test_etl.py
├── .github/workflows/tests.yml
├── requirements.txt
└── README.md
```

## 🖥 Запуск на Windows (PowerShell)

Запускайте команды из папки `industrial-energy-bi`. Подходит Python 3.10+ (желательно 3.11–3.12).

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m src.etl --source demo
.\.venv\Scripts\python.exe -m src.run_queries
.\.venv\Scripts\python.exe -m src.build_report
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

> При ошибке PowerShell `npm.ps1` или блокировке активации окружения ничего активировать не нужно: команды выше запускают `.venv\Scripts\python.exe` напрямую.

**Минимальный запуск без Streamlit:** `py -m pip install pandas numpy plotly pytest`, затем `py -m src.etl --source demo` и `py -m src.build_report`; после этого откройте `dashboard/report.html`.

### 🔁 Загрузить настоящие данные UCI

Официальный датасет: [Steel Industry Energy Consumption — UCI](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption), 35 040 наблюдений за 2018 год, лицензия CC BY 4.0.

```powershell
.\.venv\Scripts\python.exe -m src.download_uci --replace
.\.venv\Scripts\python.exe -m src.etl --source uci
.\.venv\Scripts\python.exe -m src.build_report
```

После загрузки исходных 35 040 строк в заголовке отчёта будет написано «РЕАЛЬНЫЕ ИЗМЕРЕНИЯ UCI · 2018 год». Без доступа к Интернету скачайте CSV через браузер и положите его в `data/raw/Steel_industry_data.csv`, затем выполните последние две команды. Источник менять в существующем Git-коммите лучше отдельным осознанным коммитом.

### PostgreSQL (не требуется для просмотра демо)

Создайте собственную тестовую базу данных. Для локальной учебной среды можно (при установленном Docker) выполнить `docker compose up -d`, используя `compose.yaml`. В этом случае тестовая строка подключения: `postgresql://energybi:energybi_demo_only@localhost:5432/industrial_bi` (пароль только для локального демо). Затем после ETL:

```powershell
.\.venv\Scripts\python.exe -m src.load_postgres --dsn "postgresql://postgres:YOUR_PASSWORD@localhost:5432/industrial_bi"
```

DDL: `sql/02_postgresql_schema.sql`. Скрипт повторной загрузки **очищает только таблицы проекта внутри схемы `industrial_bi`**, поэтому запускайте его исключительно в учебной БД. Для локального демо используется SQLite; выполнение PostgreSQL-загрузчика против запущенного внешнего сервера автором примера не проверялось.

## 📈 KPI и правила расчётов

| Метрика | Правило | Комментарий |
|---|---|---|
| Потребление | `SUM(usage_kwh)` | Сумма энергии за 15-минутные интервалы, кВт·ч |
| Среднее за 15 мин | `AVG(usage_kwh)` | Не средняя мощность, единица кВт·ч |
| Пиковый интервал | `MAX(usage_kwh)` | Максимальное потребление за 15 минут, не мощность кВт |
| Условные расходы | `SUM(usage_kwh * tariff)` | Учебная модель в KRW, не счёт за электричество |
| Разрез по типам | `GROUP BY load_type` | Light / Medium / Maximum Load |
| Динамика по месяцам | `SUM(usage_kwh)` + `LAG()` | MoM только для полного или явно выбранного периода |

Показатель `CO2(tCO2)` в источнике имеет несогласованное описание единиц; в проекте он сохранён как `co2_source_value` **без интерпретации как тонны или ppm**. Это отражено в Data Dictionary.

## 📋 Документы аналитика

- [`docs/business_requirements.md`](docs/business_requirements.md) — требования и «интервью» с условным заказчиком.
- [`docs/technical_spec.md`](docs/technical_spec.md) — техническая постановка, правила фильтрации, критерии приёмки.
- [`docs/data_dictionary.md`](docs/data_dictionary.md) — поля и гранулярность DWH.
- [`docs/etl_spec.md`](docs/etl_spec.md) — источник → трансформации → приёмники, качество данных.
- [`docs/bpmn_process.md`](docs/bpmn_process.md) — AS-IS / TO-BE бизнес-процесс.
- [`docs/test_cases.md`](docs/test_cases.md) — тест-кейсы, проверка SQL и BI.
- [`docs/power_bi.md`](docs/power_bi.md) — Power BI, отношения модели и DAX.
- [`docs/interview_and_cv.md`](docs/interview_and_cv.md) — описание проекта для резюме, план демонстрации на собеседовании.
- [`docs/findings_demo.md`](docs/findings_demo.md) — проверенные результаты на **синтетическом** демо-наборе.

## Границы решения и честность кейса

Это **проект для портфолио**, а не заказ реальной компании. Бизнес-цели и тарифы — учебные гипотезы; требования нельзя считать согласованными с реальным заказчиком. Данные UCI отражают одно предприятие; в наборе нет идентификаторов отдельных цехов и реальных счетов, поэтому анализ по цехам и точный расчёт себестоимости **не реализованы**. 35 040 наблюдений — небольшой объём, поэтому «Big Data на кластере» не заявляется. Реализован именно BI + DWH прототип с промышленной предметной областью.

## Источник и лицензия

Sathishkumar V E, Changsun Shin, Yongyun Cho (2021). *Steel Industry Energy Consumption* [Dataset]. UCI Machine Learning Repository. DOI: [10.24432/C52G8C](https://doi.org/10.24432/C52G8C). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Здесь включён только отдельно сгенерированный синтетический набор; оригинал можно скачать загрузчиком. При дальнейшем распространении исходных данных необходимо сохранять атрибуцию.

**Авторство:** шаблон и код созданы для учебного портфолио; перед публикацией на GitHub изучите код и адаптируйте постановку/выводы к тому, что сможете объяснить сами.
