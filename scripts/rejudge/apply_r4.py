# -*- coding: utf-8 -*-
"""apply_r4.py — 저자 결정 4차(2026-10-01)를 반영.

  1) 언어 범주를 영어·한국어·중국어 셋으로만 정리한다(필드 lang3).
     1차 수집의 검색 범주(영어·외국어 / 한국어 / 중국어 / 통·번역 / 복수언어)는 쓰지 않는다.
       - 포함 논문: 분석 언어군(group)
       - 제외 논문: 판정된 대상 언어(group). 판정값이 없으면 검색 범주 영어·외국어→영어, 한국어→한국어, 중국어→중국어.
         통·번역 범주는 제목의 언어쌍으로 가른다(한·중 번역 → 중국어).
       - 세 언어에 속하지 않거나(제2외국어) 대상 언어가 없는(언어비특정·복수언어) 제외 논문은 '해당 없음'.
  2) 복수언어 비교 연구는 제외한다. 복수언어 검색 범주에서 확정 코퍼스에 들어 있던 7편을 초록으로 다시 보아
     한 언어만 다룬 2편은 유지하고, 여러 언어를 함께 다룬 3편(사유 '복수언어')과
     대상 언어를 명시하지 않은 2편(사유 '언어비특정')은 제외한다.

입력: data/rejudge/merged_1166_20260930.json (3차 결정 반영본)
출력: data/rejudge/merged_<DATE>.json, analysis/rejudge_summary_<DATE>.md,
      data/KCI_코퍼스확정_<DATE>.xlsx, data/KCI_코퍼스확정_<DATE>_초록포함.xlsx
사용: python scripts/rejudge/apply_r4.py --date 1161_20261001
"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import merge_rejudge as M   # merge_rejudge가 stdout을 UTF-8로 감싼다

DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
SRC = '1166_20260930'
for code in ('교양교육', 'AI디지털교과서'):
    if code not in M.REASONS:
        M.REASONS.insert(M.REASONS.index('국어교과담론'), code)
if '복수언어' not in M.REASONS:
    M.REASONS.insert(M.REASONS.index('기타'), '복수언어')
M.DATE = DATE

# 복수언어 검색 범주의 포함 7편 재검토(초록 기준)
EXCLUDE = {
    'ART003153816': ('복수언어', '영어·한국어 교육의 연구 동향을 함께 분석'),
    'ART003307424': ('복수언어', '국어(L1)·영어·한국어(KSL) 교사의 문법 지도 인식을 함께 분석'),
    'ART003018913': ('복수언어', '영어·다국어·한국어 학습 도구 4종의 문법 피드백을 비교'),
    'ART002795926': ('언어비특정', '언어 수업의 기계번역 담론, 대상 언어 미명시'),
    'ART003011516': ('언어비특정', '외국어 수업 모델 일반, 대상 언어 미명시'),
}
KEEP = {
    'ART003139683': '중급 중국어 수업의 ChatGPT 대화 과제(한 언어)',
    'ART003283129': '영어교육 특집호 서문(한 언어)',
}
SHEET_LANG = {'영어·외국어': '영어', '한국어': '한국어', '중국어': '중국어'}
TT_ZH = ('채식주의자', '欢迎', '艾靑')   # 통·번역 범주 제외 논문 중 제목에 한·중 언어쌍이 드러나는 것

merged = json.load(open(f'{REPO}/data/rejudge/merged_{SRC}.json', encoding='utf-8'))
by = {r['arti_id']: r for r in merged}

for aid, (reason, why) in EXCLUDE.items():
    r = by[aid]
    assert r['include'] == 'Y' and r['sheet'] == '복수언어', aid
    prev = f"{r['group']}/{r['func']}/{r['meth']}"
    r.update(include='N', reason=reason, group='', learner='', func='', meth='', tool='', focus='', ai_role='', paper_type='')
    r['note'] = f'R4 제외: {why} (원 배정 {prev})'[:90]
for aid, why in KEEP.items():
    r = by[aid]
    assert r['include'] == 'Y' and r['sheet'] == '복수언어', aid
    r['note'] = f"{r['note']} | R4 유지: {why}"[:120]
left = [r['arti_id'] for r in merged if r['sheet'] == '복수언어' and r['include'] == 'Y' and r['arti_id'] not in KEEP]
assert not left, left


def lang3(r):
    if r['include'] == 'Y':
        return r['group']
    if r['group'] in M.GROUPS:
        return r['group']
    if r['reason'] in ('제2외국어', '언어비특정', '복수언어'):
        return '해당 없음'
    if r['sheet'] in SHEET_LANG:
        return SHEET_LANG[r['sheet']]
    if r['sheet'] == '통번역' and any(k in (r['title_ko'] or '') for k in TT_ZH):
        return '중국어'
    return '해당 없음'


for r in merged:
    r['lang3'] = lang3(r)

json.dump(merged, open(f'{REPO}/data/rejudge/merged_{DATE}.json', 'w', encoding='utf-8'), ensure_ascii=False)
inc = [r for r in merged if r['include'] == 'Y']
exc = [r for r in merged if r['include'] == 'N']
print('최종 포함', len(inc), dict(Counter(r['group'] for r in inc)))
print('언어 범주(전체)', dict(Counter(r['lang3'] for r in merged)))
print('언어 범주(제외)', dict(Counter(r['lang3'] for r in exc)))
print('제외 사유', dict(Counter(r['reason'] for r in exc)))
print('통번역 범주 → 언어 범주', dict(Counter((r['include'], r['lang3']) for r in merged if r['sheet'] == '통번역')))
print('복수언어 범주 → 언어 범주', dict(Counter((r['include'], r['lang3']) for r in merged if r['sheet'] == '복수언어')))
assert all(r['lang3'] in M.GROUPS for r in inc)

M.summarize(merged, [], [])
rows = [r for r in merged if r['include']]
M.build_xlsx(rows, False)
M.build_xlsx(rows, True)
