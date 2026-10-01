# -*- coding: utf-8 -*-
"""scale_checks.py — 공백 유형 판정과 규모 통제 점검(원고 3.4, 4.2 각주, 4.3과 <표 6>, 5.1).

rarefaction_final.py가 격자 점유와 연구방법 구성을 다룬다면, 이 스크립트는 다음을 산출한다.
  (1) 공백 좌표(중국어 ≤1편)의 유형: 확산대기(비교군 ≥임계값) / 저축적(1~임계값-1) / 구조공백(세 군 0) / 중국어 단독(비교군 0, 중국어 1)
      임계값 5·10·15·20편 민감도
  (2) 확산대기 좌표별 규모 기대값: 중국어 격자 편수(48편)를 비교군 격자 분포에서 비복원 추출할 때의
      기대 편수와 P(X ≤ 실측) (초기하). 다중 비교(좌표 수) Bonferroni 기준 병기
  (3) 언어기능 구성: 중국어 격자 편수를 비교군(합·영어·한국어 각각)에서 추출할 때 기능별 편수가
      실측만큼 적거나 많을 확률. 11개 기능 Bonferroni 기준 병기
산출: analysis/scale_checks_<DATE>.md, .json
사용: python scripts/analysis/scale_checks.py [--date 1161_20261001]
"""
import json, os, sys, io
from math import comb
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
FUNCS = ['쓰기', '말하기', '평가·채점', '읽기', '리터러시·역량', '번역', '문법', '문학·문화', '발음', '어휘', '듣기']
METHS = ['개발연구', '조사연구', '질적·사례', '실험연구', '문헌·리뷰', '성능평가', '코퍼스분석', '기타·혼합']
TH = 10  # 채택 임계값(비교군 축적 편수)

inc = [r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8')) if r['include'] == 'Y']
grid = [r for r in inc if r['func'] != '기능비특정']
cnt = {g: Counter((r['func'], r['meth']) for r in grid if r['group'] == g) for g in ('영어', '한국어', '중국어')}
n_zh = sum(cnt['중국어'].values()); n_lead = sum(cnt['영어'].values()) + sum(cnt['한국어'].values())
cells = [(f, m, cnt['영어'][(f, m)] + cnt['한국어'][(f, m)], cnt['중국어'][(f, m)]) for f in FUNCS for m in METHS]
gap = [c for c in cells if c[3] <= 1]


def kind(c, th):
    f, m, lead, zh = c
    if lead == 0:
        return '구조공백' if zh == 0 else '중국어 단독'
    return '확산대기' if lead >= th else '저축적'


def p_le(K, N, n, k):
    return sum(comb(K, i) * comb(N - K, n - i) for i in range(0, k + 1)) / comb(N, n)


def p_ge(K, N, n, k):
    return 1.0 if k <= 0 else 1 - p_le(K, N, n, k - 1)


def fp(x):
    return '<0.0001' if x < 0.0001 else f'{x:.4f}'


L = [f'# 공백 유형과 규모 통제 점검 — 확정 코퍼스 ({DATE})\n',
     f'격자(기능 특정) 편수: 중국어 {n_zh}편, 비교군(영어+한국어) {n_lead}편. 공백 = 중국어 1편 이하인 좌표.\n',
     '## 1. 공백 유형과 임계값 민감도\n',
     f'공백 {len(gap)}칸. 비교군 축적 임계값에 따른 유형 분포:\n',
     '| 임계값 | 확산대기 | 저축적 | 구조공백 | 중국어 단독 | 계 |', '|---|---|---|---|---|---|']
out = {'n_zh_grid': n_zh, 'n_lead_grid': n_lead, 'gap': len(gap), 'threshold': {}}
for th in (5, 10, 15, 20):
    k = Counter(kind(c, th) for c in gap)
    out['threshold'][th] = dict(k)
    L.append(f'| {th}편{" (채택)" if th == TH else ""} | {k["확산대기"]} | {k["저축적"]} | {k["구조공백"]} | {k["중국어 단독"]} | {len(gap)} |')
struct = [c for c in gap if kind(c, TH) == '구조공백']
solo = [c for c in gap if kind(c, TH) == '중국어 단독']
L += ['', f'구조공백 {len(struct)}칸: ' + ', '.join(f'{f}×{m}' for f, m, _, _ in struct),
      f'- 이 가운데 잔여 범주 ‘기타·혼합’ 열 {sum(1 for c in struct if c[1] == "기타·혼합")}칸 → 해석 대상 {sum(1 for c in struct if c[1] != "기타·혼합")}칸',
      f'- 기능 분포: ' + ', '.join(f'{k} {v}' for k, v in Counter(c[0] for c in struct).most_common()),
      f'중국어 단독 {len(solo)}칸: ' + ', '.join(f'{f}×{m}' for f, m, _, _ in solo), '']

L += [f'## 2. 확산대기 좌표(비교군 {TH}편 이상)의 규모 기대값\n',
      f'중국어 격자 {n_zh}편을 비교군 격자 {n_lead}편의 분포에서 비복원 추출할 때(초기하) 해당 좌표의 기대 편수와 P(X ≤ 실측). '
      f'좌표 {sum(1 for c in gap if kind(c, TH) == "확산대기")}개를 함께 보므로 Bonferroni 기준을 병기한다.\n',
      '| 좌표 | 비교군 | 중국어 | 규모 기대값 | P(X ≤ 실측) | 판정 |', '|---|---|---|---|---|---|']
wait = sorted([c for c in gap if kind(c, TH) == '확산대기'], key=lambda c: -c[2])
bonf_c = 0.05 / len(wait)
out['diffusion_pending'] = []
for f, m, lead, zh in wait:
    p = p_le(lead, n_lead, n_zh, zh); e = n_zh * lead / n_lead
    verdict = '규모 통제 후에도 적음(보정 후 유의)' if p < bonf_c else ('규모 통제 후에도 적음(보정 전)' if p < 0.05 else '규모로 설명 가능')
    out['diffusion_pending'].append(dict(func=f, meth=m, lead=lead, zh=zh, expected=round(e, 2), p_le=p, verdict=verdict))
    L.append(f'| {f}×{m} | {lead} | {zh} | {e:.2f} | {fp(p)} | {verdict} |')
L += ['', f'Bonferroni 기준 {bonf_c:.4f}.', '']

L += ['## 3. 언어기능 구성의 규모 통제 비교\n',
      f'중국어 격자 {n_zh}편과 같은 수를 비교군에서 비복원 추출할 때 기능별 편수가 중국어 실측만큼 적거나(≤) 많을(≥) 확률. '
      f'11개 기능을 함께 보므로 Bonferroni 기준 {0.05 / 11:.4f}을 병기한다.\n',
      '| 기능 | 중국어 | 비교군 합 기대 | P(합) | 영어 기대 | P(영어) | 한국어 기대 | P(한국어) |', '|---|---|---|---|---|---|---|---|']
zf = Counter(r['func'] for r in grid if r['group'] == '중국어')
pools = {'합': Counter(r['func'] for r in grid if r['group'] != '중국어'),
         '영어': Counter(r['func'] for r in grid if r['group'] == '영어'),
         '한국어': Counter(r['func'] for r in grid if r['group'] == '한국어')}
out['function'] = {}
for f in FUNCS:
    row = [f, str(zf[f])]
    out['function'][f] = {'zh': zf[f]}
    for name, pc in pools.items():
        N = sum(pc.values()); K = pc[f]; e = n_zh * K / N
        p = p_le(K, N, n_zh, zf[f]) if zf[f] < e else p_ge(K, N, n_zh, zf[f])
        mark = ' **' if p < 0.05 / 11 else (' *' if p < 0.05 else '')
        row += [f'{e:.1f}', f'{fp(p)}{"↓" if zf[f] < e else "↑"}{mark}']
        out['function'][f][name] = dict(expected=round(e, 2), p=p, direction='적음' if zf[f] < e else '많음')
    L.append('| ' + ' | '.join(row) + ' |')
L += ['', '↓ 중국어가 기대보다 적음, ↑ 많음. * P<0.05, ** Bonferroni 기준 통과.', '']

# 3b. 연구방법 구성: 연구방법은 모든 논문에 있으므로 중국어군 전체(기능 비특정 포함)를 비교군 전체에서 같은 수로 뽑는다
zm_all = [r for r in inc if r['group'] == '중국어']; n_zm = len(zm_all)
zm = Counter(r['meth'] for r in zm_all)
mpools = {'합': Counter(r['meth'] for r in inc if r['group'] != '중국어'),
          '영어': Counter(r['meth'] for r in inc if r['group'] == '영어'),
          '한국어': Counter(r['meth'] for r in inc if r['group'] == '한국어')}
L += ['## 3b. 연구방법 구성의 규모 통제 비교\n',
      f'중국어군 전체 {n_zm}편과 같은 수를 비교군에서 비복원 추출할 때 방법별 편수가 중국어 실측만큼 적거나(≤) 많을(≥) 확률. '
      f'8개 방법을 함께 보므로 Bonferroni 기준 {0.05 / len(METHS):.4f}을 병기한다. 구축·평가형(개발+성능평가)은 묶음 지표로 따로 둔다.\n',
      '| 방법 | 중국어 | 비교군 합 기대 | P(합) | 영어 기대 | P(영어) | 한국어 기대 | P(한국어) |', '|---|---|---|---|---|---|---|---|']
out['method'] = {}
for m in METHS + ['구축·평가형']:
    keys = ('개발연구', '성능평가') if m == '구축·평가형' else (m,)
    k = sum(zm[x] for x in keys)
    row = [m, str(k)]
    out['method'][m] = {'zh': k}
    for name, pc in mpools.items():
        N = sum(pc.values()); K = sum(pc[x] for x in keys); e = n_zm * K / N
        p = p_le(K, N, n_zm, k) if k < e else p_ge(K, N, n_zm, k)
        mark = ' **' if p < 0.05 / len(METHS) else (' *' if p < 0.05 else '')
        row += [f'{e:.1f}', f'{fp(p)}{"↓" if k < e else "↑"}{mark}']
        out['method'][m][name] = dict(expected=round(e, 2), p=p, direction='적음' if k < e else '많음')
    L.append('| ' + ' | '.join(row) + ' |')
L += ['', '↓ 중국어가 기대보다 적음, ↑ 많음. * P<0.05, ** Bonferroni 기준 통과. 중국어군 문헌·리뷰의 대부분은 담론·시론이다(부록 A 표 A2의 담론·시론 규칙).', '',
      '## 4. 요약\n',
      '- 규모를 통제해도 남는 차이: 연구방법 구성(위 3b, rarefaction 2절)과 언어기능 구성(위 3절: 쓰기 적음, 번역·문학·문화 많음).',
      '- 좌표 단위 공백은 쓰기 좌표 세 칸만 기대보다 적고(P<0.05), Bonferroni 기준을 통과한 좌표는 없다(위 2절).']
io.open(f'{REPO}/analysis/scale_checks_{DATE}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
io.open(f'{REPO}/analysis/scale_checks_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
