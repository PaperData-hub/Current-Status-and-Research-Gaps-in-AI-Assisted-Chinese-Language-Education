'use strict';
/*
 * reextract_originals.js — 논문 1차 수집본(원본 1,470편)을 KCI articleDetail로
 * 라이브 재수집하여 캐시본과 대조(정확성 검증)하고 캐시를 갱신한다.
 * 산출: data/_reextract_originals_log.json (요약 + 차이 목록)
 */
const fs = require('fs');
const path = require('path');
const cache = require('./kci_engine/cache_service.js');
require('./kci_engine/details_service.js'); // .env 로드

const key = process.env.KCI_API_KEY;
const BASE = 'https://open.kci.go.kr/po/openapi/openApiSearch.kci';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const cdata = (s) => (s || '').replace(/<!\[CDATA\[|\]\]>/g, '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\s+/g, ' ').trim();
const tagAttr = (x, t, a, v) => {
  const m = x.match(new RegExp('<' + t + '[^>]*' + a + '="' + v + '"[^>]*>([^]*?)</' + t + '>'));
  return m ? cdata(m[1]) : '';
};
const firstTag = (x, t) => {
  const m = x.match(new RegExp('<' + t + '(?:\\s[^>]*)?>([^]*?)</' + t + '>'));
  return m ? cdata(m[1]) : '';
};
const citation = (x) => {
  const a = x.match(/<citation-count[^>]*kci="(\d+)"/);
  if (a) return parseInt(a[1], 10);
  const b = x.match(/<citation-count[^>]*>\s*(\d+)/);
  return b ? parseInt(b[1], 10) : null;
};
const summarize = (x) => ({
  ok: /<record>/.test(x) && !/<error/i.test(x),
  title: tagAttr(x, 'article-title', 'lang', 'original') || firstTag(x, 'article-title'),
  journal: firstTag(x, 'journal-name'),
  has_abs_ko: !!tagAttr(x, 'abstract', 'lang', 'original'),
  has_abs_en: !!tagAttr(x, 'abstract', 'lang', 'english'),
  cited: citation(x),
});

async function fetchLive(id) {
  const u = `${BASE}?apiCode=articleDetail&key=${key}&id=${id}`;
  for (let a = 1; a <= 3; a++) {
    try {
      const r = await fetch(u, { headers: { 'User-Agent': 'kci-reextract/1.0' } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.text();
    } catch (e) { if (a === 3) throw e; await sleep(800); }
  }
}

(async () => {
  const orig = require('../data/details.json');
  const ids = orig.map((p) => p.arti_id);
  const diffs = [], errors = [];
  let done = 0, citedChanged = 0, absGained = 0, absLost = 0, stillNoAbs = 0;
  for (const id of ids) {
    const ck = cache.makeKey('articleDetail', { id });
    const before = cache.get(ck).value || '';
    const b = before ? summarize(before) : null;
    let live;
    try { live = await fetchLive(id); }
    catch (e) { errors.push({ id, error: e.message }); await sleep(300); continue; }
    const a = summarize(live);
    if (!a.ok) { errors.push({ id, error: 'no record in live response' }); await sleep(300); continue; }
    cache.set(ck, live); // 캐시 갱신(같은 날이면 값 동일, 피인용만 최신화)
    const d = {};
    if (b) {
      if (b.cited !== a.cited) { d.cited = [b.cited, a.cited]; citedChanged++; }
      if (b.title !== a.title && b.title && a.title) d.title = [b.title, a.title];
      if (b.has_abs_ko !== a.has_abs_ko || b.has_abs_en !== a.has_abs_en) {
        d.abstract = { before: [b.has_abs_ko, b.has_abs_en], after: [a.has_abs_ko, a.has_abs_en] };
        if (!b.has_abs_ko && !b.has_abs_en && (a.has_abs_ko || a.has_abs_en)) absGained++;
        if ((b.has_abs_ko || b.has_abs_en) && !a.has_abs_ko && !a.has_abs_en) absLost++;
      }
    }
    if (!a.has_abs_ko && !a.has_abs_en) stillNoAbs++;
    if (Object.keys(d).length) diffs.push({ id, ...d });
    done++;
    if (done % 100 === 0) console.error(`  ${done}/${ids.length}  diffs=${diffs.length} err=${errors.length}`);
    await sleep(300);
  }
  const out = {
    ran_over: ids.length, live_ok: done, errors: errors.length,
    cited_changed: citedChanged, abstract_gained: absGained, abstract_lost: absLost,
    still_no_abstract: stillNoAbs,
    error_list: errors, diff_list: diffs,
  };
  fs.writeFileSync(path.join(__dirname, '..', 'data', '_reextract_originals_log.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({ ran_over: out.ran_over, live_ok: out.live_ok, errors: out.errors,
    cited_changed: out.cited_changed, abstract_gained: out.abstract_gained,
    abstract_lost: out.abstract_lost, still_no_abstract: out.still_no_abstract }));
})().catch((e) => { console.error('FATAL', e && e.message ? e.message : e); process.exit(1); });
