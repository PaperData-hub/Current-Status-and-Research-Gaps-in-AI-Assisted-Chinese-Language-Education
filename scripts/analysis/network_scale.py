# -*- coding: utf-8 -*-
"""network_scale.py — 공저 네트워크 지표의 규모 기대값(원고 4.4.2, <표 8>의 하단 두 행).

영어군·한국어군에서 중국어군과 같은 편수(68편)를 비복원 무작위로 2,000회 뽑아(시드 20260930), <표 8>과 같은 규칙
(tables_8to11.py의 이름-기관 결합 노드)으로 공저 네트워크를 만들고 지표의 분포(중앙값, 5–95% 구간)를 구한다.
중국어군 실측값의 백분위를 함께 보인다.
지표: 논문당 저자, 단독저자 논문 %, 고립 저자 %, 평균 연결정도, 최대 공저 군집(최대 연결 요소, 명), 연결 요소 수.
산출: analysis/network_scale_<DATE>.md, .json
사용: python scripts/analysis/network_scale.py [--date 1161_20261001]
"""
import json, os, re, sys, io, random
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
REPS = 2000
random.seed(20260930)
G = ['영어', '한국어', '중국어']
inc = [r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8')) if r.get('include') == 'Y']
INST = re.compile(r'([가-힣A-Za-z&\.\- ]*?(?:대학교|대학|학교|연구원|연구소|교육청|University|College|Institute|School))', re.I)


def akey(a):   # tables_8to11.py와 같은 규칙
    m = re.match(r'\s*([^(]+?)\s*(?:\((.*)\))?\s*$', a)
    name, affil = (m.group(1), m.group(2) or '') if m else (a, '')
    im = INST.search(affil)
    inst = im.group(1).strip() if im else (affil.split()[0] if affil.split() else '')
    return f'{name.strip()}|{inst}'


AU = {r['arti_id']: list(dict.fromkeys(akey(a) for a in (r['authors'] or '').split(';') if a.strip())) for r in inc}
by = {g: [r['arti_id'] for r in inc if r['group'] == g] for g in G}


def metrics(ids):
    nodes = set(); adj = defaultdict(set); sole = 0; npa = 0
    for i in ids:
        au = AU[i]; npa += len(au); sole += len(au) <= 1; nodes.update(au)
        for a in range(len(au)):
            for b in range(a + 1, len(au)):
                adj[au[a]].add(au[b]); adj[au[b]].add(au[a])
    n = len(nodes); E = sum(len(adj[a]) for a in nodes) // 2
    seen, comps = set(), []
    for a in nodes:
        if a in seen: continue
        st = [a]; seen.add(a); c = 0
        while st:
            x = st.pop(); c += 1
            for y in adj[x]:
                if y not in seen: seen.add(y); st.append(y)
        comps.append(c)
    return dict(per=npa / len(ids), sole=100 * sole / len(ids), iso=100 * sum(1 for a in nodes if not adj[a]) / n,
                mean_deg=2 * E / n, largest=max(comps), comps=len(comps))


K = [('per', '논문당 저자', '{:.2f}'), ('sole', '단독저자 논문 %', '{:.1f}'), ('iso', '고립 저자 %', '{:.1f}'),
     ('mean_deg', '평균 연결정도', '{:.2f}'), ('largest', '최대 공저 군집(명)', '{:.0f}'), ('comps', '연결 요소 수', '{:.0f}')]
n_zh = len(by['중국어'])
obs = metrics(by['중국어'])
full = {g: metrics(by[g]) for g in G}
dist = {g: [metrics(random.sample(by[g], n_zh)) for _ in range(REPS)] for g in ('영어', '한국어')}


def summ(vals, x):
    v = sorted(vals); q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    return q(0.5), q(0.05), q(0.95), 100 * sum(1 for y in v if y <= x) / len(v)


out = {'n_zh': n_zh, 'reps': REPS, 'observed_zh': obs, 'full': full, 'summary': {}}
L = [f'# 공저 네트워크 지표의 규모 기대값 ({DATE})\n',
     f'영어군·한국어군에서 중국어군과 같은 {n_zh}편을 {REPS}회 비복원 추출(시드 20260930)해 <표 8>과 같은 규칙으로 산출한 분포. '
     '백분위는 추출 분포에서 중국어 실측값 이하인 비율이다.\n',
     f'| 지표 | 중국어 실측({n_zh}편) | 영어 전체 | 영어 {n_zh}편 중앙값(5–95%) | 백분위 | 한국어 전체 | 한국어 {n_zh}편 중앙값(5–95%) | 백분위 |',
     '|---|---|---|---|---|---|---|---|']
for k, lab, f in K:
    row = [lab, f.format(obs[k])]
    out['summary'][k] = {}
    for g in ('영어', '한국어'):
        md, lo, hi, pct = summ([d[k] for d in dist[g]], obs[k])
        out['summary'][k][g] = dict(median=md, p05=lo, p95=hi, pct_le=pct)
        row += [f.format(full[g][k]), f'{f.format(md)}({f.format(lo)}–{f.format(hi)})', f'{pct:.1f}']
    L.append('| ' + ' | '.join(row) + ' |')
big = {g: 100 * sum(1 for d in dist[g] if d['largest'] >= 9) / REPS for g in ('영어', '한국어')}
out['largest_ge9_pct'] = big
L += ['', '읽는 법: 중국어 실측이 5–95% 구간 안이면 그 지표의 차이는 편수 차이로 설명된다. 단독저자 비율은 논문 단위 비율이라 규모에 덜 민감하다.',
      f'최대 공저 군집이 9명 이상인 추출의 비율: 영어 {big["영어"]:.1f}%, 한국어 {big["한국어"]:.1f}%(원고 4.4.2).']
io.open(f'{REPO}/analysis/network_scale_{DATE}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
io.open(f'{REPO}/analysis/network_scale_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
