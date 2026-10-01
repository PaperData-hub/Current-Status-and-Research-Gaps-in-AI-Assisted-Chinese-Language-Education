#!/usr/bin/env node
'use strict';
/*
 * details_service.js — [0단계] 상세 보강 확장 (신규 분석 3종의 전제)
 *
 *   articleDetail 응답(캐시된 XML)에서 각 arti_id에 대해
 *     (a) 저자키워드(국/영),
 *     (b) 전체 저자 목록 [{name, name_en, affil}],
 *     (c) 참고문헌 목록 [{title, author, journal, year, type, doi, url, arti_id?}]
 *   를 파싱해 arti_id로 키잉한 보강 맵을 만든다.
 *
 *   ⚠ 파일명 주의: 레포의 data/details.json 은 이미 "코퍼스 마스터(Paper[] 배열)"로
 *   run_local.js 파이프라인의 입력이다. 이를 덮어쓰면 파이프라인이 깨지므로,
 *   본 0단계 산출물은 arti_id 키맵으로 별도 파일 data/details_enriched.json 에 쓴다.
 *   (작업지시서 schema: details.json = { artiId: {kw_ko,kw_en,authors,references} })
 *
 *   결정론적 순수 파서. articleDetail 은 이미 matrix_service.enrich 로 전수 캐시되어
 *   있어(1281편) 네트워크 호출이 필요 없다. 캐시에 없는 id 만 라이브 fetch 를
 *   시도한다(호출간 0.5s·3회 재시도·id별 캐시로 이어받기). 캐시가 완전하면 순수 함수.
 *
 * export:
 *   parseAuthors(xml)     → [{name, name_en, affil}]      (author-group 한정)
 *   parseReferences(xml)  → [{title, author, journal, year, type, type_code, doi, url, arti_id}]
 *   parseKeywords(xml)    → {kw_ko:[], kw_en:[]}
 *   buildFromCache(papers,{cacheDir}) → { [artiId]: {kw_ko,kw_en,authors,references,ref_available} }
 *   buildDetails(papers,{cacheDir,live}) → 위와 동일(캐시 미스 시 live fetch 옵션)
 *   coverage(details)     → 커버리지 수치
 */
const fs = require('fs');
const path = require('path');
const cache = require('./cache_service');

const SLEEP_MS = 500;      // 작업지시서: 호출간 0.5s
const MAX_RETRY = 3;       // 실패 3회 재시도
const BASE = 'https://open.kci.go.kr/po/openapi/openApiSearch.kci';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── .env 로드(라이브 fetch 시 KCI_API_KEY) ──────────────────────────────────
(function loadEnv() {
  const p = path.join(__dirname, '..', '..', '.env');
  if (!fs.existsSync(p)) return;
  for (let line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    line = line.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const i = line.indexOf('=');
    const k = line.slice(0, i).trim();
    if (!(k in process.env)) process.env[k] = line.slice(i + 1).trim();
  }
})();

// ── XML 유틸 (matrix_service 파서 규약과 동일) ───────────────────────────────
function cdata(s) {
  return (s || '')
    .replace(/<!\[CDATA\[|\]\]>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}
const hasHangul = (s) => /[가-힣]/.test(s);

/** 첫 번째 매칭 태그의 내부 텍스트(없으면 ''). */
function firstTag(xml, tag) {
  const m = xml.match(new RegExp('<' + tag + '(?:\\s[^>]*)?>([\\s\\S]*?)</' + tag + '>'));
  return m ? cdata(m[1]) : '';
}
/** 여는 태그의 특정 attribute 값(없으면 ''). openTag = '<author ...>' 문자열. */
function attr(openTag, name) {
  const m = openTag.match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1] : '';
}
/** xml 에서 <block>...</block> 의 내부만 잘라 반환(없으면 ''). */
function sliceBlock(xml, block) {
  const m = xml.match(new RegExp('<' + block + '(?:\\s[^>]*)?>([\\s\\S]*?)</' + block + '>'));
  return m ? m[1] : '';
}

// ── (a) 저자키워드 ───────────────────────────────────────────────────────────
function parseKeywords(xml) {
  const kw_ko = [];
  const kw_en = [];
  const seenKo = new Set();
  const seenEn = new Set();
  const group = sliceBlock(xml, 'keyword-group') || xml;
  for (const m of group.matchAll(/<keyword>([\s\S]*?)<\/keyword>/g)) {
    const kw = cdata(m[1]);
    if (!kw) continue;
    if (hasHangul(kw)) { if (!seenKo.has(kw)) { seenKo.add(kw); kw_ko.push(kw); } }
    else { if (!seenEn.has(kw)) { seenEn.add(kw); kw_en.push(kw); } }
  }
  return { kw_ko, kw_en };
}

// ── (b) 전체 저자 목록 — author-group 한정(참고문헌 author 와 섞이지 않게) ─────
function parseAuthors(xml) {
  const block = sliceBlock(xml, 'author-group');
  if (!block) return [];
  const out = [];
  // 각 <author ...> ... </author> 단위로 파싱
  for (const m of block.matchAll(/<author(\s[^>]*)?>([\s\S]*?)<\/author>/g)) {
    const inner = m[2];
    const name = firstTag(inner, 'name');
    const name_en = firstTag(inner, 'name-eng');
    const affil = firstTag(inner, 'institution');
    if (!name && !name_en) continue;
    out.push({ name, name_en, affil });
  }
  return out;
}

// ── (c) 참고문헌 목록 ────────────────────────────────────────────────────────
function parseReferences(xml) {
  const block = sliceBlock(xml, 'referenceInfo');
  if (!block) return [];
  const out = [];
  for (const m of block.matchAll(/<reference(\s[^>]*)?>([\s\S]*?)<\/reference>/g)) {
    const openAttrs = m[1] || '';
    const inner = m[2];
    const yr = firstTag(inner, 'pubi-year') || firstTag(inner, 'registration-day');
    const year = /\d{4}/.test(yr) ? parseInt(yr.match(/\d{4}/)[0], 10) : null;
    out.push({
      title: firstTag(inner, 'title'),
      author: firstTag(inner, 'author'),
      journal: firstTag(inner, 'journal-name') || firstTag(inner, 'conference-name'),
      publisher: firstTag(inner, 'pubilisher'),
      year,
      type: attr(openAttrs, 'type-name'),
      type_code: attr(openAttrs, 'type-code'),
      doi: firstTag(inner, 'doi'),
      url: firstTag(inner, 'url'),
      arti_id: attr(openAttrs, 'arti-id') || null, // KCI 내부 논문이면 존재
    });
  }
  return out;
}

// ── 한 XML → 보강 레코드 ─────────────────────────────────────────────────────
function parseRecord(xml) {
  const { kw_ko, kw_en } = parseKeywords(xml);
  const references = parseReferences(xml);
  return {
    kw_ko,
    kw_en,
    authors: parseAuthors(xml),
    references,
    ref_available: /<referenceInfo/.test(xml), // 참고문헌 블록 존재 여부(0편이어도 구분)
  };
}

// ── 라이브 fetch (캐시 미스 전용, 3회 재시도) ────────────────────────────────
async function fetchDetailText(artiId) {
  const cacheKey = cache.makeKey('articleDetail', { id: artiId });
  const cached = cache.get(cacheKey);
  if (cached.hit) return cached.value;
  const key = process.env.KCI_API_KEY;
  if (!key) return null; // 키 없으면 라이브 불가 → 스킵(할루시네이션 금지)
  for (let attempt = 1; attempt <= MAX_RETRY; attempt++) {
    try {
      const q = new URLSearchParams({ apiCode: 'articleDetail', key, id: artiId });
      const res = await fetch(`${BASE}?${q}`, { headers: { 'User-Agent': 'kci-details/1.0' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const text = await res.text();
      cache.set(cacheKey, text); // 성공만 캐시(이어받기)
      return text;
    } catch (e) {
      if (attempt < MAX_RETRY) await sleep(SLEEP_MS);
    }
  }
  return null;
}

/**
 * 캐시만으로 보강 맵 생성(순수·결정론적). arti_id 오름차순으로 순회.
 * @param {Array} papers  코퍼스 Paper[] (arti_id·keywords 보유)
 * @param {{cacheDir?:string}} [opts]
 * @returns {Object} { [artiId]: {kw_ko,kw_en,authors,references,ref_available} }
 */
function buildFromCache(papers, opts = {}) {
  const cacheOpts = opts.cacheDir ? { dir: opts.cacheDir } : {};
  const ids = (Array.isArray(papers) ? papers : [])
    .map((p) => p && p.arti_id).filter(Boolean)
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort();
  const byId = {};
  for (const p of papers || []) if (p && p.arti_id) byId[p.arti_id] = p;

  const details = {};
  for (const id of ids) {
    const cacheKey = cache.makeKey('articleDetail', { id });
    const hit = cache.get(cacheKey, cacheOpts);
    const rec = hit.hit ? parseRecord(hit.value)
      : { kw_ko: [], kw_en: [], authors: [], references: [], ref_available: false };
    // 코퍼스에 이미 있는 키워드로 보완(캐시 파싱이 비면 코퍼스 값 사용).
    const p = byId[id] || {};
    if (rec.kw_ko.length === 0 && Array.isArray(p.keywords_ko)) rec.kw_ko = p.keywords_ko.slice();
    if (rec.kw_en.length === 0 && Array.isArray(p.keywords_en)) rec.kw_en = p.keywords_en.slice();
    // 저자도 캐시가 비면 코퍼스 저자명(소속 없음)으로 최소 보완.
    if (rec.authors.length === 0 && Array.isArray(p.authors)) {
      rec.authors = p.authors.map((n) => ({ name: String(n), name_en: '', affil: '' }));
    }
    details[id] = rec;
  }
  return details;
}

/**
 * 캐시 우선 + 미스 시 라이브 fetch(옵션). 결과는 buildFromCache 와 동일 형태.
 * @param {Array} papers
 * @param {{cacheDir?:string, live?:boolean}} [opts]
 */
async function buildDetails(papers, opts = {}) {
  if (opts.live) {
    const ids = (Array.isArray(papers) ? papers : [])
      .map((p) => p && p.arti_id).filter(Boolean);
    let fetched = 0;
    for (let i = 0; i < ids.length; i++) {
      const cacheKey = cache.makeKey('articleDetail', { id: ids[i] });
      if (cache.get(cacheKey).hit) continue;
      if (fetched > 0) await sleep(SLEEP_MS);
      fetched++;
      await fetchDetailText(ids[i]); // 캐시에 채워둔다
    }
  }
  return buildFromCache(papers, opts);
}

// ── 커버리지 리포트 ──────────────────────────────────────────────────────────
function coverage(details) {
  const entries = Object.entries(details || {});
  const total = entries.length;
  let hasKw = 0, hasAuthorAffil = 0, hasRef = 0, refBlock = 0, refCount = 0, authorCount = 0;
  for (const [, d] of entries) {
    if ((d.kw_ko && d.kw_ko.length) || (d.kw_en && d.kw_en.length)) hasKw++;
    if (Array.isArray(d.authors) && d.authors.some((a) => a.affil)) hasAuthorAffil++;
    if (d.ref_available) refBlock++;
    if (Array.isArray(d.references) && d.references.length) { hasRef++; refCount += d.references.length; }
    authorCount += Array.isArray(d.authors) ? d.authors.length : 0;
  }
  return {
    total,
    keywords: hasKw,
    authors_with_affil: hasAuthorAffil,
    author_total: authorCount,
    references_block_present: refBlock,
    references_nonempty: hasRef,
    references_total: refCount,
  };
}

module.exports = {
  parseKeywords, parseAuthors, parseReferences, parseRecord,
  buildFromCache, buildDetails, coverage,
};

// ── CLI ──────────────────────────────────────────────────────────────────────
if (require.main === module) {
  (async () => {
    const argv = process.argv.slice(2);
    const live = argv.includes('--live');
    const corpusPath = argv.find((a) => !a.startsWith('--')) || path.join(__dirname, '..', 'data', 'details.json');
    const outPath = path.join(__dirname, '..', 'data', 'details_enriched.json');
    if (!fs.existsSync(corpusPath)) {
      console.error('코퍼스 없음:', corpusPath); process.exit(1);
    }
    const papers = JSON.parse(fs.readFileSync(corpusPath, 'utf8'));
    console.log(`[0단계] 상세 보강 확장 — 코퍼스 ${papers.length}편, 캐시 우선${live ? ' + 라이브 미스보강' : ''}`);
    const details = await buildDetails(papers, { live });
    fs.writeFileSync(outPath, JSON.stringify(details, null, 2) + '\n', 'utf8');
    const c = coverage(details);
    console.log(`✓ 산출 → ${path.relative(path.join(__dirname, '..'), outPath)}`);
    console.log('── 커버리지 ─────────────────────────────');
    console.log(`  전체 논문            : ${c.total}`);
    console.log(`  키워드 보유          : ${c.keywords} (${(100 * c.keywords / c.total).toFixed(1)}%)`);
    console.log(`  저자 소속 보유       : ${c.authors_with_affil} (${(100 * c.authors_with_affil / c.total).toFixed(1)}%)  · 저자 연인원 ${c.author_total}`);
    console.log(`  참고문헌 블록 존재   : ${c.references_block_present} (${(100 * c.references_block_present / c.total).toFixed(1)}%)`);
    console.log(`  참고문헌 보유(≥1)    : ${c.references_nonempty} · 참고문헌 총 ${c.references_total}건`);
  })().catch((e) => { console.error('[details] 실패:', e && e.message ? e.message : e); process.exit(1); });
}
