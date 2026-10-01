# -*- coding: utf-8 -*-
"""tables_8to11.py — 공저 네트워크와 피인용(원고 4.4.2·4.4.3): <표 8>(윗부분 세 행), <표 9>, <표 10>, <표 11>.

사용:  python scripts/analysis/tables_8to11.py [--date 1161_20261001]
산출:  analysis/tables_8to11_<DATE>.md, analysis/tables_8to11_<DATE>.json

- <표 8>: 저자명과 소속을 결합한 키를 노드로 삼는다(소속은 기관 수준으로 정규화). 공저 관계를 엣지로 하여
          언어군별로 단독저자 비율, 고립 저자 비율, 연결 요소 수, 최대 공저 군집, 평균 연결정도,
          한 저자의 최대 공저자 수(최대 연결정도), 매개 중심성 최댓값(Brandes, 2001)을 산출한다.
          하단 두 행(68편 추출)은 network_scale.py가 만든다.
- <표 9>~<표 11>: KCI 피인용 수(2026-09-29 조회, 판정 결과 파일의 cited 필드).
- <표 12>(참고문헌)는 references_school.py가 공개 집계(analysis/ref_aggregate_<DATE>.csv)로 만든다.
"""
import io, json, os, re, sys
from collections import defaultdict, deque
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
G = ['영어', '한국어', '중국어']
inc = [r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8')) if r.get('include') == 'Y']
by = {g: [o for o in inc if o['group'] == g] for g in G}

# ── <표 8> 공저 네트워크 ─────────────────────────────────────────────────────
INST = re.compile(r'([가-힣A-Za-z&\.\- ]*?(?:대학교|대학|학교|연구원|연구소|교육청|University|College|Institute|School))', re.I)
def akey(a):
    m = re.match(r'\s*([^(]+?)\s*(?:\((.*)\))?\s*$', a)
    name, affil = (m.group(1), m.group(2) or '') if m else (a, '')
    im = INST.search(affil)
    inst = im.group(1).strip() if im else (affil.split()[0] if affil.split() else '')
    return f'{name.strip()}|{inst}'

def authors_of(o):
    return list(dict.fromkeys(akey(a) for a in (o['authors'] or '').split(';') if a.strip()))

def betweenness(nodes, adj):
    """Brandes(2001) 무가중 무향 그래프 매개 중심성. 정규화: 2/((n-1)(n-2))."""
    bc = dict.fromkeys(nodes, 0.0)
    for s in nodes:
        S = []; P = defaultdict(list); sigma = dict.fromkeys(nodes, 0); sigma[s] = 1
        d = dict.fromkeys(nodes, -1); d[s] = 0; Q = deque([s])
        while Q:
            v = Q.popleft(); S.append(v)
            for w in adj[v]:
                if d[w] < 0: d[w] = d[v] + 1; Q.append(w)
                if d[w] == d[v] + 1: sigma[w] += sigma[v]; P[w].append(v)
        delta = dict.fromkeys(nodes, 0.0)
        while S:
            w = S.pop()
            for v in P[w]: delta[v] += sigma[v] / sigma[w] * (1 + delta[w])
            if w != s: bc[w] += delta[w]
    n = len(nodes)
    norm = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 0   # 무향: 합계를 2로 나누고 (n-1)(n-2)/2로 정규화
    return {v: bc[v] * norm for v in nodes}

def net(rows):
    nodes = set(); adj = defaultdict(set); sole = 0; npa = 0
    for o in rows:
        au = authors_of(o); npa += len(au)
        if len(au) <= 1: sole += 1
        nodes.update(au)
        for i in range(len(au)):
            for j in range(i + 1, len(au)):
                adj[au[i]].add(au[j]); adj[au[j]].add(au[i])
    for a in nodes: adj[a]  # 고립 노드도 키 생성
    n = len(nodes); E = sum(len(v) for v in adj.values()) // 2
    seen = set(); comps = []
    for a in sorted(nodes):
        if a in seen: continue
        st = [a]; seen.add(a); c = 0
        while st:
            x = st.pop(); c += 1
            for y in adj[x]:
                if y not in seen: seen.add(y); st.append(y)
        comps.append(c)
    iso = sum(1 for a in nodes if not adj[a])
    deg = {a: len(adj[a]) for a in nodes}
    dc = {a: deg[a] / (n - 1) for a in nodes} if n > 1 else {}
    bc = betweenness(sorted(nodes), adj)
    return dict(papers=len(rows), authors=n, per=npa / len(rows), sole=100 * sole / len(rows), iso=100 * iso / n,
                comps=len(comps), largest=max(comps), mean_deg=2 * E / n, edges=E,
                density=2 * E / (n * (n - 1)) if n > 1 else 0,
                deg_max=max(deg.values()), dc_mean=sum(dc.values()) / n, dc_max=max(dc.values()),
                bc_mean=sum(bc.values()) / n, bc_max=max(bc.values()))

N = {g: net(by[g]) for g in G}

# ── <표 9>~<표 11> 피인용 ───────────────────────────────────────────────────
cited = lambda o: o['cited'] or 0
tot = {g: sum(cited(o) for o in by[g]) for g in G}
per = {g: tot[g] / len(by[g]) for g in G}
coh = {}
for g in G:
    rows = [o for o in by[g] if 2020 <= int(o['year']) <= 2023]
    coh[g] = (sum(cited(o) for o in rows) / len(rows), len(rows))
med = {}
for g in G:
    cs = sorted(cited(o) for o in by[g]); k = len(cs)
    med[g] = cs[k // 2] if k % 2 else (cs[k // 2 - 1] + cs[k // 2]) / 2
zero = {g: 100 * sum(1 for o in by[g] if not cited(o)) / len(by[g]) for g in G}
_rank = sorted(inc, key=lambda o: (-cited(o), o['year'], o['arti_id']))
_cut = cited(_rank[9])   # 10위의 피인용 수. 동률은 끊지 않고 모두 싣는다
top = [o for o in _rank if cited(o) >= _cut]
def rank_of(o): return 1 + sum(1 for x in _rank if cited(x) > cited(o))  # 공동 순위

# ── 출력 ────────────────────────────────────────────────────────────────────
L = [f'# 공저 네트워크와 피인용 ({DATE})\n',
     f'분석 코퍼스 {len(inc):,}편(영어 {len(by["영어"])} · 한국어 {len(by["한국어"])} · 중국어 {len(by["중국어"])}).\n',
     '## <표 8> 언어군별 공저 네트워크 지표\n',
     '| 언어군 | 논문 | 저자(명) | 논문당 평균 저자 | 단독저자 논문 | 고립 저자 비율 | 연결 요소 | 최대 공저 군집 | 평균 연결정도 | 한 저자의 최대 공저자 수 | 매개 중심성 최댓값 |',
     '|---|---|---|---|---|---|---|---|---|---|---|']
for g in G:
    d = N[g]
    L.append(f'| {g} | {d["papers"]} | {d["authors"]} | {d["per"]:.2f} | {d["sole"]:.1f}% | {d["iso"]:.1f}% | {d["comps"]} | '
             f'{d["largest"]}명({100 * d["largest"] / d["authors"]:.1f}%) | {d["mean_deg"]:.2f} | {d["deg_max"]} | {d["bc_max"]:.4f} |')
L += ['', '참고 지표:\n', '| 지표 | 영어 | 한국어 | 중국어 |', '|---|---|---|---|',
      '| 공저 관계(엣지) 수 | ' + ' | '.join(str(N[g]['edges']) for g in G) + ' |',
      '| 밀도 | ' + ' | '.join(f'{N[g]["density"]:.4f}' for g in G) + ' |',
      '| 연결정도 중심성 평균 | ' + ' | '.join(f'{N[g]["dc_mean"]:.4f}' for g in G) + ' |',
      '| 연결정도 중심성 최댓값 | ' + ' | '.join(f'{N[g]["dc_max"]:.4f}' for g in G) + ' |',
      '| 매개 중심성 평균 | ' + ' | '.join(f'{N[g]["bc_mean"]:.5f}' for g in G) + ' |',
      '', '하단 두 행(영어·한국어에서 68편 추출)은 `analysis/network_scale_<DATE>.md`에 있다.',
      '', f'## <표 9> 피인용 상위 논문(10위 동률 포함 {len(top)}편, KCI 2026-09-29 조회)\n',
      '| 순위 | artiId | 제목 | 연도 | 언어군 | 피인용 |', '|---|---|---|---|---|---|']
for o in top:
    L.append(f'| {rank_of(o)} | {o["arti_id"]} | {o["title_ko"] or o["title_en"]} | {o["year"]} | {o["group"]} | {cited(o)} |')
L += ['', f'코퍼스 전체 총 피인용 {sum(tot.values()):,}회.',
      '', '## <표 10> 언어군별 피인용 결과\n', '| 언어군 | 논문 수 | 총 피인용 | 편당 평균 | 중앙값 | 피인용 0편 비율 |', '|---|---|---|---|---|---|']
for g in G:
    L.append(f'| {g} | {len(by[g])} | {tot[g]:,} | {per[g]:.2f} | {med[g]:g} | {zero[g]:.1f}% |')
L += ['', '## <표 11> 코호트별 편당 평균 인용\n', '| 기간 | 영어 | 한국어 | 중국어 | 영/중 배율 |', '|---|---|---|---|---|',
      f'| 2020–2026 | {per["영어"]:.2f}({len(by["영어"])}편) | {per["한국어"]:.2f}({len(by["한국어"])}편) | {per["중국어"]:.2f}({len(by["중국어"])}편) | {per["영어"] / per["중국어"]:.1f}배 |',
      f'| 2020–2023 | {coh["영어"][0]:.2f}({coh["영어"][1]}편) | {coh["한국어"][0]:.2f}({coh["한국어"][1]}편) | {coh["중국어"][0]:.2f}({coh["중국어"][1]}편) | {coh["영어"][0] / coh["중국어"][0]:.1f}배 |']
io.open(f'{REPO}/analysis/tables_8to11_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
io.open(f'{REPO}/analysis/tables_8to11_{DATE}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
    table8=N,
    table9=[dict(rank=rank_of(o), arti_id=o['arti_id'], title=o['title_ko'] or o['title_en'], year=o['year'], group=o['group'], cited=cited(o)) for o in top],
    total_cited=sum(tot.values()),
    table10=dict(total=tot, per_paper=per, median=med, zero_pct=zero, as_of='2026-09-29'),
    table11={g: dict(per_paper_2020_2026=per[g], per_paper_2020_2023=coh[g][0], n_2020_2023=coh[g][1]) for g in G}),
    ensure_ascii=False, indent=1) + '\n')
print('\n'.join(L))
