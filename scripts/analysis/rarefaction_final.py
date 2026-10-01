# -*- coding: utf-8 -*-
"""rarefaction_final.py — 격자 점유율의 희박화와 연구방법 구성의 초기하 확률(원고 3.4, 4.3의 <표 5>, 5.1).

  (1) 영어·한국어군의 격자 논문에서 중국어군 격자 편수(48편)만큼 비복원 무작위 추출(1만 회, 시드 20260930)
      → 기대 점유 칸수 분포와 중국어 실측 29칸의 백분위(<표 5>)
  (1b) 기능 비특정 제외율을 바꾼 민감도(49편, 54편, 68편)
  (2) 중국어군 전체 편수를 영어·한국어군에서 뽑을 때 실험연구가 실측 이하일 확률, 개발+성능평가가 실측 이상일 확률
  (3) 공백 좌표(중국어 ≤1편)와 비교군 축적 임계값 민감도(유형별 칸수는 scale_checks.py)
산출: analysis/rarefaction_<DATE>.md, .json
사용: python scripts/analysis/rarefaction_final.py [--date 1161_20261001]
"""
import json, os, sys, io, random, statistics as st
from math import comb
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
G = ['영어', '한국어', '중국어']
FUNCS = ['쓰기', '말하기', '평가·채점', '읽기', '리터러시·역량', '번역', '문법', '문학·문화', '발음', '어휘', '듣기']
METHS = ['개발연구', '조사연구', '질적·사례', '실험연구', '문헌·리뷰', '성능평가', '코퍼스분석', '기타·혼합']
REPS = 10000
random.seed(20260930)

inc = [r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8')) if r['include'] == 'Y']
cells = {g: [(r['func'], r['meth']) for r in inc if r['group'] == g and r['func'] != '기능비특정'] for g in G}
allm = {g: [r['meth'] for r in inc if r['group'] == g] for g in G}
zh = cells['중국어']; n_zh = len(zh); k_zh = len(set(zh))

def rarefy(pool, n):
    res = sorted(len(set(random.sample(pool, n))) for _ in range(REPS))
    pct = 100 * sum(1 for k in res if k <= k_zh) / REPS
    return dict(mean=st.mean(res), sd=st.pstdev(res), lo=res[int(0.025 * REPS)], mid=res[REPS // 2],
                hi=res[int(0.975 * REPS)], pct_le=pct)

def fp(x):
    return '<0.0001' if x < 0.0001 else f'{x:.4f}'

def hyper_le(K, N, n, k):   # P(X <= k)
    return sum(comb(K, i) * comb(N - K, n - i) for i in range(0, min(k, K) + 1)) / comb(N, n)
def hyper_ge(K, N, n, k):   # P(X >= k)
    return 1 - hyper_le(K, N, n, k - 1) if k > 0 else 1.0

L = [f'# 격자 점유 희박화·초기하 재분석 — 확정 코퍼스 ({DATE})\n',
     f'확정 코퍼스 {len(inc):,}편. 격자는 언어기능 11 × 연구방법 8 = 88칸, 기능 비특정은 제외한다.',
     f'중국어군 격자 편수 **{n_zh}편**, 점유 **{k_zh}칸**(칸당 {n_zh / k_zh:.2f}편).\n',
     '## 1. 희박화: 중국어군과 같은 편수를 뽑았을 때의 기대 점유 칸수\n',
     f'| 표본 | 모집단 격자 편수 | 기대 점유 칸(평균±SD) | 95% 구간 | 중국어 실측 {k_zh}칸의 백분위 |',
     '|---|---|---|---|---|']
R = {}
for g in ('영어', '한국어'):
    R[g] = rarefy(cells[g], n_zh)
    d = R[g]
    L.append(f'| {g}에서 {n_zh}편 | {len(cells[g])} | {d["mean"]:.1f} ± {d["sd"]:.1f} | {d["lo"]}–{d["hi"]} | {d["pct_le"]:.1f} |')
L += ['', f'해석: 영어·한국어군에서 {n_zh}편만 뽑아도 점유 칸은 평균 {R["영어"]["mean"]:.1f}칸·{R["한국어"]["mean"]:.1f}칸이다. '
      f'중국어군 실측 {k_zh}칸은 이 분포의 백분위 {R["영어"]["pct_le"]:.0f}·{R["한국어"]["pct_le"]:.0f}에 놓인다. '
      '따라서 중국어군의 낮은 점유율은 편수가 적은 데서 오는 규모 효과로 설명된다(원고 4.3, 5.1).']

# 1b. 기능 비특정 제외율 민감도. 1절 추출이 끝난 뒤에 난수를 쓰므로 1절 결과는 바뀌지 않는다.
n_all = {g: sum(1 for r in inc if r['group'] == g) for g in G}
excl = {g: 1 - len(cells[g]) / n_all[g] for g in G}
L += ['', '## 1b. 기능 비특정 제외율 민감도\n',
      '기능 비특정 제외율: ' + ', '.join(f'{g} {excl[g] * 100:.1f}%' for g in G) + '. '
      f'중국어군 {n_all["중국어"]}편에 다른 군의 제외율을 적용한 편수와 전체 편수로 다시 추출하고, 중국어 실측 {k_zh}칸의 위치를 본다. '
      '추출 편수가 늘어도 중국어 실측 칸수는 고정하므로 보수적 비교다.\n',
      '| 가정 | 추출 편수 | 영어 기대 점유(95% 구간) | 백분위 | 한국어 기대 점유(95% 구간) | 백분위 |', '|---|---|---|---|---|---|']
SENS = []
for lab, nn in ((f'영어 제외율({excl["영어"] * 100:.1f}%) 적용', round(n_all['중국어'] * (1 - excl['영어']))),
                (f'한국어 제외율({excl["한국어"] * 100:.1f}%) 적용', round(n_all['중국어'] * (1 - excl['한국어']))),
                ('제외 없음(중국어 전체)', n_all['중국어'])):
    a, b = rarefy(cells['영어'], nn), rarefy(cells['한국어'], nn)
    SENS.append((lab, nn, a, b))
    L.append(f'| {lab} | {nn} | {a["mean"]:.1f}({a["lo"]}–{a["hi"]}) | {a["pct_le"]:.1f} | {b["mean"]:.1f}({b["lo"]}–{b["hi"]}) | {b["pct_le"]:.1f} |')
L += ['', '## 2. 초기하 검정: 연구방법 구성의 차이\n',
      f'중국어군 전체 {len(allm["중국어"])}편을 영어·한국어군에서 같은 수로 뽑을 때의 확률이다.\n',
      '| 모집단 | N | 실험연구 K | 기대 실험 | P(실험 ≤ 중국어 실측) | 개발+성능 K | 기대 개발+성능 | P(개발+성능 ≥ 중국어 실측) |',
      '|---|---|---|---|---|---|---|---|']
n = len(allm['중국어'])
zx = sum(1 for m in allm['중국어'] if m == '실험연구')
zb = sum(1 for m in allm['중국어'] if m in ('개발연구', '성능평가'))
H = {}
for g in ('영어', '한국어'):
    N = len(allm[g]); Kx = sum(1 for m in allm[g] if m == '실험연구'); Kb = sum(1 for m in allm[g] if m in ('개발연구', '성능평가'))
    H[g] = (hyper_le(Kx, N, n, zx), hyper_ge(Kb, N, n, zb))
    L.append(f'| {g} | {N} | {Kx} | {n * Kx / N:.1f} | {fp(H[g][0])} | {Kb} | {n * Kb / N:.1f} | {fp(H[g][1])} |')
L += ['', f'중국어 실측: 실험연구 {zx}편, 개발+성능평가 {zb}편.',
      f'해석: 영어군 대비로는 실험연구가 적고(P {fp(H["영어"][0])}) 개발·성능평가가 많다(P {fp(H["영어"][1])}). '
      f'한국어군 대비로는 실험연구 P={fp(H["한국어"][0])}, 개발+성능 P={fp(H["한국어"][1])}로, 한국어군과는 구성이 비슷하다. '
      '규모를 통제해도 남는 차이는 영어군과의 연구방법 구성 차이이다(원고 4.2 각주, 5.1).',
      '', '## 3. 공백 좌표 유형과 임계값 민감도\n']
grid = {g: Counter(cells[g]) for g in G}
gap = [(f, m, grid['영어'][(f, m)] + grid['한국어'][(f, m)]) for f in FUNCS for m in METHS if grid['중국어'][(f, m)] <= 1]
struct = [(f, m) for f, m, s in gap if s == 0 and grid['중국어'][(f, m)] == 0]
L.append(f'공백 좌표(중국어 ≤1편) **{len(gap)}칸**, 세 군 모두 0편인 구조공백 **{len(struct)}칸**.\n')
L.append('구조공백 기능 분포: ' + ', '.join(f'{k} {v}' for k, v in Counter(f for f, m in struct).most_common()))
L.append('구조공백 방법 분포: ' + ', '.join(f'{k} {v}' for k, v in Counter(m for f, m in struct).most_common()) + '\n')
L += ['| 선도군(영+한) 축적 임계값 | 확산대기 칸 | 나머지 공백 칸 |', '|---|---|---|']
for th in (5, 10, 15, 20):
    w = sum(1 for x in gap if x[2] >= th)
    L.append(f'| {th}편 이상 | {w} | {len(gap) - w} |')
out = dict(n_zh_grid=n_zh, k_zh=k_zh, rarefy=R, hyper={g: dict(p_exp_le=H[g][0], p_build_ge=H[g][1]) for g in H},
           zh_exp=zx, zh_build=zb, gap=len(gap), struct=len(struct))
io.open(f'{REPO}/analysis/rarefaction_{DATE}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
io.open(f'{REPO}/analysis/rarefaction_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
