#!/usr/bin/env node
'use strict';
/*
 * import_xlsx.js — 수동 큐레이션한 KCI 코퍼스 엑셀(.xlsx) → data/details.json 어댑터
 *
 * 배경: 연구자가 KCI 검색·스코프 검토를 엑셀로 직접 끝낸 코퍼스를, JS 분석
 *       파이프라인(pipeline.assemble / stats / gap / coauthor / distinctive / citation)이
 *       읽는 표준 Paper[] JSON 으로 변환한다. 네트워크 없이 순수 파일 변환.
 *
 * 대상 시트: 이름이 ①/②/③ 또는 '중국어교육'/'한국어교육'/'영어교육' 을 포함하는 시트.
 *            '0. 연도별 분포'(요약)·'검토 필요'(폐기)는 건너뛴다.
 *            그룹은 시트로 확정한다(연구자가 이미 수동 검토·분류 완료 → scope.tag 재판정 안 함).
 *
 * 기대 헤더(행 어디에 있든 '논문명(국문)' 셀로 자동 탐지):
 *   논문명(국문) | 논문명(영문/키워드) | 저자1(소속) | 저자2(소속) | 학술지명(국문) |
 *   학술지명(원어) | 발행기관 | 학술지명(영문) | 발행연월 | 키워드(국문) |
 *   키워드(영문) | 분류(KCI) | KCI 주소 | 피인용
 *   (KCI 주소 칸은 표시문자 'KCI 원문' + 하이퍼링크 → URL 의 artiId 로 arti_id 확보)
 *
 * 사용:  node kci_engine/import_xlsx.js [입력.xlsx] [출력.json]
 *   기본 입력 = data/ 안의 첫 .xlsx,  기본 출력 = data/details.json
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const scope = require('./scope.js'); // GROUP 상수만 사용

// ─────────────────────────────────────────────────────── ZIP 리더 (순수 Node)
// .xlsx 는 ZIP 컨테이너. 중앙디렉터리를 걸어 필요한 엔트리만 해제한다.
function readZip(buf) {
  // End Of Central Directory 탐색(뒤에서부터)
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0 && i >= buf.length - 22 - 65536; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('EOCD 없음 — ZIP/xlsx 아님');
  const count = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  const entries = {};
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(off) !== 0x02014b50) break;
    const method = buf.readUInt16LE(off + 10);
    const compSize = buf.readUInt32LE(off + 20);
    const nameLen = buf.readUInt16LE(off + 28);
    const extraLen = buf.readUInt16LE(off + 30);
    const commentLen = buf.readUInt16LE(off + 32);
    const localOff = buf.readUInt32LE(off + 42);
    const name = buf.toString('utf8', off + 46, off + 46 + nameLen);
    entries[name] = { method, compSize, localOff };
    off += 46 + nameLen + extraLen + commentLen;
  }
  const get = (name) => {
    const e = entries[name];
    if (!e) return null;
    // 로컬 헤더에서 실제 데이터 시작 계산(가변 name/extra 길이)
    const lo = e.localOff;
    if (buf.readUInt32LE(lo) !== 0x04034b50) throw new Error('로컬헤더 불일치: ' + name);
    const lNameLen = buf.readUInt16LE(lo + 26);
    const lExtraLen = buf.readUInt16LE(lo + 28);
    const dataStart = lo + 30 + lNameLen + lExtraLen;
    const raw = buf.slice(dataStart, dataStart + e.compSize);
    return e.method === 0 ? raw : zlib.inflateRawSync(raw);
  };
  return { names: Object.keys(entries), get };
}

// ─────────────────────────────────────────────────────── XML 헬퍼
function decode(s) {
  return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
          .replace(/&apos;/g, "'").replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
          .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
          .replace(/&amp;/g, '&');
}

function parseSharedStrings(xml) {
  if (!xml) return [];
  const out = [];
  const siRe = /<si>([\s\S]*?)<\/si>/g;
  let m;
  while ((m = siRe.exec(xml))) {
    let s = '';
    const tRe = /<t[^>]*>([\s\S]*?)<\/t>/g;
    let tm;
    while ((tm = tRe.exec(m[1]))) s += tm[1];
    out.push(decode(s));
  }
  return out;
}

function colToNum(ref) { // "M5" -> 12 (0-based col)
  const m = ref.match(/^([A-Z]+)/);
  let n = 0;
  for (const ch of m[1]) n = n * 26 + (ch.charCodeAt(0) - 64);
  return n - 1;
}

// 워크시트 XML → [{ row: <spreadsheet 행번호>, cells: string[] }]
function parseSheet(xml, shared) {
  const rows = [];
  const rowRe = /<row[^>]*?\br="(\d+)"[^>]*>([\s\S]*?)<\/row>/g;
  let rm;
  while ((rm = rowRe.exec(xml))) {
    const rownum = +rm[1];
    const cells = [];
    const cRe = /<c\s+([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g;
    let cm;
    while ((cm = cRe.exec(rm[2]))) {
      const attrs = cm[1];
      const body = cm[2] || '';
      const refM = attrs.match(/r="([A-Z]+\d+)"/);
      const col = refM ? colToNum(refM[1]) : cells.length;
      const tM = attrs.match(/t="([^"]+)"/);
      const type = tM ? tM[1] : 'n';
      let val = '';
      if (type === 's') {
        const vM = body.match(/<v>([\s\S]*?)<\/v>/);
        if (vM) val = shared[+vM[1]] || '';
      } else if (type === 'inlineStr') {
        const tt = body.match(/<t[^>]*>([\s\S]*?)<\/t>/);
        if (tt) val = decode(tt[1]);
      } else if (type === 'str') {
        const vM = body.match(/<v>([\s\S]*?)<\/v>/);
        if (vM) val = decode(vM[1]);
      } else {
        const vM = body.match(/<v>([\s\S]*?)<\/v>/);
        if (vM) val = decode(vM[1]);
      }
      cells[col] = val;
    }
    rows.push({ row: rownum, cells });
  }
  return rows;
}

// 시트의 하이퍼링크: { 행번호 -> URL }  (KCI 주소 칸의 실제 링크)
function parseHyperlinks(sheetXml, relsXml) {
  const rel = {};
  if (relsXml) {
    const re = /<Relationship\b[^>]*>/g;
    let m;
    while ((m = re.exec(relsXml))) {
      const tag = m[0];
      const id = (tag.match(/Id="([^"]+)"/) || [])[1];
      const target = (tag.match(/Target="([^"]+)"/) || [])[1];
      if (id && target) rel[id] = decode(target);
    }
  }
  const byRow = {};
  const re = /<hyperlink\b[^>]*>/g;
  let m;
  while ((m = re.exec(sheetXml))) {
    const tag = m[0];
    const ref = (tag.match(/ref="([A-Z]+)(\d+)"/) || []);
    const rid = (tag.match(/r:id="([^"]+)"/) || [])[1];
    if (ref[2] && rid && rel[rid]) byRow[+ref[2]] = rel[rid];
  }
  return byRow;
}

// workbook.xml + rels → [{ name, file }] (시트 순서대로)
function listSheets(zip) {
  const wb = zip.get('xl/workbook.xml').toString('utf8');
  const rels = zip.get('xl/_rels/workbook.xml.rels').toString('utf8');
  const ridToFile = {};
  let m;
  const rRe = /<Relationship\b[^>]*>/g;
  while ((m = rRe.exec(rels))) {
    const tag = m[0];
    const id = (tag.match(/Id="([^"]+)"/) || [])[1];
    let target = (tag.match(/Target="([^"]+)"/) || [])[1];
    if (id && target) ridToFile[id] = target.replace(/^\//, '').replace(/^xl\//, '');
  }
  const sheets = [];
  const sRe = /<sheet\b[^>]*>/g;
  while ((m = sRe.exec(wb))) {
    const tag = m[0];
    const name = decode((tag.match(/name="([^"]+)"/) || [])[1] || '');
    const rid = (tag.match(/r:id="([^"]+)"/) || [])[1];
    const file = ridToFile[rid];
    sheets.push({ name, file: file.startsWith('worksheets/') ? 'xl/' + file : 'xl/' + file });
  }
  return sheets;
}

// 시트 이름 → 그룹(중/한/영) 또는 null(제외)
function groupOf(name) {
  if (/①|중국어교육/.test(name)) return scope.GROUP.ZH;
  if (/②|한국어교육/.test(name)) return scope.GROUP.KO;
  if (/③|영어교육/.test(name)) return scope.GROUP.EN;
  return null; // 0.연도별분포 · 검토필요 등
}

// "이름(소속)" → "이름"
function authorName(cell) {
  if (!cell) return '';
  return String(cell).replace(/\s*[(（].*$/, '').trim();
}
function splitKeywords(cell) {
  if (!cell) return [];
  return String(cell).split(/[,;/·|]/).map((s) => s.trim()).filter(Boolean);
}
function toYear(cell) {
  const m = String(cell || '').match(/\d{4}/);
  return m ? parseInt(m[0], 10) : null;
}
const ARTID_RE = /ART\d{6,}/;

function rowToPaper(cells, group, url) {
  const arti_id = url ? (url.match(ARTID_RE) || [''])[0] : '';
  const authors = [authorName(cells[2]), authorName(cells[3])].filter(Boolean);
  const cited = String(cells[13] || '').match(/\d+/);
  const p = {
    arti_id,
    title_ko: (cells[0] || '').trim(),
    title_en: (cells[1] || '').trim() || null,
    authors,
    journal: (cells[4] || '').trim() || (cells[7] || '').trim() || null,
    year: toYear(cells[8]),
    keywords_ko: splitKeywords(cells[9]),
    keywords_en: splitKeywords(cells[10]),
    kci_field: (cells[11] || '').trim() || null,
    permalink: url || (arti_id ? 'https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=' + arti_id : ''),
    group,
    source: 'kci',
  };
  if (cited) p.cited_by_count = parseInt(cited[0], 10);
  return p;
}

function main() {
  const REPO = path.join(__dirname, '..');
  let input = process.argv[2];
  if (!input) {
    const dataDir = path.join(REPO, 'data');
    const xlsx = fs.readdirSync(dataDir).filter((f) => f.toLowerCase().endsWith('.xlsx') && !f.startsWith('~'));
    if (!xlsx.length) { console.error('data/ 안에 .xlsx 가 없습니다. 경로를 인자로 주세요.'); process.exit(1); }
    input = path.join(dataDir, xlsx[0]);
  }
  const output = process.argv[3] || path.join(REPO, 'data', 'details.json');

  const zip = readZip(fs.readFileSync(input));
  const shared = parseSharedStrings(zip.get('xl/sharedStrings.xml') ? zip.get('xl/sharedStrings.xml').toString('utf8') : '');
  const sheets = listSheets(zip);

  const papers = [];
  const perGroup = {};
  let withId = 0;
  for (const sh of sheets) {
    const group = groupOf(sh.name);
    if (!group) continue;
    const xml = zip.get(sh.file).toString('utf8');
    const relsName = sh.file.replace(/worksheets\/(sheet\d+)\.xml$/, 'worksheets/_rels/$1.xml.rels');
    const relsXml = zip.get(relsName) ? zip.get(relsName).toString('utf8') : '';
    const links = parseHyperlinks(xml, relsXml);
    const rows = parseSheet(xml, shared);
    // 헤더 행 탐지: 첫 셀이 '논문명(국문)'
    const headerRow = rows.find((r) => (r.cells[0] || '').replace(/\s/g, '') === '논문명(국문)');
    const headerNum = headerRow ? headerRow.row : 0;
    let taken = 0;
    for (const r of rows) {
      if (r.row <= headerNum) continue;
      const title = (r.cells[0] || '').trim();
      if (!title) continue; // 빈 행 스킵
      const url = links[r.row] || '';
      const p = rowToPaper(r.cells, group, url);
      if (p.arti_id) withId++;
      papers.push(p);
      taken++;
    }
    perGroup[sh.name] = taken;
  }

  // arti_id 중복 제거(그룹 교차 중복 방지) — 먼저 나온 것 유지
  const seen = new Set();
  const deduped = [];
  let dupes = 0;
  for (const p of papers) {
    const key = p.arti_id || ('no-id::' + p.title_ko);
    if (seen.has(key)) { dupes++; continue; }
    seen.add(key);
    deduped.push(p);
  }

  fs.writeFileSync(output, JSON.stringify(deduped, null, 2) + '\n', 'utf8');

  console.log('입력 :', path.relative(REPO, input));
  console.log('출력 :', path.relative(REPO, output));
  for (const [k, v] of Object.entries(perGroup)) console.log('  ' + k + ': ' + v + '편');
  console.log('합계 :', deduped.length + '편 (중복 제거 ' + dupes + '건)');
  console.log('arti_id 확보:', withId + '/' + papers.length + '편');
}

if (require.main === module) main();
module.exports = {
  readZip, parseSheet, parseHyperlinks, parseSharedStrings, listSheets,
  rowToPaper, groupOf, decode, ARTID_RE,
};
