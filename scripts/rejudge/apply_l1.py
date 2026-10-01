# -*- coding: utf-8 -*-
"""apply_l1.py — 저자 결정(2026-09-30 '교양은 제외')을 L1 한국어군 145편 재판정 결과로 반영.

data/rejudge/merged_20260930.json + data/rejudge/l1/out/L*.json
  → data/rejudge/merged_<DATE>.json (교양 제외 반영)
  → merge_rejudge.summarize / build_xlsx 재사용으로 요약·엑셀 재생성
"""
import json, os, sys, glob, io
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import merge_rejudge as M   # merge_rejudge가 stdout을 UTF-8로 감싼다

DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '20260930b'
if '교양교육' not in M.REASONS:
    M.REASONS.insert(M.REASONS.index('국어교과담론'), '교양교육')
M.DATE = DATE

merged = json.load(open(f'{REPO}/data/rejudge/merged_20260930.json', encoding='utf-8'))
by = {r['arti_id']: r for r in merged}
verd = {}
for f in sorted(glob.glob(f'{REPO}/data/rejudge/l1/out/L*.json')):
    for o in json.load(open(f, encoding='utf-8')):
        verd[o['id']] = o
print('L1 판정', len(verd), '건')
from collections import Counter
print('verdict:', Counter(v.get('verdict') for v in verd.values()))

n_ex = n_l2 = 0
for aid, v in verd.items():
    r = by.get(aid)
    if r is None or r['include'] != 'Y':
        print('  건너뜀(포함 아님):', aid); continue
    vd = (v.get('verdict') or '').strip()
    if vd == '교양':
        r.update(include='N', reason='교양교육', group=r['group'], func='', meth='', tool='', focus='', learner='')
        r['note'] = (v.get('note') or '')[:60]
        r['boundary'] = 'Y' if str(v.get('boundary', '')).upper().startswith('Y') else r['boundary']
        n_ex += 1
    elif vd == 'L2재분류':
        r['learner'] = 'L2'; r['boundary'] = 'Y'
        r['note'] = (r.get('note') or '') + ' | L1→L2 정정'
        n_l2 += 1
    else:
        if str(v.get('boundary', '')).upper().startswith('Y'): r['boundary'] = 'Y'
print(f'교양 제외 {n_ex}편, L2 재분류 {n_l2}편')
json.dump(merged, open(f'{REPO}/data/rejudge/merged_{DATE}.json', 'w', encoding='utf-8'), ensure_ascii=False)
inc = [r for r in merged if r['include'] == 'Y']
print('최종 포함', len(inc), Counter(r['group'] for r in inc))
print('한국어군 learner', Counter(r['learner'] for r in inc if r['group'] == '한국어'))
M.summarize(merged, [], [])
M.build_xlsx([r for r in merged if r['include']], False)
M.build_xlsx([r for r in merged if r['include']], True)
