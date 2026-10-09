"""Optional real Edge smoke test against tests/browser_diagnostic_app.py."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from playwright.sync_api import sync_playwright


def main(url):
    edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=edge, headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        calls = []
        page.on('request', lambda request: calls.append(request.url))
        page.goto(url+'/admin/works')
        button = page.get_by_role('button', name='导出 AI 诊断包')
        button.wait_for()
        assert page.get_by_text('Browser fixture DESIGN Work').count() >= 1
        assert not any('/api/admin/traces/' in call for call in calls)
        work_id = button.get_attribute('data-diagnostic-work')
        with page.expect_download() as transfer:
            button.click()
        download = transfer.value
        assert download.suggested_filename == f'watt-work-{work_id}-diagnostic.zip'
        with ZipFile(download.path()) as archive:
            manifest = json.loads(archive.read('evidence-manifest.json'))
            trace = json.loads(archive.read('trace.json'))
        assert manifest['work_id'] == trace['work_id'] == work_id
        assert trace['lifecycle']['units'] == []
        page.get_by_role('button', name='查看 Trace').click()
        page.get_by_role('button', name='完整证据包').wait_for()
        with page.expect_download() as transfer:
            page.get_by_role('button', name='下载 report.md').click()
        assert transfer.value.suggested_filename == 'report.md'
        assert 'Browser fixture DESIGN Work' in Path(transfer.value.path()).read_text(encoding='utf-8')
        page.route('**/diagnostic?mode=full', lambda route: route.fulfill(
            status=409, content_type='application/json',
            body='{"code":"DIAGNOSTIC_EXPORT_SIZE_LIMIT","message":"fixture size limit"}'))
        page.get_by_role('button', name='完整证据包').click()
        page.get_by_text('fixture size limit').wait_for()
        print(json.dumps({'browser':'Edge headless','work_id':work_id,
            'list_download':'PASS','detail_download':'PASS',
            'error_notice':'PASS','list_trace_hydration':'NONE'},sort_keys=True))
        context.close()
        browser.close()


if __name__ == '__main__':
    main(sys.argv[1])
