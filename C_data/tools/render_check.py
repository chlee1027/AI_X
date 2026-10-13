# Render each YAML snippet standalone (same page template as hg_collect/tr_verify.py) and compare pixels with/without the target.
import sys, io, yaml, numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#fff;font:16px/1.6 'Malgun Gothic',sans-serif;color:#222}}
#root{{padding:16px;width:640px}} {css}</style></head><body><div id="root">{html}</div></body></html>"""
rows = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge'); pg = b.new_page(viewport={'width': 900, 'height': 900})
    for r in rows:
        pg.set_content(PAGE.format(css=r['css'], html=r['html']))
        pg.wait_for_timeout(150)
        el = pg.query_selector('#root > ' + r['expected_location']) or pg.query_selector('#root ' + r['expected_location'])
        if not el: out[r['id']] = 'no-el'; continue
        box = el.bounding_box()
        if not box or box['width'] == 0 or box['height'] == 0: out[r['id']] = 'zero-box'; continue
        clip = {'x': max(0, box['x'] - 2), 'y': max(0, box['y'] - 2), 'width': box['width'] + 4, 'height': box['height'] + 4}
        a = np.asarray(Image.open(io.BytesIO(pg.screenshot(clip=clip, full_page=True))).convert('RGB'), dtype=int)
        el.evaluate("e => e.style.visibility = 'hidden'")
        c = np.asarray(Image.open(io.BytesIO(pg.screenshot(clip=clip, full_page=True))).convert('RGB'), dtype=int)
        d = int(np.abs(a - c).max()); out[r['id']] = 'invisible' if d <= 8 else ('visible' if d >= 40 else 'borderline')
    b.close()
import collections
print(collections.Counter(out.values()))
bad = {k: v for k, v in out.items() if v != 'invisible'}
print('not invisible:', list(bad.items())[:30])
yaml.safe_dump(out, open(sys.argv[1].replace('.yaml', '_render.yaml'), 'w', encoding='utf-8'), allow_unicode=True)
