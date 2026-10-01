# -*- coding: utf-8 -*-
"""apply_r3.py — 저자 결정 3차(2026-09-30)를 반영.

  A) AI 디지털교과서(AIDT) 자체를 대상으로 한 연구 제외 — [언어교육+AI] 융합이 아님
  B) AI 자동채점·자동평가·화법 평가 도구 연구는 대학 교양 맥락이어도 포함

입력: data/rejudge/merged_20260930b.json (교양 제외 반영본, 1,177편)
      data/rejudge/r3/out/AIDT.json, data/rejudge/r3/out/KYO.json
출력: data/rejudge/merged_<DATE>.json + 엑셀·요약 재생성

B로 되돌리는 행은 코딩 값(언어기능·연구방법·핵심도구·초점)을 교양 제외 전 판정본
(merged_20260930.json)에서 복원한다.
"""
import json, os, sys, glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import merge_rejudge as M   # merge_rejudge가 stdout을 UTF-8로 감싼다

DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1166_20260930'
for code in ('교양교육', 'AI디지털교과서'):
    if code not in M.REASONS:
        M.REASONS.insert(M.REASONS.index('국어교과담론'), code)
M.DATE = DATE

merged = json.load(open(f'{REPO}/data/rejudge/merged_20260930b.json', encoding='utf-8'))
pre = {r['arti_id']: r for r in json.load(open(f'{REPO}/data/rejudge/merged_20260930.json', encoding='utf-8'))}
by = {r['arti_id']: r for r in merged}

def load(name):
    p = f'{REPO}/data/rejudge/r3/out/{name}.json'
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []

# ── A) AIDT 제외 ────────────────────────────────────────────────────────────
n_aidt = n_keep = 0
for o in load('AIDT'):
    r = by.get(o['id'])
    if r is None or r['include'] != 'Y':
        print('  AIDT 건너뜀(포함 아님):', o['id']); continue
    vd = (o.get('verdict') or '').strip()
    if vd == '제외':
        r.update(include='N', reason='AI디지털교과서', func='', meth='', tool='', focus='', learner='')
        r['note'] = (o.get('note') or '')[:60]
        n_aidt += 1
    else:
        n_keep += 1
    if str(o.get('boundary', '')).upper().startswith('Y'): r['boundary'] = 'Y'
print(f'A) AIDT 제외 {n_aidt}편, 유지 {n_keep}편')

# ── B) 자동채점·평가 도구 포함 복원 ─────────────────────────────────────────
n_back = n_stay = 0
for o in load('KYO'):
    r = by.get(o['id'])
    if r is None:
        print('  KYO 없음:', o['id']); continue
    vd = (o.get('verdict') or '').strip()
    if vd == '포함':
        if r['reason'] != '교양교육':
            print('  KYO 건너뜀(교양 제외분 아님):', o['id'], r['reason']); continue
        p = pre[o['id']]
        r.update(include='Y', reason='', func=p['func'], meth=p['meth'], tool=p['tool'],
                 focus=p['focus'], learner=p['learner'] or 'L1')
        r['note'] = ((o.get('note') or '') + ' | 교양이나 평가도구로 포함')[:60]
        r['boundary'] = 'Y'
        n_back += 1
    else:
        n_stay += 1
        if str(o.get('boundary', '')).upper().startswith('Y'): r['boundary'] = 'Y'
print(f'B) 교양 제외분 중 포함 복원 {n_back}편, 제외 유지 {n_stay}편')

json.dump(merged, open(f'{REPO}/data/rejudge/merged_{DATE}.json', 'w', encoding='utf-8'), ensure_ascii=False)
inc = [r for r in merged if r['include'] == 'Y']
print('최종 포함', len(inc), dict(Counter(r['group'] for r in inc)))
print('한국어군 learner', dict(Counter(r['learner'] for r in inc if r['group'] == '한국어')))
print('제외 사유', dict(Counter(r['reason'] for r in merged if r['include'] == 'N')))

M.summarize(merged, [], [])
rows = [r for r in merged if r['include']]
M.build_xlsx(rows, False)
M.build_xlsx(rows, True)
