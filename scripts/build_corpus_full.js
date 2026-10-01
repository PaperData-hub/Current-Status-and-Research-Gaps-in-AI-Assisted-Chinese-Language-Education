'use strict';
/*
 * build_corpus_full.js — 1차 수집 후보 1,644편(details_full.json, 검색 범주 ①~⑤ 전체)의 서지에
 * 상세 조회 응답(캐시)의 초록·주제어·저자·참고문헌·피인용을 보강한다. 산출: data/corpus_full_merged.json
 */
const fs = require('fs');
const path = require('path');
const cache = require('./kci_engine/cache_service.js');
const ds = require('./kci_engine/details_service.js');
const scope = require('./kci_engine/scope.js');
const orig = require('../data/details_full.json');
const SUPP = path.join(__dirname, '..', 'data', 'supp_search.json');
const supp = fs.existsSync(SUPP) ? require(SUPP) : [];

const cdata = (s) => (s || '')
  .replace(/<!\[CDATA\[|\]\]>/g, '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
  .replace(/\s+/g, ' ').trim();
const tag = (x, t) => { const m = x.match(new RegExp('<' + t + '(?:\\s[^>]*)?>([^]*?)</' + t + '>')); return m ? cdata(m[1]) : ''; };
// 논문 서지(<articleInfo>) 안의 DOI만 읽는다(CDATA 허용). 논문 쪽 DOI가 빈 태그(<doi />)일 때 참고문헌 블록의 DOI나 </doi>까지 잡히는 일을 막는다.
const articleDoi = (x) => { const a = x.match(/<articleInfo[\s>][^]*?<\/articleInfo>/); const m = a && a[0].match(/<doi(?:\s[^>\/]*)?>([^]*?)<\/doi>/); return m ? cdata(m[1]) : ''; };
const tagAttr = (x, t, a, v) => { const m = x.match(new RegExp('<' + t + '[^>]*' + a + '="' + v + '"[^>]*>([^]*?)</' + t + '>')); return m ? cdata(m[1]) : ''; };

const VAR = [
  ['쓰기', ['쓰기', '작문', '글쓰기', 'writing', 'composition']],
  ['말하기', ['말하기', '회화', '구어', 'speaking', 'oral', 'conversation']],
  ['발음', ['발음', '성조', 'pronunciation', 'tone']],
  ['듣기', ['듣기', '청해', 'listening']],
  ['읽기', ['읽기', '독해', 'reading']],
  ['어휘', ['어휘', '단어', '한자', 'vocabulary', 'lexical']],
  ['문법', ['문법', 'grammar']],
  ['번역', ['번역', '통역', 'translation', 'interpret']],
  ['평가·채점', ['평가', '채점', '문항', 'assessment', 'scoring', 'grading', 'test item']],
  ['리터러시·역량', ['리터러시', '역량', 'literacy', 'competenc']],
  ['문학·문화', ['문학', '문화', '소설', '고전', 'literature', 'culture']],
];
const MET = [
  ['실험연구', ['실험', '통제집단', '사전·사후', '사전 사후', '사전-사후', 'experiment', 'pre-test', 'post-test', 'quasi']],
  ['조사연구', ['설문', '인식 조사', '인식조사', '요구조사', 'survey', 'questionnaire', 'perception']],
  ['질적·사례', ['사례', '질적', '면담', '인터뷰', 'case study', 'qualitative', 'interview']],
  ['개발연구', ['개발', '설계', '구축', '모형', 'development', 'design', 'framework']],
  ['성능평가', ['정확도', '성능', '벤치마크', '비교 평가', 'accuracy', 'benchmark', 'evaluation of', 'performance of']],
  ['문헌·리뷰', ['동향', '문헌', '메타', '체계적', 'review', 'trend', 'meta-analysis']],
  ['코퍼스분석', ['코퍼스', '말뭉치', 'corpus']],
];
const hit = (txt, list) => { const low = txt.toLowerCase(); return list.filter(([, ps]) => ps.some((p) => low.includes(p.toLowerCase()))).map((x) => x[0]); };

const byId = new Map();
for (const p of orig) byId.set(p.arti_id, { ...p, src: '원본', orig_group: p.group, hint_group: '', hit_queries: [] });
let suppNew = 0;
for (const p of supp) {
  if (byId.has(p.arti_id)) {
    const o = byId.get(p.arti_id);
    o.hit_queries = p.hit_queries; o.src = '원본+보충'; o.hint_group = p.hint_group;
  } else {
    byId.set(p.arti_id, { ...p, src: '보충', orig_group: '', hint_group: p.hint_group });
    suppNew++;
  }
}

const rows = [];
let detOk = 0;
for (const p of byId.values()) {
  const c = cache.get(cache.makeKey('articleDetail', { id: p.arti_id }));
  const x = c.hit ? c.value : '';
  if (x) detOk++;
  const rec = x ? ds.parseRecord(x) : { kw_ko: [], kw_en: [], authors: [], references: [], ref_available: false };
  const year = x ? (parseInt(tag(x, 'pub-year'), 10) || p.year) : p.year;
  const ccAttr = x.match(/<citation-count[^>]*kci="(\d+)"/);
  const cc = x.match(/<citation-count[^>]*>\s*(\d+)/);
  const authors = rec.authors.length ? rec.authors.map((a) => (a.affil ? `${a.name}(${a.affil})` : a.name)) : (p.authors || []);
  const row = {
    arti_id: p.arti_id, src: p.src, orig_group: p.orig_group || '', hint_group: p.hint_group || '',
    rule_group: scope.tag({ ...p, keywords_ko: rec.kw_ko, keywords_en: rec.kw_en }) || '',
    title_ko: x ? (tagAttr(x, 'article-title', 'lang', 'original') || p.title_ko) : p.title_ko,
    title_en: x ? (tagAttr(x, 'article-title', 'lang', 'english') || p.title_en || '') : (p.title_en || ''),
    authors: authors.join('; '), n_authors: authors.length,
    journal: x ? (tag(x, 'journal-name') || p.journal) : p.journal,
    publisher: x ? tag(x, 'publisher-name') : '',
    year, month: x ? tag(x, 'pub-mon') : '',
    kci_field: x ? (tag(x, 'article-categories') || p.kci_field) : p.kci_field,
    kw_ko: rec.kw_ko.join('; '), kw_en: rec.kw_en.join('; '),
    abstract_ko: x ? tagAttr(x, 'abstract', 'lang', 'original') : '',
    abstract_en: x ? tagAttr(x, 'abstract', 'lang', 'english') : '',
    cited: ccAttr ? parseInt(ccAttr[1], 10) : (cc ? parseInt(cc[1], 10) : (p.cited_by_count ?? '')),
    n_refs: rec.references.length, ref_available: rec.ref_available,
    doi: x ? articleDoi(x).replace(/^https?:\/\/(dx\.)?doi\.org\//, '') : '',
    permalink: p.permalink,
    hit_queries: (p.hit_queries || []).join(' | '), detail_ok: !!x,
    references: rec.references,
  };
  const txt = [row.title_ko, row.title_en, row.kw_ko, row.kw_en, row.abstract_ko].join(' ');
  row.tag_var = hit(txt, VAR).join('; ');
  row.tag_met = hit(txt, MET).join('; ');
  row.has_ai = scope.AI_MARKERS.some((re) => re.test(txt)) ? 'Y' : 'N';
  row.has_edu = scope.EDU_MARKERS.some((re) => re.test(txt)) ? 'Y' : 'N';
  rows.push(row);
}
const gkey = (r) => r.orig_group || r.hint_group;
rows.sort((a, b) => gkey(a).localeCompare(gkey(b)) || (b.year - a.year) || a.arti_id.localeCompare(b.arti_id));
fs.writeFileSync(path.join(__dirname, '..', 'data', 'corpus_full_merged.json'), JSON.stringify(rows));
const origBy = (g) => orig.filter((p) => p.group === g).length;
console.log(JSON.stringify({
  total: rows.length, orig: orig.length, supp_new: suppNew, detail_ok: detOk,
  orig_by_group: { 중국어: origBy('중국어'), 한국어: origBy('한국어'), '영어·외국어': origBy('영어·외국어'), 통번역: origBy('통번역'), 복수언어: origBy('복수언어') },
}));
