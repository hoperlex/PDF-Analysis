"""Rebuild synthetic presentation inputs; no application/model/network calls."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/fixtures'))

from portal_bundle import bundle, validate
from portal_bundle.blocklist import Block, ImageNote
from portal_bundle.committed import baseline_full
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


def plain_zip(name: str, members: list[tuple[str, Path]]) -> None:
    with zipfile.ZipFile(OUT / name, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for display, source in members:
            info = zipfile.ZipInfo(display, (2026, 10, 30, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, source.read_bytes())


def eom_pdf() -> bytes:
    font = ROOT / 'tools/fixtures/assets/ARCorpusSans.ttf'
    pdfmetrics.registerFont(TTFont('DemoDejaVu', str(font)))
    output = io.BytesIO(); canvas = Canvas(output, pagesize=(595, 842), invariant=1, initialFontName='DemoDejaVu', pageCompression=0)
    canvas.setTitle('СИНТ-ЭОМ: native text and synthetic electrical diagram')
    canvas.setFont('DemoDejaVu', 12)
    lines = [
        'СИНТ-ЭОМ. Электроснабжение. Демонстрационный набор.',
        'Синтетический документ, не проект и не нормативное заключение.',
        'Учебная схема питания помещения. Напряжение сети 400/230 В.',
        'Заявленная мощность оборудования 12 кВт. Таблица групп ниже.',
        'Группа 1: освещение, нагрузка 1,2 кВт, автомат 10 А.',
        'Группа 2: розетки, нагрузка 3,5 кВт, автомат 16 А.',
        'Группа 3: оборудование, нагрузка 7,3 кВт, автомат 25 А.',
        'Кабель группы 2: медный, 3 x 2,5 мм2; длина 20 м.',
        'Выбор сечений и защит требует расчёта и проверки инженером.',
        'Нормативные ссылки намеренно не включены.',
    ]
    for index, line in enumerate(lines): canvas.drawString(38, 790 - index * 24, line)
    canvas.setFont('DemoDejaVu', 10)
    canvas.rect(65, 220, 460, 175)
    canvas.drawString(80, 375, 'Учебная однолинейная схема — IMAGE область портала')
    canvas.line(90, 320, 490, 320)
    for x, label in [(150, 'QF1 10 A'), (290, 'QF2 16 A'), (430, 'QF3 25 A')]:
        canvas.line(x, 320, x, 275); canvas.rect(x - 12, 284, 24, 20)
        canvas.drawString(x - 30, 250, label)
    canvas.save(); return output.getvalue()


def main() -> None:
    provenance = {'synthetic': True, 'task': 'HOTFIX-PRESENTATION-DEMO-1030', 'sources': {}, 'bundles': {}}
    font = ROOT / 'tools/fixtures/assets/ARCorpusSans.ttf'
    provenance['sources'][str(font.relative_to(ROOT))] = hashlib.sha256(font.read_bytes()).hexdigest()
    vs = [(f'VS1/v{i}.pdf', ROOT / f'fixtures/comparison/vs1/v{i}.pdf') for i in range(1, 6)]
    old = [('SP1/П/old_p.pdf', ROOT / 'fixtures/comparison/sp1/old_p.pdf')]
    new = [(f'SP1/Р/new_r{i}.pdf', ROOT / f'fixtures/comparison/sp1/new_r{i}.pdf') for i in range(1, 4)]
    plain_zip('VS1-five-versions.zip', vs)
    plain_zip('SP1-OLD.zip', old)
    plain_zip('SP1-NEW.zip', new)
    graphic = ROOT / 'tests/e2e/pc01/journey/fixtures/sp1-new-r2-graphic.pdf'
    plain_zip('SP1-NEW-graphic-derivative.zip', [(display, graphic if display.endswith('new_r2.pdf') else source) for display, source in new])
    for _, source in [*vs, *old, *new, ('graphic', graphic)]:
        provenance['sources'][str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    ar = baseline_full((ROOT / 'fixtures/synthetic/ar/ar_baseline.pdf').read_bytes())
    ar_zip = bundle.build_bundle(ar)
    (OUT / 'AR-native-image-portal.zip').write_bytes(ar_zip.data)
    provenance['sources']['fixtures/synthetic/ar/ar_baseline.pdf'] = hashlib.sha256(ar.pdf).hexdigest()
    previous = bundle.DISPLAY_PATH
    try:
        bundle.DISPLAY_PATH = 'Синтетический набор / [ЭОМ] Электроснабжение / {stem}'
        eom = bundle.make_files(eom_pdf(), 'eom_native_image', extra_blocks=[Block('image', 0, (0.10, 0.50, 0.90, 0.76),
            image=ImageNote('Схема', (), 'Синтетическая однолинейная схема групп питания.',
                            'Векторные линии и аппараты на исходной PDF странице; учебный пример, не проект.', ('QF1', 'QF2', 'QF3')))])
    finally:
        bundle.DISPLAY_PATH = previous
    (OUT / 'EOM-native-image-portal.zip').write_bytes(bundle.build_bundle(eom).data)
    for name, files in [('AR-native-image-portal.zip', ar), ('EOM-native-image-portal.zip', eom)]:
        verdict = validate.validate((OUT / name).read_bytes(), bundle.GENERATOR_LIMITS)
        assert verdict.accepted, verdict
        kinds = {kind: sum(block.kind == kind for block in files.blocks) for kind in ('text', 'image')}
        assert kinds['text'] >= 1 and kinds['image'] >= 1
        provenance['bundles'][name] = {'pages': files.page_count, 'blocks': kinds, 'portal_validator': 'accepted',
                                    'pdf_sha256': hashlib.sha256(files.pdf).hexdigest(), 'live_analysis': 'UNVERIFIED'}
    for archive in sorted(OUT.glob('*.zip')):
        with zipfile.ZipFile(archive) as opened:
            assert opened.testzip() is None
            if archive.name.startswith(('VS1', 'SP1')):
                assert all(member.filename.lower().endswith('.pdf') for member in opened.infolist())
    (OUT / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(OUT.glob('*.zip'))))
    print(json.dumps({'archives': len(list(OUT.glob('*.zip'))), 'portal_inputs': provenance['bundles']}, ensure_ascii=False))


if __name__ == '__main__': main()
