"""결과 확인 화면 (10-19). result.json + debug.json -> report.html 한 파일(인터넷 없이 열림).

근거(진행보고서 1절·7-24절): 본심사 「실무 활용성」 20점. 담당자가 검출 결과를 보고 바로 조치할 수 있어야 한다.
  - 집계: 기법별·쪽별 개수, 검사 쪽수·시간
  - 건별: 쪽 주소, 기법, 위치(CSS 선택자, iframe 여부), 근거 원문 + 위장을 푼 글자, 판정 근거(숨김 방식·글자 변형), 광고 점수
  - 업자 묶음: 근거 글자에서 연락처(URL·메신저·전화)를 뽑아 같은 연락처를 쓰는 검출을 묶는다(한 업자가 여러 쪽에 뿌린 것)
  - 조치 안내: 기법별로 무엇을 지우고 무엇을 점검할지
  - 담당자 검토: 건마다 「광고 확인 / 오탐 / 미검토」를 고르고 CSV 로 내려받는다(브라우저에만 저장)
외부 파일·인터넷을 쓰지 않는다(공공기관 내부망 PC 대비).

사용: python report_html.py <result.json> [debug.json] [report.html]
"""
import html
import json
import re
import sys
from pathlib import Path

from textfeat import restore
from train2 import URL_RE, HANDLE_RE, PHONE_RE

TECH_KO = {"HOMOGLYPH": "닮은꼴 글자", "JAMO": "자모 분해", "TRANSPARENT": "투명 글자", "OFFSCREEN": "화면 밖 숨김",
           # 10-20 추가 유형(result_extra.json, 진행보고서 7-50절). 적격평가 4종과 따로 센다
           "ZERO_WIDTH": "추가: 보이지 않는 글자", "ENCODING": "추가: 인코딩 숨김", "META_CLOAKING": "추가: 메타 태그 은닉",
           "CSS_CONTENT": "추가: CSS 생성 글자", "LINK_CLOAKING": "추가: 링크 위장"}
ACTION = {
    "HOMOGLYPH": "게시글·댓글이면 삭제하고 작성자를 차단합니다. 닮은꼴 글자는 금칙어 필터를 피하려는 것이므로, 필터가 글자를 정규화(NFKC 등)한 뒤 검사하도록 설정을 점검합니다.",
    "JAMO": "게시글·댓글이면 삭제하고 작성자를 차단합니다. 자모를 풀어 쓴 글자는 금칙어 필터를 피하려는 것이므로, 필터가 자모를 다시 조합한 뒤 검사하도록 점검합니다.",
    "TRANSPARENT": "보이지 않게 숨겨 넣은 글자입니다. 게시물 본문이면 편집기에서 style 속성(색·투명도) 입력을 제한합니다. 머리말·꼬리말 같은 공통 영역이면 사이트 변조 가능성이 있으므로 관리자 계정과 템플릿 변경 이력을 점검합니다.",
    "ZERO_WIDTH": "광고 문구 글자 사이에 보이지 않는 글자(소프트 하이픈·폭 없는 공백)를 끼워 금칙어 필터를 피한 것입니다. 게시물이면 삭제하고, 필터가 이 글자들을 지운 뒤 검사하도록 점검합니다.",
    "ENCODING": "광고 문구를 링크 주소의 퍼센트 인코딩이나 HTML 문자 참조 안에만 적어 원문 검사를 피한 것입니다. 링크를 지우고, 외부 사이트 검색창을 악용한 주소면 같은 꼴의 링크를 함께 찾습니다.",
    "META_CLOAKING": "화면에는 없고 head 의 메타 태그(설명·제목)에만 광고 문구가 있어 검색 결과에만 노출됩니다. 페이지 템플릿·게시판 설정의 메타 값이 변조됐는지 점검하고, 원 글이 지워졌어도 메타가 남는지 확인합니다.",
    "CSS_CONTENT": "광고 문구가 본문이 아니라 스타일시트의 ::before·::after content 값에 들어 있습니다. 해당 스타일시트·템플릿의 변경 이력을 점검합니다.",
    "LINK_CLOAKING": "링크 글은 평범한데 주소가 단축 주소·의심 도메인으로 갑니다. 목적지를 확인하고(직접 열지 말고 차단 목록 조회), 광고 게이트면 링크를 지우고 작성 경로를 점검합니다.",
    "OFFSCREEN": "화면 밖이나 크기 0 으로 숨겨 넣은 글자입니다. 게시물 본문이면 편집기에서 style 속성(위치·크기·display) 입력을 제한합니다. 공통 영역이면 사이트 변조 가능성이 있으므로 관리자 계정과 템플릿 변경 이력을 점검합니다.",
}


def contacts(text):
    """근거 글자(위장을 푼 것)에서 연락처 꼴을 뽑는다. 업자 묶음 열쇠."""
    t = restore(text)
    out = set()
    for w in t.split():
        if URL_RE.search(w):
            out.add(re.sub(r"^https?://|^www\.|[/?#].*$", "", w.lower()).strip(".,;:()[]"))
    for m in re.finditer(r"@[A-Za-z0-9_]{3,}", t):
        out.add(m.group(0).lower())
    for m in PHONE_RE.finditer(t):
        out.add(re.sub(r"\D", "", m.group(0)))
    if HANDLE_RE.search(t) and not out:
        m = re.search(r"(?:텔레그램|텔레|카톡|카카오|라인|telegram|kakao)\s*[:：]?\s*([A-Za-z0-9_]{3,})", t, re.I)
        if m:
            out.add("@" + m.group(1).lower())
    return sorted(x for x in out if len(x) >= 4)


def build(result_path, debug_path=None, out_path=None):
    result_path = Path(result_path)
    res = json.loads(result_path.read_text(encoding="utf-8"))
    dbg = {}
    debug_path = Path(debug_path) if debug_path else result_path.with_name("debug.json")
    if debug_path.exists():
        dbg = json.loads(debug_path.read_text(encoding="utf-8"))
    extra = {(f["url"], f["location"], f["technique"]): f for f in dbg.get("findings", [])}
    items = []
    for f in res["findings"]:
        x = extra.get((f["url"], f["location"], f["technique"]), {})
        ev = f.get("evidence_text", "")
        rs = restore(ev)
        items.append({"id": f["id"], "url": f["url"], "t": f["technique"], "loc": f["location"], "ev": ev,
                      "rs": rs if rs != ev else "", "why": x.get("_why", []), "ad": x.get("_ad"),
                      "iframe": ">>>" in f["location"], "ct": contacts(ev), "llm": x.get("_llm")})
    # 10-20: 추가 유형(result_extra.json)도 같은 화면에 보인다. 기법 칸에는 extra_finding 이름을 쓴다
    xp = result_path.with_name("result_extra.json")
    if xp.exists():
        xd = {(f["url"], f["location"], f["extra_finding"]): f for f in dbg.get("extra_findings", [])}
        for f in json.loads(xp.read_text(encoding="utf-8")).get("findings", []):
            x = xd.get((f["url"], f["location"], f["extra_finding"]), {})
            ev = f.get("evidence_text", "")
            items.append({"id": f["id"], "url": f["url"], "t": f["extra_finding"], "loc": f["location"], "ev": ev, "rs": "",
                          "why": x.get("_why", []), "ad": x.get("_ad"), "iframe": ">>>" in f["location"], "ct": contacts(ev), "llm": None})
    pages = dbg.get("pages", [])
    data = {"meta": res["meta"], "items": items, "npages": len([p for p in pages if "error" not in p]),
            "nerr": len([p for p in pages if "error" in p]), "tech": TECH_KO, "action": ACTION}
    out_path = Path(out_path) if out_path else result_path.with_name("report.html")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out_path.write_text(PAGE.replace("__DATA__", payload).replace("__TITLE__", html.escape(res["meta"].get("entry_url", ""))),
                        encoding="utf-8")
    return out_path


PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>불법광고 탐지 결과</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1d2330;--mut:#5d6677;--line:#dfe3ea;--acc:#1f5fbf;--hg:#7a3db8;--ja:#b85c00;--tr:#0f7f6f;--of:#b8233a;--ok:#2e7d32;--no:#8a8f98}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--fg:#e6e9ef;--mut:#9aa3b2;--line:#2e343e;--acc:#6ea8ff;--hg:#c79cf2;--ja:#f0a35a;--tr:#4fd1bd;--of:#ff7d8f;--ok:#7bd88f;--no:#8a8f98}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 "Malgun Gothic","맑은 고딕",system-ui,sans-serif}
header{padding:20px 24px;border-bottom:1px solid var(--line);background:var(--card)}h1{margin:0 0 4px;font-size:20px}
.mut{color:var(--mut)}.wrap{max-width:1200px;margin:0 auto;padding:16px 24px}
.status{display:inline-block;padding:2px 10px;border-radius:12px;background:var(--ok);color:#fff;font-weight:600;font-size:12px;margin-right:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}.kpi b{display:block;font-size:24px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0 8px}.tabs button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 12px;border-radius:6px;cursor:pointer}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}.bar input,.bar select{padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
.bar input{flex:1;min-width:180px}.btn{padding:6px 12px;border:1px solid var(--acc);color:var(--acc);background:transparent;border-radius:6px;cursor:pointer}
.it{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--c);border-radius:8px;padding:12px 14px;margin:8px 0}
.it .h{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tag{font-size:12px;padding:1px 8px;border-radius:10px;color:#fff;background:var(--c)}
.it code,.loc{font-family:Consolas,monospace;font-size:12px;word-break:break-all}.ev{margin:6px 0;padding:6px 8px;background:var(--bg);border-radius:6px;white-space:pre-wrap;word-break:break-all}
.small{font-size:12px}a{color:var(--acc);word-break:break-all;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;background:var(--card)}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.rev{margin-left:auto}.rev select{padding:3px 6px}.hide{display:none}.act{font-size:13px;color:var(--mut);margin-top:4px}
@media (max-width:600px){.wrap,header{padding:12px 16px}}
</style></head><body>
<header><div class="wrap" style="padding:0"><h1>불법광고 탐지 결과</h1>
<div><span class="status">탐지 완료</span><span class="mut" id="meta"></span></div></div></header>
<div class="wrap">
<div class="grid" id="kpi"></div>
<div class="tabs" id="tabs"><button data-v="list" class="on">검출 목록</button><button data-v="pages">쪽별</button><button data-v="groups">업자 묶음</button><button data-v="guide">조치 안내</button></div>
<section id="v-list"><div class="bar"><input id="q" placeholder="글자·주소·선택자로 찾기"><select id="ft"><option value="">모든 기법</option></select>
<select id="fr"><option value="">모든 검토 상태</option><option value="미검토">미검토</option><option value="광고 확인">광고 확인</option><option value="오탐">오탐</option></select>
<button class="btn" id="csv">CSV 내려받기</button></div><div class="small mut" id="cnt"></div><div id="list"></div></section>
<section id="v-pages" class="hide"><table id="ptab"></table></section>
<section id="v-groups" class="hide"><p class="mut small">근거 글자에서 연락처(웹 주소·메신저 아이디·전화번호)를 뽑아, 같은 연락처를 쓰는 검출을 한 업자로 묶었습니다. 여러 쪽에 걸친 묶음은 한 업자가 사이트 전반에 뿌린 것일 가능성이 큽니다.</p><div id="groups"></div></section>
<section id="v-guide" class="hide"><div id="guide"></div></section>
<p class="small mut" style="margin-top:24px">검토 상태는 이 PC 의 브라우저에만 저장됩니다. 공유하려면 CSV 로 내려받으세요. 결과 파일(result.json)은 이 화면과 같은 폴더에 있습니다.</p>
</div>
<script>
const D=__DATA__;const C={HOMOGLYPH:"var(--hg)",JAMO:"var(--ja)",TRANSPARENT:"var(--tr)",OFFSCREEN:"var(--of)",ZERO_WIDTH:"var(--no)",ENCODING:"var(--no)",META_CLOAKING:"var(--no)",CSS_CONTENT:"var(--no)",LINK_CLOAKING:"var(--no)"};
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const KEY="adrev|"+D.meta.entry_url+"|"+D.meta.started_at;let rev={};try{rev=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(rev))}catch(e){}};
const m=D.meta;document.getElementById("meta").textContent=`${m.entry_url} | ${m.started_at.replace("T"," ")} ~ ${m.finished_at.slice(11)} | ${Math.round(m.elapsed_sec)}초 | ${m.tool_version}`;
const by={};D.items.forEach(x=>by[x.t]=(by[x.t]||0)+1);const pg=new Set(D.items.map(x=>x.url));
document.getElementById("kpi").innerHTML=[["검사한 쪽",D.npages+(D.nerr?` (오류 ${D.nerr})`:"")],["검출",D.items.length],["검출된 쪽",pg.size]].concat(Object.keys(D.tech).map(t=>[D.tech[t],by[t]||0])).map(([a,b])=>`<div class="kpi"><span class="mut small">${esc(a)}</span><b>${esc(b)}</b></div>`).join("");
const ft=document.getElementById("ft");Object.entries(D.tech).forEach(([k,v])=>ft.insertAdjacentHTML("beforeend",`<option value="${k}">${esc(v)}</option>`));
function card(x){const st=rev[x.id]||"미검토";return `<div class="it" style="--c:${C[x.t]}"><div class="h"><span class="tag">${esc(D.tech[x.t])}</span><b>${esc(x.id)}</b>
${x.ad!=null?`<span class="small mut">광고 점수 ${x.ad.toFixed(2)}</span>`:""}${x.iframe?'<span class="small mut">iframe 안</span>':""}${x.llm==="ad"?'<span class="small mut">AI 2차 판정: 광고</span>':""}
<span class="rev"><select data-id="${x.id}">${["미검토","광고 확인","오탐"].map(o=>`<option${o===st?" selected":""}>${o}</option>`).join("")}</select></span></div>
<div class="small">쪽: <a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.url)}</a></div>
<div class="small">위치: <span class="loc">${esc(x.loc)}</span></div>
<div class="ev">${esc(x.ev)}</div>${x.rs?`<div class="small">위장을 푼 글자: <span class="ev" style="display:inline-block">${esc(x.rs)}</span></div>`:""}
${x.why&&x.why.length?`<div class="small mut">판정 근거: ${x.why.map(esc).join(" · ")}</div>`:""}
${x.ct.length?`<div class="small mut">연락처: ${x.ct.map(esc).join(", ")}</div>`:""}</div>`}
function draw(){const q=document.getElementById("q").value.trim().toLowerCase(),t=ft.value,r=document.getElementById("fr").value;
const xs=D.items.filter(x=>(!t||x.t===t)&&(!r||(rev[x.id]||"미검토")===r)&&(!q||(x.ev+" "+x.rs+" "+x.url+" "+x.loc).toLowerCase().includes(q)));
document.getElementById("cnt").textContent=`${xs.length}건 표시 / 전체 ${D.items.length}건`;document.getElementById("list").innerHTML=xs.map(card).join("")||'<p class="mut">해당하는 검출이 없습니다.</p>'}
document.addEventListener("change",e=>{if(e.target.dataset.id){rev[e.target.dataset.id]=e.target.value;save();if(document.getElementById("fr").value)draw()}else if(["ft","fr"].includes(e.target.id))draw()});
document.getElementById("q").addEventListener("input",draw);
const pc={};D.items.forEach(x=>{pc[x.url]=pc[x.url]||{};pc[x.url][x.t]=(pc[x.url][x.t]||0)+1});
document.getElementById("ptab").innerHTML=`<tr><th>쪽</th>${Object.values(D.tech).map(v=>`<th>${esc(v)}</th>`).join("")}<th>합계</th></tr>`+Object.entries(pc).sort((a,b)=>Object.values(b[1]).reduce((s,v)=>s+v,0)-Object.values(a[1]).reduce((s,v)=>s+v,0)).map(([u,c])=>`<tr><td class="loc"><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></td>${Object.keys(D.tech).map(t=>`<td>${c[t]||""}</td>`).join("")}<td><b>${Object.values(c).reduce((s,v)=>s+v,0)}</b></td></tr>`).join("");
const gk={};D.items.forEach(x=>x.ct.forEach(k=>{(gk[k]=gk[k]||[]).push(x)}));const gs=Object.entries(gk).sort((a,b)=>b[1].length-a[1].length);
document.getElementById("groups").innerHTML=gs.length?gs.map(([k,xs])=>`<div class="it" style="--c:var(--acc)"><div class="h"><b class="loc">${esc(k)}</b><span class="small mut">${xs.length}건 · ${new Set(xs.map(x=>x.url)).size}쪽 · ${[...new Set(xs.map(x=>D.tech[x.t]))].map(esc).join(", ")}</span></div><div class="small">${xs.map(x=>esc(x.id)).join(", ")}</div></div>`).join(""):'<p class="mut">연락처가 든 검출이 없습니다.</p>';
document.getElementById("guide").innerHTML=Object.keys(D.tech).map(t=>`<div class="it" style="--c:${C[t]}"><div class="h"><span class="tag">${esc(D.tech[t])}</span><b>${by[t]||0}건</b></div><div class="act">${esc(D.action[t])}</div></div>`).join("");
document.getElementById("tabs").addEventListener("click",e=>{const v=e.target.dataset.v;if(!v)return;document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b===e.target));["list","pages","groups","guide"].forEach(n=>document.getElementById("v-"+n).classList.toggle("hide",n!==v))});
document.getElementById("csv").addEventListener("click",()=>{const rows=[["id","기법","쪽","위치","근거 원문","위장을 푼 글자","연락처","광고 점수","검토"]].concat(D.items.map(x=>[x.id,D.tech[x.t],x.url,x.loc,x.ev,x.rs,x.ct.join(" "),x.ad??"",rev[x.id]||"미검토"]));
const csv="﻿"+rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\r\n");const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="탐지결과_검토.csv";a.click()});
draw();
</script></body></html>"""


if __name__ == "__main__":
    a = sys.argv[1:]
    print(build(a[0], a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None))
