#!/usr/bin/env node
'use strict';
/*
 * search_service.js — accept.best 1.1 "통합 논문 검색" (KCI articleSearch)
 *
 * 키워드 리스트를 articleSearch로 페이지네이션하며 훑어, 중복·제외ID를 걸러
 * models.Paper 표준 객체 배열을 반환한다. 스코프(중/한/영 분류)나 화이트리스트
 * 필터는 하지 않는다 — 여기는 "순수 검색"이고, 도메인 판정은 scope.js의 몫이다.
 *
 * Paper 데이터 계약(서비스 공통):
 *   { arti_id, title_ko, title_en, authors:[], journal, year,
 *     keywords_ko:[], keywords_en:[], kci_field, permalink, group, source:"kci" }
 *
 * 주의: articleSearch 응답에는 키워드가 없다(초록·분류·저자·연도까지만).
 *       keywords_ko/en 은 []로 두고, matrix_service.enrich(articleDetail)에서 보강한다.
 *
 * 실제 응답 XML 구조(확인됨):
 *   <record>
 *     <journalInfo><journal-name/><pub-year/><pub-mon/>…</journalInfo>
 *     <articleInfo article-id="ART003093937">
 *       <article-categories/> <title-group><article-title lang="original|english"/></title-group>
 *       <author-group><author english="…">이름(소속)</author></author-group>
 *       <abstract-group><abstract lang="original|english"/></abstract-group>
 *       <url><![CDATA[…artiId=ART…]]></url> <doi/> …
 *     </articleInfo>
 *   </record>
 *
 * 사용:
 *   const { search } = require('./kci_engine/search_service');
 *   const papers = await search({ keywords: ['ChatGPT 영어교육'], excludeIds, maxPages: 10 });
 */

const fs = require('fs');
const path = require('path');
const cache = require('./cache_service'); // 30일 응답 캐시(순수 fs) — articleSearch fetch 를 감싼다.

// ------------------------------------------------------------------ .env 로더
// python-dotenv/외부 의존성 없이 표준 라이브러리만으로 .env를 읽어 process.env에 채운다.
// 스크립트 상위 폴더(레포 루트) → 현재 작업 폴더 순. 이미 설정된 값은 덮어쓰지 않는다.
function loadDotenv() {
  const candidates = [path.join(__dirname, '..', '..', '.env'), path.join(process.cwd(), '.env')];
  for (const p of candidates) {
    if (!fs.existsSync(p)) continue;
    for (let line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
      line = line.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) continue;
      if (line.toLowerCase().startsWith('export ')) line = line.slice(7);
      const i = line.indexOf('=');
      const k = line.slice(0, i).trim();
      const v = line.slice(i + 1).trim().replace(/^["']|["']$/g, '');
      if (k && !(k in process.env)) process.env[k] = v;
    }
  }
}
loadDotenv();

// ------------------------------------------------------------------ CONFIG
const BASE = process.env.KCI_DIRECT_BASE || 'https://open.kci.go.kr/po/openapi/openApiSearch.kci';
const PERMA = 'https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=';
const ARTID_RE = /ART\d{9,}/;
const PAGE_SIZE = 100;   // 한 페이지 요청 건수 (명세서 최대치)
const SLEEP_MS = 300;    // 호출 간 대기 — 서버 예의

// ------------------------------------------------------------------ 검색 필드 CONFIG (과제⑦)
// articleSearch 요청 파라미터명. KCI Open API 활용가이드(openApiConnSearch.kci 파라미터 표)로
// 확정. 하드코딩 대신 상수로 모아 두어 필드명이 바뀌면 여기 한 곳만 고친다.
//   - title 은 기존에 실측 확인됨. author/journal/keyword 는 공식 문서로 확정.
//   (본 환경엔 KCI_API_KEY 가 없어 라이브 재확인은 불가 → 문서 기준 확정.)
const SEARCH_FIELDS = Object.freeze({
  title: 'title',       // 논문 제목
  author: 'author',     // 저자명
  journal: 'journal',   // 학술지명
  keyword: 'keyword',   // 키워드
});
// 페이지네이션 파라미터명.
const PARAM = Object.freeze({
  page: 'page',
  count: 'displayCount',
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const cdata = (s) => (s || '').replace(/<!\[CDATA\[|\]\]>/g, '').trim();
const pick = (block, re) => { const m = block.match(re); return m ? cdata(m[1]) : ''; };

// ------------------------------------------------------------------ 파싱
// articleSearch XML 한 응답을 Paper[] 로 변환. 정규식 기반이라 태그 일부가
// 달라져도(article-id는 /ART\d{9,}/로 견고 추출) 최대한 살아남는다.
function parseRecords(xml) {
  const out = [];
  for (const m of (xml || '').matchAll(/<record>([\s\S]*?)<\/record>/g)) {
    const b = m[1];
    const idm = b.match(/article-id="(ART\d{9,})"/);
    const fallback = b.match(ARTID_RE);
    const arti_id = idm ? idm[1] : (fallback ? fallback[0] : null);
    if (!arti_id) continue;

    const title_ko = pick(b, /<article-title lang="original">([\s\S]*?)<\/article-title>/);
    const title_en = pick(b, /<article-title lang="english">([\s\S]*?)<\/article-title>/) || null;

    // <author english="…">이름(소속)</author> → 이름만 (끝의 (소속) 제거)
    const authors = [...b.matchAll(/<author(?:\s[^>]*)?>([\s\S]*?)<\/author>/g)]
      .map((a) => cdata(a[1]).replace(/\s*\([^)]*\)\s*$/, '').trim())
      .filter(Boolean);

    const journal = pick(b, /<journal-name>([\s\S]*?)<\/journal-name>/) || null;
    const yearStr = pick(b, /<pub-year>([\s\S]*?)<\/pub-year>/);
    const year = /^\d{4}$/.test(yearStr) ? parseInt(yearStr, 10) : null;
    const kci_field = pick(b, /<article-categories>([\s\S]*?)<\/article-categories>/) || null;

    const urlTag = pick(b, /<url>([\s\S]*?)<\/url>/);
    const permalink = urlTag || (PERMA + arti_id);

    out.push({
      arti_id,
      title_ko,
      title_en,
      authors,
      journal,
      year,
      keywords_ko: [], // articleSearch 미제공 → matrix_service.enrich에서 보강
      keywords_en: [],
      kci_field,
      permalink,
      group: null,     // 스코프 판정은 scope.js 담당
      source: 'kci',
    });
  }
  return out;
}

// 응답의 총 검색건수(<total>) — 페이지네이션 참고용.
function totalCount(xml) {
  const m = (xml || '').match(/<total>\s*(\d+)\s*<\/total>/);
  return m ? parseInt(m[1], 10) : null;
}

// ------------------------------------------------------------------ API 호출
async function fetchPage({ keyword, page, displayCount = PAGE_SIZE }) {
  const key = process.env.KCI_API_KEY;
  if (!key) throw new Error('KCI_API_KEY 없음 — .env 또는 환경변수를 확인하세요.');

  // 캐시 키에는 인증키를 넣지 않는다(비밀·가변 배제, 키 회전에도 캐시 안정).
  const cacheKey = cache.makeKey('articleSearch', {
    [SEARCH_FIELDS.title]: keyword,
    [PARAM.page]: String(page),
    [PARAM.count]: String(displayCount),
  });
  const cached = cache.get(cacheKey);
  if (cached.hit) return cached.value; // 히트 → 네트워크 스킵

  const q = new URLSearchParams({
    apiCode: 'articleSearch',
    key,
    [SEARCH_FIELDS.title]: keyword,
    [PARAM.count]: String(displayCount),
    [PARAM.page]: String(page),
  });
  const res = await fetch(`${BASE}?${q}`, { headers: { 'User-Agent': 'kci-search-service/1.0' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`); // 실패 응답은 캐시하지 않음
  const text = await res.text();
  cache.set(cacheKey, text); // 미스 → 저장
  return text;
}

// ------------------------------------------------------------------ 공개 API
/**
 * 여러 키워드를 훑어 중복 제거된 Paper[]를 반환한다.
 * @param {object} opts
 * @param {string|string[]} opts.keywords  검색어(단일 문자열 또는 배열)
 * @param {string[]} [opts.excludeIds]     이미 보유한 arti_id(코퍼스) — 결과에서 제외
 * @param {number}  [opts.maxPages]        키워드당 최대 페이지 수
 * @returns {Promise<Array>} Paper[]
 */
async function search({ keywords, excludeIds = [], maxPages = 100 } = {}) {
  if (!keywords) throw new Error('search: keywords 인자가 필요합니다.');
  const kws = Array.isArray(keywords) ? keywords : [keywords];
  const exclude = new Set(excludeIds);
  const byId = new Map(); // arti_id -> Paper (최초 발견 유지)

  for (const kw of kws) {
    for (let page = 1; page <= maxPages; page++) {
      let xml;
      try {
        xml = await fetchPage({ keyword: kw, page });
      } catch (e) {
        console.error(`  [err] '${kw}' p${page}: ${e.message}`);
        break;
      }
      const recs = parseRecords(xml);
      if (!recs.length) break;
      for (const p of recs) {
        if (exclude.has(p.arti_id) || byId.has(p.arti_id)) continue;
        byId.set(p.arti_id, p);
      }
      if (recs.length < PAGE_SIZE) break; // 마지막 페이지
      await sleep(SLEEP_MS);
    }
    await sleep(SLEEP_MS);
  }
  return [...byId.values()];
}

module.exports = { search, parseRecords, totalCount, PAGE_SIZE, PERMA, SEARCH_FIELDS, PARAM };

// ------------------------------------------------------------------ 데모
if (require.main === module) {
  (async () => {
    const demo = ['생성형 인공지능 교육', 'ChatGPT 영어교육', '인공지능 한국어교육'];
    console.log(`데모: ${demo.length}개 키워드 × 1페이지 검색…`);
    const papers = await search({ keywords: demo, maxPages: 1 });
    console.log(`→ 고유 ${papers.length}건`);
    for (const p of papers.slice(0, 5)) {
      console.log(`  ${p.arti_id}  ${p.year || '----'}  [${p.kci_field || '-'}]  ${(p.title_ko || '').slice(0, 40)}`);
    }
  })();
}
