# -*- coding: utf-8 -*-
"""make_public.py — 판정 결과(초록 포함 작업본)에서 공개본을 만든다. 초록이 든 원자료가 필요하다.

  data/rejudge/merged_<DATE>.json(작업본) → release/data/rejudge/merged_<DATE>.json(공개본). 작업본은 그대로 둔다.
    - 초록(abstract_ko, abstract_en) 필드를 뺀다.
    - DOI 칸에 KCI 응답 XML이 섞인 경우(수집 초기 정규식 오류) 비운다. 논문 쪽 DOI가 빈 태그였던 논문들이다.
    - 영문 주제어 칸에 영문 초록이 들어간 경우(KCI 원자료 입력 오류) 비운다.
  release/data/KCI_코퍼스확정.xlsx: 공개용 엑셀(시트 1–6). merge_rejudge.build_xlsx(public=True)로 만든다.
공개 패키지에는 release/ 아래 두 파일과 analysis/의 두 집계(school_level, ref_aggregate)를 옮긴다.
사용: python scripts/rejudge/make_public.py [--date 1161_20261001]
      (원자료 파이프라인의 마지막 단계: merge_rejudge → apply_l1 → apply_r3 → apply_r4 → school_level → ref_aggregate → make_public)
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import merge_rejudge as M   # stdout을 UTF-8로 감싼다

DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
M.DATE = DATE
for code in ('교양교육', 'AI디지털교과서'):
    if code not in M.REASONS: M.REASONS.insert(M.REASONS.index('국어교과담론'), code)
if '복수언어' not in M.REASONS: M.REASONS.insert(M.REASONS.index('기타'), '복수언어')

path = f'{REPO}/data/rejudge/merged_{DATE}.json'
recs = json.load(open(path, encoding='utf-8'))
if not any('abstract_ko' in r for r in recs):
    sys.exit('이미 공개본이다(초록 필드 없음). 작업본에서 실행한다.')
n_doi = n_kw = 0
for r in recs:
    ab_en = (r.get('abstract_en') or '').strip()
    if '<' in (r.get('doi') or ''):
        r['doi'] = ''; n_doi += 1
    kw = (r.get('kw_en') or '').strip()
    norm = lambda t: re.sub(r'[\s;,]+', ' ', t).strip().lower()
    if kw and ab_en and len(kw) > 300 and norm(kw)[:200] in norm(ab_en):
        r['kw_en'] = ''; n_kw += 1
    r.pop('abstract_ko', None); r.pop('abstract_en', None)
out = f'{REPO}/release/data/rejudge/merged_{DATE}.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(recs, ensure_ascii=False))
print(f'공개본 JSON {len(recs)}편: DOI 정리 {n_doi}건, 영문 주제어 정리 {n_kw}건 → {out}')
M.build_xlsx([r for r in recs if r['include']], False, public=True)
