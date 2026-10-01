'use strict';
// 보충 검색: 논문 3.1의 검색 범위(언어군 × AI 용어, 제목·주제어 필드)를 넓게 재수집한다.
const fs = require('fs'); const path = require('path');
const ss = require('./kci_engine/search_service.js');
const cache = require('./kci_engine/cache_service.js');
require('./kci_engine/details_service.js'); // .env 로드
const key = process.env.KCI_API_KEY; const B = 'https://open.kci.go.kr/po/openapi/openApiSearch.kci';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const AI = ['인공지능','챗봇','ChatGPT','생성형','딥러닝','기계번역','음성인식','LLM','챗GPT','거대언어모델','대화형'];
const SETS = {
  '중국어': ['중국어','HSK','한자 교육','한자 학습','중국어 학습','어니봇','딥시크','DeepSeek','文心一言','汉语','漢語','Chinese'],
  '한국어': ['한국어교육','한국어 학습','한국어 교육','KFL','한국어능력시험','TOPIK','Korean language','국어교육','글쓰기','작문 교육'],
  '영어':   ['영어','영어교육','EFL','English','외국어교육','외국어 학습'],
};
const EXTRA = [ // 언어 표지 없이 AI 표지만으로는 너무 넓으므로, 영어 제목형 조합만 추가
  ['영어','ChatGPT EFL'],['영어','AI EFL'],['영어','chatbot English'],['영어','generative AI English'],
  ['한국어','ChatGPT Korean'],['한국어','AI Korean language'],['중국어','ChatGPT Chinese'],['중국어','AI Chinese language'],
  ['중국어','人工智能 汉语'],['중국어','ChatGPT 汉语'],['중국어','生成式 汉语'],
];
const queries = [];
for (const [g, terms] of Object.entries(SETS)) for (const t of terms) for (const a of AI) queries.push([g, `${a} ${t}`]);
for (const q of EXTRA) queries.push(q);
async function fetchPage(field, q, page) {
  const ck = cache.makeKey('articleSearch', { [field]: q, page: String(page), displayCount: '100' });
  const c = cache.get(ck); if (c.hit) return c.value;
  const u = `${B}?apiCode=articleSearch&key=${key}&${field}=${encodeURIComponent(q)}&displayCount=100&page=${page}`;
  for (let a = 1; a <= 3; a++) { try { const r = await fetch(u); if (!r.ok) throw new Error('HTTP ' + r.status); const t = await r.text(); cache.set(ck, t); return t; } catch (e) { if (a === 3) throw e; await sleep(800); } }
}
(async () => {
  const byId = new Map(); const log = [];
  for (const field of ['title', 'keyword']) for (const [g, q] of queries) {
    let total = null, got = 0, fresh = 0;
    for (let page = 1; page <= 20; page++) {
      let xml; try { xml = await fetchPage(field, q, page); } catch (e) { log.push({ field, q, group: g, error: e.message }); break; }
      if (total === null) total = ss.totalCount(xml);
      const recs = ss.parseRecords(xml); if (!recs.length) break;
      for (const p of recs) {
        got++;
        // 초록도 같이 보관(articleSearch에 초록이 들어 있음)
        if (!byId.has(p.arti_id)) { byId.set(p.arti_id, { ...p, hit_queries: [`${field}:${q}`], hint_group: g }); fresh++; }
        else byId.get(p.arti_id).hit_queries.push(`${field}:${q}`);
      }
      if (recs.length < 100) break; await sleep(250);
    }
    log.push({ field, q, group: g, total, got, fresh });
    console.error(`${field}\t${q}\ttotal=${total}\tgot=${got}\tnew=${fresh}\tacc=${byId.size}`);
    await sleep(250);
  }
  fs.writeFileSync(path.join(__dirname, '..', 'data', 'supp_search.json'), JSON.stringify([...byId.values()], null, 1));
  fs.writeFileSync(path.join(__dirname, '..', 'data', 'supp_search_log.json'), JSON.stringify(log, null, 1));
  const yrs = {}; for (const p of byId.values()) yrs[p.year] = (yrs[p.year] || 0) + 1;
  console.log('unique', byId.size, JSON.stringify(yrs));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
