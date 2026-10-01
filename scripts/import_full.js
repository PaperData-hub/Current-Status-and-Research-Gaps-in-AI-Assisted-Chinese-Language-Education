'use strict';
/*
 * import_full.js — 1차 수집 후보 목록 xlsx의 5개 검색 범주 시트 전체(①~⑤, 1,644행)를 details_full.json으로 가져온다.
 * ④통번역·⑤복수언어 범주는 별도 그룹 라벨로 보존한다(언어 범주는 판정 단계에서 셋으로 정한다).
 */
const fs = require('fs');
const path = require('path');
const ix = require('./kci_engine/import_xlsx.js');
const cache = require('./kci_engine/cache_service.js');

function groupOfFull(name) {
  if (/①|중국어교육/.test(name)) return '중국어';
  if (/②|한국어교육/.test(name)) return '한국어';
  if (/③|영어교육/.test(name)) return '영어·외국어';
  if (/④|통번역/.test(name)) return '통번역';
  if (/⑤|복수언어/.test(name)) return '복수언어';
  return null; // 0.연도별분포
}

const input = path.join(__dirname, '..', 'input', 'KCI_corpus_정리.xlsx');
const zip = ix.readZip(fs.readFileSync(input));
const shared = ix.parseSharedStrings(zip.get('xl/sharedStrings.xml') ? zip.get('xl/sharedStrings.xml').toString('utf8') : '');
const sheets = ix.listSheets(zip);

const papers = [];
const perGroup = {};
for (const sh of sheets) {
  const group = groupOfFull(sh.name);
  if (!group) continue;
  const xml = zip.get(sh.file).toString('utf8');
  const relsName = sh.file.replace(/worksheets\/(sheet\d+)\.xml$/, 'worksheets/_rels/$1.xml.rels');
  const relsXml = zip.get(relsName) ? zip.get(relsName).toString('utf8') : '';
  const links = ix.parseHyperlinks(xml, relsXml);
  const rows = ix.parseSheet(xml, shared);
  const header = rows.find((r) => (r.cells[0] || '').replace(/\s/g, '') === '논문명(국문)');
  const hn = header ? header.row : 0;
  let taken = 0;
  for (const r of rows) {
    if (r.row <= hn) continue;
    if (!(r.cells[0] || '').trim()) continue;
    const p = ix.rowToPaper(r.cells, group, links[r.row] || '');
    papers.push(p);
    taken++;
  }
  perGroup[sh.name] = taken;
}

// arti_id 중복 제거(먼저 나온 것 유지)
const seen = new Set();
const deduped = [];
let dupes = 0;
for (const p of papers) {
  const key = p.arti_id || ('no-id::' + p.title_ko);
  if (seen.has(key)) { dupes++; continue; }
  seen.add(key);
  deduped.push(p);
}
fs.writeFileSync(path.join(__dirname, '..', 'data', 'details_full.json'), JSON.stringify(deduped, null, 2) + '\n');

// 캐시 커버리지 점검(articleDetail)
let cached = 0, noId = 0;
const missing = [];
for (const p of deduped) {
  if (!p.arti_id) { noId++; continue; }
  const hit = cache.get(cache.makeKey('articleDetail', { id: p.arti_id })).hit;
  if (hit) cached++; else missing.push({ id: p.arti_id, g: p.group, t: p.title_ko });
}
console.log('per-sheet:', JSON.stringify(perGroup));
console.log(JSON.stringify({ total: deduped.length, dupes, no_arti_id: noId,
  detail_cached: cached, detail_missing: missing.length }));
// ④⑤만 따로
const ext = deduped.filter((p) => p.group === '통번역' || p.group === '복수언어');
const extMissing = ext.filter((p) => p.arti_id && !cache.get(cache.makeKey('articleDetail', { id: p.arti_id })).hit);
console.log('④⑤ total:', ext.length, '| ④⑤ detail 미캐시:', extMissing.length);
fs.writeFileSync(path.join(__dirname, '..', 'data', '_details_missing.json'), JSON.stringify(missing, null, 2));
