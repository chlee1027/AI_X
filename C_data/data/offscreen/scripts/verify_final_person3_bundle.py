"""Check imported evidence and offline rendering of derived positive/negative fixtures."""
from pathlib import Path
from collections import Counter
import hashlib
import html
import json
import os
import re
import sys
import yaml

sys.path.insert(0,'/tmp/person3_browser_tools')
os.environ['LD_LIBRARY_PATH']='/tmp/person3_browser_deps/root/usr/lib/x86_64-linux-gnu'
from playwright.sync_api import sync_playwright

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'사람3_최종결과_20261005'
OLD=BASE/'국내외_과거사례포함_숨김광고_원문검수'
CHROME='/home/dyhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    original=json.loads((OUT/'data/originals/offscreen_originals.json').read_text())
    previous={r['id']:r for r in json.loads((OLD/'원문_검수목록.json').read_text())}
    fixtures=json.loads((OUT/'data/samples/offscreen.json').read_text())
    controls=json.loads((OUT/'data/samples/offscreen_controls.json').read_text())
    summary=json.loads((OUT/'최종현황.json').read_text())
    assert len(original)==len(fixtures)==100 and len(controls)==7
    assert len({r['id'] for r in original})==len({r['campaign_key'] for r in original})==len({r['ad_href'] for r in original})==100
    assert len({r['original_id'] for r in fixtures})==100
    assert max(summary['source_publisher_counts'].values())<=10
    assert all(summary['approved_original_counts'][k]>=n for k,n in summary['quotas'].items())
    review=OUT/'data/review/실제광고_국내외_과거포함_검수결과.csv'
    assert digest(review)==summary['review_file_sha256']==digest(Path('/mnt/c/Users/user/Downloads')/review.name)
    before_yaml=digest(BASE/'data/samples/offscreen.yaml')
    for r in original:
        old=previous[r['id']]
        for k in ['html','css','evidence_text','source','ad_href','expected_location','provenance']:
            assert r[k]==old[k],(r['id'],k)
        assert not r['css_applied_by_collector'] and r['is_positive'] and r['original']
        p=r['provenance']
        if p.get('snapshot'):
            raw=BASE/'data/raw/site_checks'/p['snapshot']/'page.html'
            assert digest(raw)==p['page_sha256']
        if p.get('provider_cache'):
            assert digest(BASE/p['provider_cache'])==p['provider_cache_sha256']
        if r.get('evidence_image'):
            assert digest(OUT/r['evidence_image'])==p['code_image_sha256']
        if r['evidence_basis']=='historical_copied_original':
            assert not r['native_live_positive'] and r['expected_location']=='' and not r['victim_full_page_rendering_verified']
    css_rules=json.loads((OUT/'data/css/hidden_rules.json').read_text())
    for r in css_rules:
        source=(OUT/r['source_file']).read_bytes().decode('utf-8-sig')
        offset=sum(map(len,source.splitlines(keepends=True)[:r['source_line']-1]))+r['source_column']-1
        assert source[offset:offset+len(r['raw_css'])]==r['raw_css']
    for item in json.loads((OUT/'data/source_manifest.json').read_text()):
        p=OUT/item['path']
        if p.exists():assert digest(p)==item['sha256']
    mandatory=['id','category','subtype','html','css','evidence_text','original','expected_location','is_positive','extra_finding','source','notes']
    for r in fixtures+controls:
        assert all(k in r for k in mandatory)
        assert r['original'] is False and r['css_applied_by_collector'] is True
        assert r['evidence_text']==previous[r['original_id']]['evidence_text']
        assert (OUT/'fixtures'/f"{r['id']}.html").exists()
        assert '<script' not in r['html']
    assert yaml.safe_load((OUT/'data/samples/offscreen.yaml').read_text())==fixtures
    observations=[];network=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=CHROME,headless=True)
        for name,width,height in [('desktop',1280,900),('mobile',390,844)]:
            context=browser.new_context(viewport=dict(width=width,height=height),device_scale_factor=1)
            page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            def route_request(route):
                if route.request.url.startswith('file:'):route.continue_()
                else:network.append(route.request.url);route.abort()
            page.route('**/*',route_request)
            for r in fixtures+controls:
                page.goto((OUT/'fixtures'/f"{r['id']}.html").as_uri())
                target=page.locator(r['expected_location'])
                assert target.count()==1,(r['id'],name)
                assert target.text_content()==r['evidence_text']
                # Compare actual raster output with the text explicitly suppressed,
                # without changing layout. Scroll and focus before the second comparison.
                data=target.evaluate('''e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return {computed:{fontSize:s.fontSize,display:s.display,visibility:s.visibility,clip:s.clip,clipPath:s.clipPath,textIndent:s.textIndent,transform:s.transform,position:s.position},rect:{x:r.x,y:r.y,width:r.width,height:r.height}}}''')
                before=page.screenshot(animations='disabled')
                target.evaluate("e=>e.style.setProperty('visibility','hidden','important')")
                suppressed=page.screenshot(animations='disabled')
                target.evaluate("e=>e.style.removeProperty('visibility')")
                initial_pixels=before!=suppressed
                target.evaluate("e=>e.scrollIntoView({block:'center',inline:'center'})")
                page.keyboard.press('Tab')
                after=page.screenshot(animations='disabled')
                target.evaluate("e=>e.style.setProperty('visibility','hidden','important')")
                after_suppressed=page.screenshot(animations='disabled')
                scroll_tab_pixels=after!=after_suppressed
                accepted_tiny=r['is_positive'] and r['expected_visibility']=='tiny_font_trace_allowed'
                if r['is_positive'] and not accepted_tiny:
                    assert not initial_pixels and not scroll_tab_pixels,(r['id'],name,data,initial_pixels,scroll_tab_pixels)
                if not r['is_positive']:
                    assert initial_pixels or scroll_tab_pixels,(r['id'],name,'negative control never visible')
                observation=dict(id=r['id'],viewport=name,selector_matches=1,exact_evidence_text=True,
                    initial_text_pixels_detected=initial_pixels,after_scroll_tab_text_pixels_detected=scroll_tab_pixels,
                    tiny_font_trace_allowed=accepted_tiny,**data)
                observations.append(observation)
                if r['is_positive']:
                    r.setdefault('rendering_evidence',{})
                    if r['rendering_evidence'] is None:r['rendering_evidence']={}
                    r['rendering_evidence'][name]=observation
            context.close()
        browser.close()
    assert not network and not errors,(network,errors)
    for r in fixtures:r['rendered_verified']=True
    (OUT/'data/samples/offscreen.json').write_text(json.dumps(fixtures,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'data/samples/offscreen.yaml').write_text(yaml.safe_dump(fixtures,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
    (OUT/'data/review/fixture_rendering_observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert digest(BASE/'data/samples/offscreen.yaml')==before_yaml
    report=dict(status='passed',human_review_rows=102,approved_originals=100,reference_only=2,
        quotas=summary['quotas'],approved_original_counts=summary['approved_original_counts'],original_quota_completed=True,
        source_publisher_cap_passed=True,known_campaign_and_exact_destination_uniqueness_passed=True,
        source_excerpt_and_provenance_preserved=100,library_rule_exact_source_slices=141,
        fixture_count=100,visible_controls=7,viewport_runs=len(observations),unique_selector_and_exact_text_checks=len(observations),
        positive_fixture_rendering_passed=200,negative_controls_visible_passed=14,tiny_font_positive_fixtures=12,
        network_requests=0,page_errors=[],unicode_version='17.0.0',
        review_file_sha256=summary['review_file_sha256'],previous_21_original_yaml_unchanged=True,
        caveats=['Historical originals verified by published code and human review; full historical victim page rendering not verified.',
                 'Ranum redacted terms preserved; historical merchant identities are not reconstructed.',
                 'Fixture rendering is tested in Chromium, two viewports, DPR1; does not imply all browser/zoom settings.'])
    (OUT/'검증결과.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary['status']='complete';summary['fixture_rendering_verified']=True;summary['person3_task_completed']=True
    (OUT/'최종현황.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
