"""Import explicit human decisions, preserve originals, and build labeled CSS fixtures."""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import html
import json
import re
import shutil
import yaml

BASE = Path(__file__).resolve().parents[1]
PREVIOUS = BASE / '국내외_과거사례포함_숨김광고_원문검수'
OUT = BASE / '사람3_최종결과_20261005'
REVIEW = Path('/mnt/c/Users/user/Downloads/실제광고_국내외_과거포함_검수결과.csv')
QUOTAS = dict(font_left_display=45, visibility_hidden=15, clip=15, text_indent=10, transform_outside=15)
GROUPS = dict(font_size_0_1px='font_left_display', left_negative='font_left_display', display_none='font_left_display',
              visibility_hidden='visibility_hidden', clip_clip_path='clip', text_indent='text_indent', transform_document_coords='transform_outside')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def document(record, controls=False):
    # CSS fixture HTML contains only our local markup and a fragment link.
    return ('<!doctype html><html lang="ko"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:">'
            '<title>'+html.escape(record['id'])+'</title><style>'
            'body{margin:24px;font:16px/1.5 sans-serif;color:#111;background:#fff}'
            '.review-root{box-sizing:border-box;min-height:80px}a{color:#111}'
            +record['css']+'</style><body>'+record['html']+'</body></html>')

def main():
    OUT.mkdir(exist_ok=True)
    records = json.loads((PREVIOUS/'원문_검수목록.json').read_text())
    with REVIEW.open(encoding='utf-8-sig', newline='') as f:
        reviews = list(csv.DictReader(f))
    byid = {r['id']: r for r in reviews}
    assert len(reviews) == len(byid) == len(records) == 102
    assert set(byid) == {r['id'] for r in records}
    review_hash = digest(REVIEW)
    selected, references, rejected, pending = [], [], [], []
    for original in records:
        r = dict(original)
        row = byid[r['id']]
        for name in ['source', 'evidence_text', 'evidence_basis']:
            assert row[name] == r[name], (r['id'], name)
        assert row['hide_method'] == r['hide_label'], r['id']
        r['human_review'] = {name: row[col] for name, col in dict(visual='visual_review', advertisement='advertisement_review',
            suitability='suitability_review', same_ad_visible='same_ad_visible_review', historical_source='historical_source_review',
            historical_hiding='historical_hiding_review', duplicate='duplicate_review', memo='memo').items()}
        h = r['human_review']
        excluded = h['suitability']=='제외' or h['advertisement']=='홍보 아님' or h['duplicate']=='중복'
        common = h['suitability']=='사용' and h['advertisement']=='홍보 맞음' and h['duplicate']=='중복 없음'
        native = r['evidence_basis']=='native_page_snapshot'
        approved = common and ((h['visual'] in ['안 보임', '작은 흔적만 보임'] and h['same_ad_visible']=='없음') if native
                              else (h['historical_source']=='공개된 피해 원문 확인' and h['historical_hiding']=='원래 숨김 설정 확인'))
        state = 'rejected' if excluded else ('user_accepted_native_original' if native else 'user_accepted_historical_copied_original') if approved else 'pending'
        assert row['is_positive']==state, (r['id'], row['is_positive'], state)
        r['review_status'] = state
        r['review_provenance'] = dict(file_name=REVIEW.name, file_sha256=review_hash, matching_fields=['id','source','evidence_text','hide_method','evidence_basis'])
        r['is_positive'] = approved and not excluded
        r['original'] = True
        r['css_applied_by_collector'] = False
        r['native_live_positive'] = approved and not excluded and native
        r['victim_full_page_rendering_verified'] = 'human_reviewed' if r['native_live_positive'] else False
        r['notes'] += ' 2026-10-05 최종 사용자 CSV의 광고성·숨김 근거·중복·사용 판정을 반영함. 과거 공개 사본은 피해 전체 화면 확인과 구분함.'
        if excluded: rejected.append(r)
        elif not approved: pending.append(r)
        elif r['quota_type'] is None: references.append(r)
        else: selected.append(r)
    counts = Counter(r['quota_type'] for r in selected)
    publishers = Counter(r.get('source_publisher_key',r.get('source_publisher',r['source_host'])) for r in selected+references)
    assert max(publishers.values()) <= 10
    assert len({r['campaign_key'] for r in selected}) == len(selected)
    assert len({r['ad_href'] for r in selected}) == len(selected)
    assert all(counts[k]>=v for k,v in QUOTAS.items()), counts
    # Original quota counting is independent of any generated CSS variants.
    dump(OUT/'data/originals/offscreen_originals.json', selected)
    (OUT/'data/originals/offscreen_originals.yaml').write_text(yaml.safe_dump(selected,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
    dump(OUT/'data/originals/reference_only.json',references)
    dump(OUT/'data/review/imported_decisions.json', reviews)
    dump(OUT/'data/review/rejected_and_pending.json',dict(rejected=rejected,pending=pending))
    shutil.copy2(REVIEW,OUT/'data/review'/REVIEW.name)
    dump(BASE/'data/review/최종원문_확정_20261005.json',selected)
    shutil.copy2(REVIEW,BASE/'data/review'/REVIEW.name)

    plans = json.loads((BASE/'data/catalog/offscreen_variations.json').read_text())
    rules = {r['id']:r for r in json.loads((BASE/'data/css/hidden_rules.json').read_text())}
    buckets = defaultdict(list)
    for r in selected: buckets[r['quota_type']].append(r)
    offsets = Counter()
    fixtures, controls = [], []
    for plan in plans:
        group = GROUPS[plan['subtype']]
        original = buckets[group][offsets[group]]
        offsets[group] += 1
        identifier = plan['id'].replace('OF-V','OF-T')
        css = plan['css'].replace(plan['id'],identifier)
        markup = plan['html'].replace(plan['id'],identifier).replace('화면 표시 여부를 확인하는 검수용 문장입니다.',html.escape(original['evidence_text']))
        adjustments = []
        # Keep prior visible controls in a separate negative set; create positive counterparts.
        old_markup, old_css = markup, css
        if plan['intended_visual_result']=='cascade_control_may_be_visible':
            css = css.replace('visibility:visible;', 'visibility:hidden;')
            adjustments.append('기존 자손 visibility:visible 대조군을 visibility:hidden 시험용으로 변경')
        if plan['id'] in ['OF-V089','OF-V090','OF-V099','OF-V100']:
            css = css.replace('translateX(10000px)','translateX(-10000px)').replace('translateY(10000px)','translateY(-10000px)')
            css = css.replace('right:-10000px;top:0;','top:-10000px;left:0;').replace('bottom:-10000px;left:0;','top:-10000px;left:0;')
            adjustments.append('스크롤로 보이는 양수/right/bottom 이동 대조군을 음수 이동 시험용으로 변경')
        referenced = [rules[k] for k in plan['source_rule_ids']]
        r = dict(id=identifier,category='OFFSCREEN',subtype=plan['subtype'],html=markup,css=css,
            evidence_text=original['evidence_text'],original=False,expected_location=plan['expected_location'].replace(plan['id'],identifier),
            is_positive=True,extra_finding=None,source=original['source'],notes='사용자가 승인한 원문 문구에 라이브러리 CSS 또는 명시한 파생 변형을 적용한 시험용 샘플. 실제 사이트 원문 HTML/CSS와 다름.',
            original_id=original['id'],original_quota_type=original['quota_type'],fixture_quota_type=group,
            evidence_basis='controlled_css_fixture_from_user_approved_original',css_applied_by_collector=True,
            original_evidence_basis=original['evidence_basis'],original_review_provenance=original['review_provenance'],
            source_rule_ids=plan['source_rule_ids'],css_source_status=plan['source_status'],
            css_rule_sources=[{k:s[k] for k in ['id','library','version','source_file','source_line','source_column','license']} for s in referenced],
            css_adjustments=adjustments,rendered_verified=False,rendering_evidence=None,
            expected_visibility='tiny_font_trace_allowed' if plan['subtype']=='font_size_0_1px' and 'font-size:0;' not in css else 'not_visible_after_scroll_and_tab',
            legal_illegality_verified=False)
        if adjustments:
            control = dict(r,id=identifier.replace('OF-T','OF-C'),html=old_markup.replace('OF-T','OF-C'),css=old_css.replace('OF-T','OF-C'),
                expected_location=r['expected_location'].replace('OF-T','OF-C'),is_positive=False,expected_visibility='visible_initially_or_after_scroll',
                notes='자손 가시성 복원 또는 스크롤로 도달할 수 있는 이동 대조군. 원문 개수 및 positive 개수에 포함하지 않음.',css_adjustments=[])
            controls.append(control)
        fixtures.append(r)
    assert len(fixtures)==len({r['original_id'] for r in fixtures})==100
    for r in fixtures+controls:
        (OUT/'fixtures').mkdir(exist_ok=True)
        (OUT/'fixtures'/f"{r['id']}.html").write_text(document(r),encoding='utf-8')
    dump(OUT/'data/samples/offscreen.json',fixtures)
    (OUT/'data/samples/offscreen.yaml').write_text(yaml.safe_dump(fixtures,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
    dump(OUT/'data/samples/offscreen_controls.json',controls)
    shutil.copytree(PREVIOUS/'근거이미지',OUT/'근거이미지',dirs_exist_ok=True)
    shutil.copy2(PREVIOUS/'최종확인_국내외_과거사례포함.html',OUT/'원문검수_보관.html')
    shutil.copy2(PREVIOUS/'원문근거_수집메타데이터.json',OUT/'data/originals/원문근거_수집메타데이터.json')
    for folder in ['data/css','data/unicode','licenses']:
        shutil.copytree(BASE/folder,OUT/folder,dirs_exist_ok=True)
    shutil.copytree(BASE/'data/catalog',OUT/'data/catalog',dirs_exist_ok=True)
    for relative in ['THIRD_PARTY.md','CSS_추출설명.md','로컬_게시판_실행기록.md','.gitignore','data/source_manifest.json','data/review/human_observations.json','data/review/review_summary.json']:
        dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/relative,dest)
    for s in json.loads((BASE/'data/css/source_files.json').read_text()):
        dest=OUT/s['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/s['path'],dest)
    tailwind_js='data/raw/tailwind-3.4.17/corePlugins.js'
    dest=OUT/tailwind_js;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/tailwind_js,dest)

    summary = dict(status='human_review_imported_rendering_pending',review_file_sha256=review_hash,
        total_human_approved= len(selected)+len(references),quota_originals=len(selected),reference_only=len(references),
        rejected=len(rejected),pending=len(pending),quotas=QUOTAS,approved_original_counts=dict(counts),
        original_shortage={k:max(0,n-counts[k]) for k,n in QUOTAS.items()},original_quota_completed=True,
        original_evidence_basis_counts=dict(Counter(r['evidence_basis'] for r in selected)),source_publisher_limit=10,
        source_publisher_counts=dict(publishers),duplicate_review_basis='Known campaign/destination families plus explicit human duplicate decisions; unknown historical advertiser identities remain unverified.',
        controlled_css_fixtures=len(fixtures),visible_controls=len(controls),fixture_counts=dict(Counter(r['fixture_quota_type'] for r in fixtures)),
        historical_full_victim_rendering_verified=0,js_visibility_and_display_combined_originals=4,
        redacted_original_text_ids=[r['id'] for r in selected if 'ranum.com' in r['source'] and ' . ' in ' '+r['evidence_text']+' '],
        original_counts_include_generated_variants=False)
    dump(OUT/'최종현황.json',summary)
    index=['<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>사람3 최종 결과</title><style>body{max-width:1100px;margin:30px auto;padding:0 20px;font:16px/1.7 sans-serif}table{border-collapse:collapse;width:100%}th,td{padding:8px;border:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}a{color:#075fa8}</style><h1>사람3 최종 결과</h1>',
        '<p>검수 승인 102개 중 유형별 원문 100개, 참고 2개. 시험용 CSS 샘플 100개와 가시 대조군 7개입니다. 아래 문구는 확인을 위해 표시합니다. 시험용 화면은 각 링크를 열어 확인할 수 있습니다.</p>',
        '<p><a href="README.md">사용 설명</a> · <a href="data/review/실제광고_국내외_과거포함_검수결과.csv">원본 검수 CSV</a> · <a href="data/samples/offscreen.yaml">시험용 YAML</a> · <a href="data/originals/offscreen_originals.yaml">승인 원문 YAML</a></p>']
    mapped={r['original_id']:r for r in fixtures}
    previous=None
    for r in selected:
        if r['source']!=previous:
            if previous is not None:index.append('</tbody></table>')
            index.append('<h2>'+html.escape(r['source_publisher'])+'</h2><p><a href="'+html.escape(r['source'],quote=True)+'">공개 원문 출처</a></p><table><thead><tr><th>원문 ID</th><th>광고 문구</th><th>원문 유형</th><th>시험용 화면</th></tr></thead><tbody>')
            previous=r['source']
        f=mapped[r['id']]
        index.append('<tr><td>'+r['id']+'</td><td>'+html.escape(r['evidence_text'])+'</td><td>'+r['quota_type']+'</td><td><a href="fixtures/'+f['id']+'.html">'+f['id']+'</a></td></tr>')
    index.append('</tbody></table><h2>가시 대조군</h2><p>표시되는 것이 정상이며 positive 개수에 포함하지 않습니다.</p><ul>')
    for r in controls:index.append('<li><a href="fixtures/'+r['id']+'.html">'+r['id']+'</a></li>')
    index.append('</ul></html>')
    (OUT/'시작.html').write_text('\n'.join(index),encoding='utf-8')
    readme='''# 사람3 최종 결과

2026-10-05 사용자가 보낸 최종 CSV 102행을 원문 ID·출처·문구·숨김 방식·근거 종류와 대조해 반영했습니다. 전부 사용 승인되었으며 참고 2개는 유형별 개수에 포함하지 않았습니다.

| 원문 유형 | 승인 원문 | 최소 기준 |
|---|---:|---:|
| font-size 0~1px / 음수 left / display:none | 45 | 45 |
| visibility:hidden (display:none 동시 적용 4개 포함) | 15 | 15 |
| clip / clip-path | 15 | 15 |
| text-indent | 10 | 10 |
| transform / 문서 밖 좌표 | 15 | 15 |

원문 100개는 현재 페이지 수집 52개와 사용자가 승인한 과거 피해 코드 공개 사본 48개입니다. 과거 사본을 현재 직접 방문해 확인한 데이터로 표시하지 않습니다. 같은 출처 사이트는 여러 페이지를 합쳐 최대 10개이며, 원문 링크는 연속 배치했습니다. 기존 검수·출처 자료는 보존했습니다.

ZIP을 풀고 `시작.html`을 열면 목록과 시험용 화면을 볼 수 있습니다. 외부 광고 링크를 열 필요 없이 시험용 HTML을 로컬에서 실행할 수 있습니다. 시험용 화면이 비어 보이는 것은 숨김 기법의 기대 동작입니다. font-size 0.25~1px는 읽을 수 없는 작은 흔적을 허용합니다. 가시 대조군 7개는 글자가 보이는 것이 정상입니다.

- `data/originals/offscreen_originals.yaml`: 사용 승인한 원문 100개. 원래 HTML·CSS, 상위 태그, 출처, 수집 해시와 사람 검수 기록을 보존했습니다. 원문 선택자는 당시 페이지 기준이며 독립 발췌 파일에 재사용하지 않습니다. 과거 피해 DOM 선택자를 알 수 없으면 빈 값으로 보존했습니다.
- `data/originals/reference_only.json`: 폭·높이0 overflow 사례와 잘린 hacklink 이미지, 참고 2개. 원문 유형별 기준 및 시험용 100개에서 제외했습니다.
- `data/samples/offscreen.yaml`: 공통 필드를 갖춘 CSS 시험용 100개. `original:false`, `css_applied_by_collector:true`, 원문 ID·문구·출처와 CSS 규칙 출처를 기록했습니다. 실제 사이트의 HTML/CSS 원문이라고 주장하지 않습니다.
- `data/samples/offscreen_controls.json`: 자손 visibility 복원 3개와 스크롤 가능한 양수 이동 4개, 총7개 가시 대조군.
- `fixtures/`: 외부 네트워크 및 JavaScript 없이 실행하는 시험용 화면 107개. 링크는 로컬 fragment입니다.
- `data/review/`: 사용자 CSV 원본과 가져오기 결과. 사용자 판정과 자동 렌더링 관찰을 구분합니다.
- `data/css/`, `data/raw/`, `licenses/`, `THIRD_PARTY.md`: 라이브러리 규칙 원문·출처 위치·라이선스. Tailwind 정적 JS 정의를 CSS로 기계 변환한 것은 배포 CSS 원문과 구분했습니다.
- `data/unicode/`: Unicode 17.0.0 confusables.txt, Scripts.txt, IdentifierType.txt 및 출처 해시.
- `로컬_게시판_실행기록.md`: 사용자가 전자정부 표준FW 로그인, 게시판 생성, 글 등록·내용 조회를 직접 확인한 기록.

Bootstrap·Tailwind·HTML5BP·전자정부 CSS 추출, 변형 목록, Unicode 출처·라이선스, CSS 원문 복사 자료, THIRD_PARTY 초안, 로컬 게시판 실행, 원문 수집 및 최종 사람 검수는 완료했습니다. 시험용 CSS는 라이브러리 원문 또는 명시한 파생 변형입니다. 원래 대조군 7개는 별도 보존하고, positive 시험용에는 숨겨지는 변형을 사용했습니다. 원문 부족을 변형으로 채우지 않았습니다.

Ranum의 점(.)으로 축약된 상품명은 그대로 보존했습니다. 사용자의 승인과 별개로 복원 전 상품명·과거 광고주 신원은 미확인입니다. 문구·도메인 계열의 알려진 중복과 사용자의 중복 검수를 반영했지만, 알 수 없는 과거 운영자 신원까지 확인했다는 뜻은 아닙니다. 과거 피해 사이트 전체 화면과 그 당시 이미지 중복은 확인할 수 없는 한계로 보존했습니다. 기술적 숨김 광고 판정은 법적 불법성 확정이나 주최 측 데이터 사용 승인과 구분됩니다.

`검증결과.json`에 렌더링·선택자·출처 검증 결과를 기록합니다. 검증 환경은 Chromium 데스크톱/모바일, DPR1이며 다른 브라우저 및 확대 비율 전체를 검증한 것은 아닙니다. 개인정보·계정 비밀번호와 기사 전체 원문, 비공개 대량 웹페이지 사본은 이 패키지에 넣지 않습니다.
'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
