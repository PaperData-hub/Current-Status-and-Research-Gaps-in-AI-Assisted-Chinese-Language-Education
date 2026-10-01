'use strict';

/**
 * scope.js — 도메인 스코프 필터 (accept.best 1.3 연구공백 분류의 도메인 필터 프로토타입)
 *
 * docs/ARCHITECTURE.md '스코프 규칙' 을 코드로 고정한다.
 *   포함: 세 언어교육(중국어교육 / 한국어교육=KFL / 영어·외국어교육)에
 *         AI 를 *교육적으로* 접목한 KCI 논문.
 *   제외(→ null):
 *     ① L1 국어교육 (모어 화자 대상)
 *     ② 번역 품질·오류만 다룬 번역학 (교육 없음)
 *     ③ 언어와 무관한 일반 교육 AI (수학·사회과·일반 대학수업 ChatGPT)
 *     ④ 순수 언어학 / NLP (교육 없음)
 *
 * 판정은 keywords_ko/en · kci_field · title 기반 규칙으로만 한다.
 * 모든 기준을 아래 상수 테이블(RULES)에 두어 재현·수정 가능하게 유지한다.
 *
 * export: tag(paper) → "중국어" | "한국어" | "영어·외국어" | null
 */

// ── 그룹 라벨 (반환값 / 스코프 태그) ────────────────────────────────────────
const GROUP = {
  ZH: '중국어',
  KO: '한국어',
  EN: '영어·외국어',
};

// ── 언어군 판정 규칙 (우선순위 = 배열 순서) ─────────────────────────────────
// title/keywords/kci_field 를 합친 텍스트에 하나라도 걸리면 해당 언어군.
const LANG_RULES = [
  {
    group: GROUP.ZH,
    patterns: [
      /중국어/, /중어중문/, /중어/, /汉语/, /漢語/, /华语/,
      /\bCFL\b/i, /\bTCFL\b/i, /\bHSK\b/i, /\bchinese\b/i, /\bmandarin\b/i,
    ],
    field: [/중국어와문학/, /중어중문/],
  },
  {
    group: GROUP.KO,
    // 한국어교육(KFL/L2). L1 '국어교육' 은 아래 EXCLUDE.L1 에서 별도 배제.
    patterns: [
      /한국어\s*교육/, /\bKFL\b/i, /외국어로서(의)?\s*한국어/, /제2언어로서.*한국어/,
      /한국어\s*학습/, /한국어\s*교재/, /한국어\s*능력/, /재외동포.*한국어/,
      /korean\s+as\s+a\s+(foreign|second)\s+language/i, /한국어/,
    ],
    field: [/한국어와문학/],
  },
  {
    group: GROUP.EN,
    patterns: [
      /영어\s*교육/, /\bEFL\b/i, /\bESL\b/i, /\bTESOL\b/i, /\bELT\b/i,
      /\benglish\b/i, /영어/, /외국어\s*교육/, /제2외국어/, /제이(2)?외국어/,
      /일본어/, /\b일어\b/, /프랑스어/, /불어/, /독일어/, /\b독어\b/,
      /스페인어/, /서반아어/, /러시아어/, /노어/, /베트남어/, /아랍어/,
      /foreign\s+language/i,
    ],
    field: [/영어와문학/],
  },
];

// ── 교육(pedagogy) 신호 ─────────────────────────────────────────────────────
// 언어교육으로 인정하려면 교육/학습/교수 맥락이 있어야 한다(순수 언어학·NLP 배제).
const EDU_MARKERS = [
  /교육/, /교수/, /학습/, /수업/, /교실/, /학습자/, /교재/, /교과/,
  /리터러시/, /literacy/i, /teaching/i, /learning/i, /education/i,
  /pedagog/i, /instruction/i, /classroom/i, /curriculum/i,
  /외국어로서/, /제2언어/, /\bL2\b/, /\bCALL\b/i, /\bMALL\b/i,
];

// ── AI(참고: 코퍼스 주제) 신호 — ③ 판정 보조용 ─────────────────────────────
const AI_MARKERS = [
  /\bAI\b/i, /인공지능/, /chatgpt/i, /\bgpt\b/i, /생성형/, /머신러닝/, /기계학습/,
  /딥러닝/, /deep\s*learning/i, /machine\s*learning/i, /챗봇/, /chatbot/i,
  /\bLLM\b/i, /자동\s*채점/, /음성\s*인식/, /speech\s*recognition/i, /뉴럴/,
  /\bBERT\b/i, /트랜스포머/, /transformer/i,
];

// ── 제외 규칙 (→ null) ─────────────────────────────────────────────────────
const EXCLUDE = {
  // ① L1 국어교육 (모어 화자). '한/외/중/제2 국어' 등 언어명 접두는 lookbehind 로 제외해
  //    '한국어교육/외국어교육/중국어교육' 의 부분일치 오탐을 막는다.
  L1: {
    patterns: [
      /(?<![한외중])국어\s*교육/, /국어과/, /국어\s*교과/, /초등\s*국어/, /중등\s*국어/,
      /모어\s*화자/, /모국어\s*화자/, /국어\s*수업/,
    ],
    field: [/^국어교육$/],
  },
  // ② 번역 품질·오류만 다룬 번역학 (교육 없음). '번역 교육' 은 포함(번역=기능 축).
  TRANSLATION_ONLY: {
    patterns: [
      /번역\s*품질/, /오역/, /번역\s*오류/, /번역학/, /번역\s*평가/, /번역\s*전략/,
      /번역\s*투/, /기계번역\s*(품질|성능|오류|평가|비교)/, /post[- ]?editing/i,
      /translation\s+quality/i,
    ],
    field: [/^통역번역학$/],
  },
  // ④ 순수 언어학 / NLP (교육 없음).
  LINGUISTICS_NLP: {
    patterns: [
      /언어학/, /음운론/, /통사론/, /형태론/, /의미론/, /화용론/, /코퍼스\s*언어학/,
      /자연어\s*처리/, /\bNLP\b/i, /형태소\s*분석/, /구문\s*분석/, /개체명/,
      /감성\s*분석/, /감정\s*분석/, /토픽\s*모델링/, /어휘\s*의미망/, /corpus\s+linguistics/i,
    ],
    field: [/^언어학$/],
  },
};

// KFL(한국어교육) 확정 신호 — L1 오탐 방지 가드.
const KFL_GUARD = [
  /한국어\s*교육/, /\bKFL\b/i, /외국어로서(의)?\s*한국어/, /한국어\s*학습/,
  /korean\s+as\s+a\s+(foreign|second)\s+language/i,
];

// ── 유틸 ────────────────────────────────────────────────────────────────────
function anyMatch(patterns, text) {
  return patterns.some((re) => re.test(text));
}

/** paper → 판정에 쓰는 소문자 정규화 텍스트(제목·키워드) 와 원본 kci_field. */
function buildText(paper) {
  const parts = [
    paper.title_ko,
    paper.title_en,
    ...(Array.isArray(paper.keywords_ko) ? paper.keywords_ko : []),
    ...(Array.isArray(paper.keywords_en) ? paper.keywords_en : []),
  ].filter(Boolean);
  return parts.join(' ');
}

function detectLang(text, field) {
  for (const rule of LANG_RULES) {
    if (anyMatch(rule.patterns, text)) return rule.group;
    if (field && rule.field && anyMatch(rule.field, field)) return rule.group;
  }
  return null;
}

/**
 * tag(paper) — 스코프 판정.
 * @param {object} paper  models.Paper (title_ko/en, keywords_ko/en, kci_field …)
 * @returns {"중국어"|"한국어"|"영어·외국어"|null}
 */
function tag(paper) {
  if (!paper || typeof paper !== 'object') return null;
  const text = buildText(paper);
  const field = paper.kci_field || '';
  const combined = `${text} ${field}`;

  const hasEdu = anyMatch(EDU_MARKERS, combined);
  const hasKfl = anyMatch(KFL_GUARD, combined);

  // ① L1 국어교육 (KFL 신호가 없을 때만) → 배제
  if (!hasKfl && (anyMatch(EXCLUDE.L1.patterns, text) || anyMatch(EXCLUDE.L1.field, field))) {
    return null;
  }
  // ② 번역 품질·오류만(교육 없음) → 배제
  if (!hasEdu && (anyMatch(EXCLUDE.TRANSLATION_ONLY.patterns, text)
      || anyMatch(EXCLUDE.TRANSLATION_ONLY.field, field))) {
    return null;
  }
  // ④ 순수 언어학·NLP(교육 없음) → 배제
  if (!hasEdu && (anyMatch(EXCLUDE.LINGUISTICS_NLP.patterns, text)
      || anyMatch(EXCLUDE.LINGUISTICS_NLP.field, field))) {
    return null;
  }

  const group = detectLang(text, field);

  // ③ 언어와 무관한 일반 교육 AI, 그리고 언어군 미검출 → 범위 밖
  if (!group) return null;

  // 언어군은 잡혔으나 교육 맥락이 없으면(순수 언어 자료·언어학) 범위 밖
  if (!hasEdu) return null;

  return group;
}

module.exports = { tag, GROUP, LANG_RULES, EDU_MARKERS, AI_MARKERS, EXCLUDE };
