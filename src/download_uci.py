"""Скачивает и распаковывает реальный датасет UCI CC BY 4.0.

Команда: python -m src.download_uci --replace
После этого выполните ETL и пересоздайте отчёт.
"""
import argparse
import io
import urllib.request
import zipfile
from src.config import ARCHIVE_URL, RAW


def download(replace: bool = False):
    if RAW.exists() and not replace:
        raise FileExistsError(f'{RAW} уже существует. Используйте --replace.')
    request = urllib.request.Request(ARCHIVE_URL, headers={'User-Agent': 'industrial-energy-bi-demo/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        target = next((x for x in archive.namelist() if x.lower().endswith('steel_industry_data.csv')), None)
        if not target:
            raise ValueError('CSV не найден внутри архива UCI')
        data = archive.read(target)
    # Не заменять существующий источник, пока архив не проверен.
    if b'Usage_kWh' not in data[:1000] or len(data) < 100_000:
        raise ValueError('Неожиданный формат архива / CSV')
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_bytes(data)
    print(f'Реальные данные UCI сохранены: {RAW} ({len(data):,} bytes)')
    print('Источник: UCI Steel Industry Energy Consumption, DOI 10.24432/C52G8C, CC BY 4.0')
    print('Дальше: python -m src.etl --source uci && python -m src.build_report')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--replace', action='store_true', help='заменить демонстрационный CSV')
    download(parser.parse_args().replace)
