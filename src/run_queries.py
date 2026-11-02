"""Запускает SQL-примеры и печатает результаты в терминал.

python -m src.run_queries
"""
import sqlite3
from src.config import ROOT, WAREHOUSE


def main():
    sql_path = ROOT / 'sql' / '01_analytics.sql'
    with sqlite3.connect(WAREHOUSE) as conn:
        conn.row_factory = sqlite3.Row
        fragment = ''
        count = 0
        for line in sql_path.read_text(encoding='utf-8').splitlines(keepends=True):
            fragment += line
            if sqlite3.complete_statement(fragment):
                if fragment.strip().lstrip('-').strip():
                    count += 1
                    cur = conn.execute(fragment)
                    names = [col[0] for col in cur.description]
                    values = cur.fetchall()
                    print(f'\n--- SQL запрос #{count} ---')
                    print(' | '.join(names))
                    for row in values[:15]:
                        print(' | '.join(str(x) for x in row))
                    if len(values) > 15:
                        print(f'... ещё {len(values)-15} строк')
                fragment = ''
        print(f'\nВыполнено SQL-запросов: {count}')


if __name__ == '__main__':
    main()
