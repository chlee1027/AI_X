// 페이지 안의 "숨김 신호가 있는 텍스트 요소" 와 "위험 어휘가 든 보이는 텍스트 요소" 를 모은다.
// 결과마다 원래 페이지 선택자, 숨김을 만든 요소, 그 요소에 실제로 적용된 CSS 규칙 원문, 잘라낸 html 조각을 준다.
// page.evaluate(PROBE, {riskyWords}) 로 호출한다.
({ riskyWords }) => {
  const HIDE_PROPS = ['display', 'visibility', 'clip', 'clip-path', 'position', 'left', 'top', 'right', 'width', 'height',
    'overflow', 'opacity', 'text-indent', 'font-size', 'transform', 'margin', 'padding', 'border', 'white-space'];
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'PATH', 'OPTION', 'HEAD', 'TITLE', 'META']);

  const ownText = (el) => {
    let s = '';
    for (const n of el.childNodes) if (n.nodeType === 3) s += n.nodeValue;
    return s.replace(/\s+/g, ' ').trim();
  };

  const isDynamicClass = (c) => /^(css|sc|jsx|svelte|emotion)-|[0-9a-f]{6,}|__[A-Za-z0-9]{5,}$/.test(c) || c.length > 40;

  const seg = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id && !/\d{3,}/.test(el.id)) return s + '#' + CSS.escape(el.id);
    const cls = [...el.classList].filter((c) => !isDynamicClass(c)).slice(0, 3);
    if (cls.length) s += cls.map((c) => '.' + CSS.escape(c)).join('');
    return s;
  };

  const nth = (el) => {
    let i = 1;
    for (let p = el.previousElementSibling; p; p = p.previousElementSibling) if (p.tagName === el.tagName) i++;
    return `:nth-of-type(${i})`;
  };

  // 문서 전체에서 유일한 가장 짧은 접미 경로
  const uniqueSelector = (el, root) => {
    const chain = [];
    for (let e = el; e && e !== root && e.nodeType === 1; e = e.parentElement) chain.push(e);
    const parts = [];
    for (let i = 0; i < chain.length; i++) {
      parts.unshift(seg(chain[i]));
      let sel = parts.join(' > ');
      try {
        const m = root.querySelectorAll(sel);
        if (m.length === 1 && m[0] === el) return sel;
      } catch (e) { /* 이상한 클래스 */ }
    }
    // 실패 시 nth-of-type 보강
    const parts2 = [];
    for (let i = 0; i < chain.length; i++) {
      parts2.unshift(seg(chain[i]) + nth(chain[i]));
      const sel = parts2.join(' > ');
      try {
        const m = root.querySelectorAll(sel);
        if (m.length === 1 && m[0] === el) return sel;
      } catch (e) { }
    }
    return null;
  };

  // 숨김 원인 판정 (자기 자신 또는 조상)
  const hideReason = (el) => {
    // display:none 조상이 있으면 그 안의 크기 0 은 부작용이므로 조상을 원인으로 잡는다
    for (let e = el, depth = 0; e && e !== document.documentElement; e = e.parentElement, depth++) {
      if (getComputedStyle(e).display === 'none') return { el: e, depth, reasons: ['display:none'] };
    }
    for (let e = el, depth = 0; e && e !== document.documentElement; e = e.parentElement, depth++) {
      const cs = getComputedStyle(e);
      const r = e.getBoundingClientRect();
      const reasons = [];
      if (cs.display === 'none') reasons.push('display:none');
      if (depth === 0 && cs.visibility === 'hidden') reasons.push('visibility:hidden');
      if (parseFloat(cs.opacity) === 0) reasons.push('opacity:0');
      if (cs.clip && /rect\(\s*0(px)?[\s,]+0(px)?[\s,]+0(px)?[\s,]+0(px)?\s*\)|rect\(\s*1px[\s,]+1px[\s,]+1px[\s,]+1px\s*\)/.test(cs.clip) && cs.position !== 'static') reasons.push('clip:' + cs.clip);
      if (cs.clipPath && /inset\(\s*(50|100)%/.test(cs.clipPath)) reasons.push('clip-path:' + cs.clipPath);
      if (cs.display !== 'none' && r.width <= 1 && r.height <= 1 && cs.overflow.includes('hidden')) reasons.push(`size:${r.width}x${r.height}+overflow:hidden`);
      if (cs.position === 'absolute' || cs.position === 'fixed') {
        if (parseFloat(cs.left) <= -999 || parseFloat(cs.top) <= -999) reasons.push(`offset:left=${cs.left},top=${cs.top}`);
      }
      if (parseFloat(cs.textIndent) <= -999) reasons.push('text-indent:' + cs.textIndent);
      if (depth === 0 && parseFloat(cs.fontSize) <= 1) reasons.push('font-size:' + cs.fontSize);
      if (reasons.length) return { el: e, depth, reasons };
    }
    return null;
  };

  // 적용 규칙 원문 수집 (같은 출처·--disable-web-security 일 때 교차 출처 시트도 읽힌다)
  const matchedRules = (el) => {
    const out = [];
    const visit = (rules, media) => {
      for (const rule of rules) {
        if (rule.type === 1) { // style rule
          let ok = false;
          try { ok = el.matches(rule.selectorText); } catch (e) { }
          if (!ok) continue;
          const props = [];
          for (let i = 0; i < rule.style.length; i++) props.push(rule.style[i]);
          if (!props.some((p) => HIDE_PROPS.some((h) => p === h || p.startsWith(h + '-')))) continue;
          out.push({ text: rule.cssText, media, sheet: (rule.parentStyleSheet && rule.parentStyleSheet.href) || 'inline' });
        } else if (rule.type === 4) { // media
          if (window.matchMedia(rule.media.mediaText).matches) {
            try { visit(rule.cssRules, rule.media.mediaText); } catch (e) { }
          }
        } else if (rule.cssRules) {
          try { visit(rule.cssRules, media); } catch (e) { }
        }
      }
    };
    for (const sh of document.styleSheets) {
      try { visit(sh.cssRules, null); } catch (e) { out.push({ text: null, media: null, sheet: sh.href, error: 'unreadable' }); }
    }
    return out;
  };

  // 조상 depth 단까지 자르고 무관한 형제는 버린 html 조각
  const snippet = (el, depth) => {
    let node = el.cloneNode(true);
    let cur = el;
    for (let i = 0; i < depth && cur.parentElement && cur.parentElement !== document.body && cur.parentElement !== document.documentElement; i++) {
      cur = cur.parentElement;
      const shell = cur.cloneNode(false);
      shell.appendChild(node);
      node = shell;
    }
    // 이미지·스크립트 같은 장식 제거
    node.querySelectorAll('script,style,noscript,svg,img,iframe,video').forEach((n) => n.remove());
    return { html: node.outerHTML, top: cur };
  };

  const results = [];
  const all = document.body ? document.body.querySelectorAll('*') : [];
  for (const el of all) {
    if (SKIP_TAGS.has(el.tagName.toUpperCase())) continue;
    const t = ownText(el);
    if (t.length < 2) continue;
    const hr = hideReason(el);
    const risky = riskyWords.filter((w) => t.includes(w));
    if (!hr && !risky.length) continue;
    const sel = uniqueSelector(el, document);
    const hideEl = hr ? hr.el : null;
    const rules = hideEl ? matchedRules(hideEl) : [];
    const depth = Math.min(Math.max(3, hr ? hr.depth : 0), 8);
    const sn = snippet(el, depth);
    results.push({
      kind: hr ? 'hidden' : 'risky_visible',
      text: t.slice(0, 500),
      tag: el.tagName.toLowerCase(),
      selector: sel,
      hide_reasons: hr ? hr.reasons : [],
      hide_depth: hr ? hr.depth : null,
      hide_selector: hideEl ? uniqueSelector(hideEl, document) : null,
      hide_tag: hideEl ? seg(hideEl) : null,
      aria_hidden: !!el.closest('[aria-hidden="true"]'),
      in_nav: !!el.closest('nav,header,#gnb,.gnb,.lnb,#lnb,.menu,.depth2,.sub_menu,.submenu,ul.depth2'),
      in_modal: !!el.closest('[role="dialog"],.modal,.popup,.layer,.layer_pop,.pop'),
      rules,
      inline_style: hideEl ? (hideEl.getAttribute('style') || '') : '',
      snippet_html: sn.html.slice(0, 6000),
      snippet_depth: depth,
      risky,
    });
  }
  return results;
}
