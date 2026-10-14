// 페이지(또는 iframe 문서) 전체의 요소별 계산 스타일·글자·위치를 모은다. dev/probe.py 의 조각용 수집과 같은 칸.
// window.__probeEls 에 요소 배열을 남겨 두고, 나중에 __probeSel(i) 로 요강 형식 유일 선택자를 만든다.
() => {
  const body = document.body || document.documentElement;
  const metas = [...document.querySelectorAll('head meta[name], head meta[property], head title')];
  const all = [body, ...body.querySelectorAll('*')].filter(e => !['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(e.tagName)).slice(0, 6000);
  const els = [...all, ...metas];
  const idx = new Map(els.map((e, i) => [e, i]));
  window.__probeEls = els;
  const rgba = s => { const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const cache = new Map();
  function info(e) {
    if (cache.has(e)) return cache.get(e);
    const cs = getComputedStyle(e);
    const par = (e === body || !idx.has(e.parentElement)) ? null : e.parentElement;
    const pi = par ? info(par) : null;
    const bg = rgba(cs.backgroundColor);
    const r = {
      cum_op: (pi ? pi.cum_op : 1) * parseFloat(cs.opacity),
      disp_none: (pi ? pi.disp_none : false) || cs.display === 'none',
      eff_bg: (bg && bg[3] > 0.5) ? bg : (pi ? pi.eff_bg : [255, 255, 255, 1]),
      bg_img: (pi ? pi.bg_img : false) || (cs.backgroundImage && cs.backgroundImage !== 'none'),
    };
    cache.set(e, r); return r;
  }
  const out = [];
  for (const e of els) {
    const isMeta = e.tagName === 'META' || (e.tagName === 'TITLE' && e.parentElement && e.parentElement.tagName === 'HEAD');
    let own = '';
    for (const n of e.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    if (isMeta) {
      out.push({i: idx.get(e), parent: -1, tag: e.tagName.toLowerCase(), own: e.tagName === 'TITLE' ? own.slice(0, 600) : '',
        text: e.tagName === 'TITLE' ? own.slice(0, 600) : '', href: '', attr_content: (e.getAttribute('content') || '').slice(0, 600),
        meta_key: e.tagName === 'TITLE' ? 'title' : (e.getAttribute('name') || e.getAttribute('property') || ''), pseudo: '',
        display: 'none', visibility: 'visible', opacity: 1, color: [0, 0, 0, 1], tfill: '', bgclip: '', font_size: 16,
        position: 'static', left: 'auto', top: 'auto', text_indent: 0, transform: 'none', clip: 'auto', clip_path: 'none',
        overflow: 'visible', x: 0, y: 0, w: 0, h: 0, cum_op: 1, disp_none: false, eff_bg: [255, 255, 255, 1], bg_img: false, meta: true});
      continue;
    }
    const cs = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    const inf = info(e);
    out.push({
      i: idx.get(e), parent: (e === body || !idx.has(e.parentElement)) ? -1 : idx.get(e.parentElement),
      tag: e.tagName.toLowerCase(), own: own.slice(0, 600), text: (e.textContent || '').slice(0, 1500),
      href: e.href && typeof e.href === 'string' ? e.href : (e.getAttribute('href') || ''),
      attr_content: '', meta_key: '',
      pseudo: ['::before', '::after'].map(ps => { const c = getComputedStyle(e, ps).content;
        return (!c || c === 'none' || c === 'normal') ? '' : (/^["']/.test(c) ? c.slice(1, -1) : c); }).join(' ').trim().slice(0, 300),
      display: cs.display, visibility: cs.visibility, opacity: parseFloat(cs.opacity),
      color: rgba(cs.color), tfill: cs.webkitTextFillColor || '', bgclip: cs.webkitBackgroundClip || cs.backgroundClip || '',
      font_size: parseFloat(cs.fontSize), position: cs.position, left: cs.left, top: cs.top,
      text_indent: parseFloat(cs.textIndent) || 0, transform: cs.transform, clip: cs.clip, clip_path: cs.clipPath,
      overflow: cs.overflow, x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height,
      cum_op: inf.cum_op, disp_none: inf.disp_none, eff_bg: inf.eff_bg, bg_img: inf.bg_img,
    });
  }
  // 요강 형식 선택자: 태그 + 클래스, 형제 사이 모호하면 :nth-of-type(k), 아래에서 위로 붙여 유일해지면 멈춘다
  window.__probeSel = (i) => {
    const e = window.__probeEls[i];
    if (!e) return '';
    if (e.tagName === 'META') {
      const n = e.getAttribute('name'), p = e.getAttribute('property');
      return n ? `meta[name="${n}"]` : `meta[property="${p}"]`;
    }
    if (e.tagName === 'TITLE') return 'title';
    const step = (x) => {
      let s = x.tagName.toLowerCase();
      const cls = [...x.classList].filter(c => /^[A-Za-z_][\w-]*$/.test(c)).slice(0, 2);
      if (cls.length) s += '.' + cls.join('.');
      const p = x.parentElement;
      if (p) {
        const same = [...p.children].filter(c => c.tagName === x.tagName && (cls.length === 0 || cls.every(k => c.classList.contains(k))));
        if (same.length > 1) {
          const k = [...p.children].filter(c => c.tagName === x.tagName).indexOf(x) + 1;
          s += `:nth-of-type(${k})`;
        }
      }
      return s;
    };
    let parts = [], cur = e;
    while (cur && cur !== document.documentElement) {
      if (cur.id && /^[A-Za-z][\w-]*$/.test(cur.id) && document.querySelectorAll('#' + cur.id).length === 1) {
        parts.unshift(cur.tagName.toLowerCase() + '#' + cur.id);
      } else {
        parts.unshift(step(cur));
      }
      const sel = parts.join(' > ');
      let n = 0;
      try { n = document.querySelectorAll(sel).length; } catch (err) { n = 0; }
      if (n === 1 && document.querySelector(sel) === e) return sel;
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  };
  return out;
}
