"""Regenerate synthetic examples; never use production credentials or records."""
from pathlib import Path
import sys
from uuid import UUID
from zipfile import ZipFile, ZIP_DEFLATED

from spg.evaluation.work_diagnostic_export import FILES
sys.path.insert(0, str(Path(__file__).parents[3] / 'tests'))
from test_work_diagnostic_export import service


def main():
    output = Path(__file__).parent / 'samples'
    output.mkdir(exist_ok=True)
    exporter, _ = service()
    work_id = UUID('00000000-0000-4000-8000-000000000001')
    product_id = UUID('00000000-0000-4000-8000-000000000002')
    exporter.registry.expected = work_id
    owner_get = exporter.registry.get
    def stable_owner(owner, selected):
        row = owner_get(owner, selected)
        row['product_id'] = str(product_id)
        return row
    exporter.registry.get = stable_owner
    for mode in ('compact', 'full'):
        files = exporter.capture('human:owner', work_id, mode=mode)
        folder = output / mode
        folder.mkdir(exist_ok=True)
        for name, content in files.items():
            (folder / name).write_bytes(content)
        with ZipFile(output / f'watt-work-{work_id}-{mode}-diagnostic.zip', 'w',
                     compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for name in FILES:
                archive.writestr(name, files[name])
    print(f'SYNTHETIC_SAMPLE_WORK_ID={work_id}')


if __name__ == '__main__':
    main()
