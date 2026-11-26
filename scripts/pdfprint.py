"""HTML → PDF(PC · 폰 «PDF 로 볼트에 저장»·«PDF 로 공유»의 엔진 · 11-23).
폰이 그린 화면(옵시디언 노트·폰 보기 표·쪽 원본)을 HTML 한 장으로 보내면, 이 PC 의 크로미움 계열 브라우저(크롬·엣지)를
헤드리스로(창 없음) 띄워 인쇄한다 — 데스크톱 brain-source 의 «PrintDoc → printToPDF» 와 같은 꼴(글자 = 벡터 · 고르기·찾기 됨).
막음: 받은 HTML 머리에 CSP 를 넣어 바깥 주소·파일을 못 읽게 하고(그림·글꼴은 data: 만) 대본을 끈다. 잠깐 프로필·파일은 끝에 지운다.

    py -3 pdfprint.py <html> <out.pdf>      # 손으로 시험
"""
import glob
import pathlib
import os
import shutil
import subprocess
import sys
import tempfile

CSP = ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; font-src data:; '
       'style-src \'unsafe-inline\'; media-src data:">')
TIMEOUT = 120


def browser():
    """크롬 → 엣지(윈도엔 늘 있음) · BRAIN_PDF_BROWSER 로 바꿀 수 있다 · 없으면 None"""
    env = os.environ.get('BRAIN_PDF_BROWSER')
    if env and os.path.isfile(env):
        return env
    roots = [os.environ.get(k) for k in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
    for rel in (r'Google\Chrome\Application\chrome.exe', r'Microsoft\Edge\Application\msedge.exe', r'Chromium\Application\chrome.exe'):
        for r in roots:
            if r and os.path.isfile(os.path.join(r, rel)):
                return os.path.join(r, rel)
    for name in ('chrome', 'google-chrome', 'chromium', 'msedge'):
        p = shutil.which(name)
        if p:
            return p
    return None


def guard(html):
    """CSP 를 <head> 맨 앞에 · <script> 빼기(폰이 이미 빼지만 한 번 더)"""
    import re
    html = re.sub(r'(?is)<script\b.*?</script\s*>', '', html)
    m = re.search(r'(?i)<head[^>]*>', html)
    return html[:m.end()] + CSP + html[m.end():] if m else '<head>' + CSP + '</head>' + html


def html_to_pdf(html, out, tmp_root=None):
    """html(str) → out(PDF 경로) · 돌려줌 = 바이트 수 · 실패는 RuntimeError"""
    exe = browser()
    if not exe:
        raise RuntimeError('이 PC 에 크롬·엣지가 없음')
    tmp = tempfile.mkdtemp(prefix='brain-pdf-', dir=tmp_root)
    try:
        src = os.path.join(tmp, 'page.html')
        with open(src, 'w', encoding='utf-8') as f:
            f.write(guard(html))
        dst = os.path.join(tmp, 'out.pdf')
        argv = [exe, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
                '--disable-background-networking', '--no-pdf-header-footer',   # 대본은 CSP(default-src 'none')가 막음 · --blink-settings=scriptEnabled=false 는 인쇄를 비게 함(11-23 잼)
                '--user-data-dir=' + os.path.join(tmp, 'prof'), '--print-to-pdf=' + dst, pathlib.Path(src).as_uri()]   # 한글 경로 = %인코딩 주소(그대로 넘기면 빈 결과 · 11-23 잼)
        r = subprocess.run(argv, capture_output=True, timeout=TIMEOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if not os.path.isfile(dst) or not os.path.getsize(dst):
            raise RuntimeError('PDF 를 못 만듦 ' + (r.stderr or b'').decode('utf-8', 'replace')[-200:])
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        shutil.move(dst, out)
        return os.path.getsize(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for p in glob.glob(os.path.join(tmp_root or tempfile.gettempdir(), 'brain-pdf-*')):   # 지난번에 못 지운 것
            shutil.rmtree(p, ignore_errors=True)


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        print(html_to_pdf(f.read(), sys.argv[2]))
