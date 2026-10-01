'use strict';
/*
 * cache_service.js — KCI 응답 파일 캐시 (accept.best 30일 캐싱 정책)
 *
 * 순수 fs 계층. 네트워크·전역 가변상태 없음. 응답 "텍스트"를 그대로 저장한다.
 *   - makeKey(apiCode, params) : apiCode + 정렬된 params 를 sha256 해시한 캐시 키.
 *   - get(key, opts)           : { hit, value }  (TTL(mtime 기준) 만료·부재 시 hit=false)
 *   - set(key, value, opts)    : 캐시에 텍스트 저장(디렉터리 자동 생성), 저장 경로 반환.
 *
 * 캐시 디렉터리 결정 우선순위: opts.dir → env KCI_CACHE_DIR → data/cache (레포 루트).
 * (테스트는 opts.dir 또는 KCI_CACHE_DIR 로 임시폴더를 주입해 레포를 더럽히지 않는다.)
 *
 * TTL 기본 30일. mtime 기준으로 age = now - mtime, age > ttl 이면 미스(만료).
 * 실패 응답(비-2xx)은 호출부에서 set 을 부르지 않음으로써 캐시에서 배제한다.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30일
const DEFAULT_DIR = path.join(__dirname, '..', '..', 'data', 'cache');

/** 캐시 디렉터리 결정(순수: 인자·환경변수만 본다). */
function resolveDir(opts) {
  if (opts && opts.dir) return opts.dir;
  if (process.env.KCI_CACHE_DIR) return process.env.KCI_CACHE_DIR;
  return DEFAULT_DIR;
}

/**
 * 캐시 키 생성 — apiCode + 정렬된 params 의 sha256(hex).
 * params 키를 정렬해 직렬화하므로 동일 요청은 항상 동일 키(결정론적).
 * 인증키 등 비밀·가변 파라미터는 호출부에서 params 에 넣지 않는다.
 */
function makeKey(apiCode, params) {
  const p = params && typeof params === 'object' ? params : {};
  const sorted = {};
  for (const k of Object.keys(p).sort()) sorted[k] = p[k];
  const payload = JSON.stringify([String(apiCode == null ? '' : apiCode), sorted]);
  return crypto.createHash('sha256').update(payload).digest('hex');
}

/** 키에 대응하는 캐시 파일 경로. */
function pathFor(key, opts) {
  return path.join(resolveDir(opts), String(key) + '.txt');
}

/**
 * @param {string} key
 * @param {{dir?:string, ttlMs?:number}} [opts]
 * @returns {{hit:boolean, value:(string|null), expired?:boolean}}
 */
function get(key, opts = {}) {
  const ttl = typeof opts.ttlMs === 'number' ? opts.ttlMs : DEFAULT_TTL_MS;
  const file = pathFor(key, opts);
  let st;
  try {
    st = fs.statSync(file);
  } catch (e) {
    return { hit: false, value: null }; // 파일 없음 → 미스
  }
  const age = Date.now() - st.mtimeMs;
  if (age > ttl) {
    return { hit: false, value: null, expired: true }; // 만료 → 미스 (ttl=0/음수면 즉시 만료)
  }
  try {
    return { hit: true, value: fs.readFileSync(file, 'utf8') };
  } catch (e) {
    return { hit: false, value: null };
  }
}

/**
 * @param {string} key
 * @param {string} value  응답 텍스트
 * @param {{dir?:string}} [opts]
 * @returns {string} 저장된 파일 경로
 */
function set(key, value, opts = {}) {
  const dir = resolveDir(opts);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, String(key) + '.txt');
  fs.writeFileSync(file, value == null ? '' : String(value), 'utf8');
  return file;
}

module.exports = { makeKey, get, set, pathFor, resolveDir, DEFAULT_TTL_MS, DEFAULT_DIR };

// ── 데모 ──────────────────────────────────────────────────────────────────────
if (require.main === module) {
  const os = require('node:os');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'kci-cache-demo-'));
  const key = makeKey('articleSearch', { title: '인공지능', page: '1', displayCount: '100' });
  console.log('key =', key);
  console.log('miss (before set):', get(key, { dir: tmp }));
  set(key, '<xml>ART000000001</xml>', { dir: tmp });
  console.log('hit  (after set) :', get(key, { dir: tmp }));
  // 만료 시연: mtime 을 31일 전으로 되돌린다.
  const past = Date.now() / 1000 - 31 * 24 * 3600;
  fs.utimesSync(pathFor(key, { dir: tmp }), past, past);
  console.log('miss (expired)  :', get(key, { dir: tmp }));
}
