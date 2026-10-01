# -*- coding: utf-8 -*-
"""descriptives.py — 판정 결과의 기초 집계: 원고 3.1, 4.1–4.3의 편수·비율과 <표 1>~<표 4>, <그림 1>~<그림 3>의 값.

입력: data/rejudge/merged_<DATE>.json (후보 1,644편의 판정 결과, include == 'Y'가 분석 코퍼스)
산출: analysis/descriptives_<DATE>.md, analysis/descriptives_<DATE>.json
사용: python scripts/analysis/descriptives.py [--date 1161_20261001]
"""
import io, json, os, re, sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
G = ['영어', '한국어', '중국어']
# <표 2>와 <표 4>의 행 순서
METHS = ['개발연구', '실험연구', '조사연구', '질적·사례', '성능평가', '문헌·리뷰', '코퍼스분석', '기타·혼합']
FUNCS = ['쓰기', '기능비특정', '말하기', '평가·채점', '읽기', '리터러시·역량', '번역', '문법', '문학·문화', '발음', '어휘', '듣기']
FOCUS = ['교사·교육주체', '학습자 인식·수용·정의적', '연구동향·메타분석', '일반 논의·활용 제언', '도구·자원 개발']
# <표 1>의 제외 범주와 판정 결과의 제외 사유 코드(부록 A의 <표 A3>)
EXCL = [('세 언어군 밖 외국어', ['제2외국어']),
        ('교육맥락 없는 순수 연구', ['교육맥락없음', '번역품질']),
        ('AI 비중심 연구', ['메타버스VR', '비AI에듀테크', 'AI신호부재']),
        ('언어 비특정 일반 연구', ['언어비특정']),
        ('대학 교양 교육 연구', ['교양교육']),
        ('국어 교과 담론형 연구', ['국어교과담론']),
        ('AI 디지털교과서 연구', ['AI디지털교과서']),
        ('복수언어 연구', ['복수언어']),
        ('기타', ['기타'])]

recs = json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8'))
inc = [r for r in recs if r['include'] == 'Y']
exc = [r for r in recs if r['include'] != 'Y']
by = {g: [r for r in inc if r['group'] == g] for g in G}
n = {g: len(by[g]) for g in G}
N = len(inc)
pct = lambda a, b: 100 * a / b if b else 0.0
out = {'date': DATE, 'candidates': len(recs), 'included': N, 'excluded': len(exc), 'by_group': n}
L = [f'# 판정 결과의 기초 집계 ({DATE})\n',
     f'후보 {len(recs):,}편 가운데 포함 {N:,}편, 제외 {len(exc)}편. '
     + ', '.join(f'{g} {n[g]}편({pct(n[g], N):.1f}%)' for g in G) + '. (원고 3.1, <그림 1>)\n']

# <표 1> 제외 기준
rc = Counter(r['reason'] for r in exc)
assert sum(rc[c] for _, cs in EXCL for c in cs) == len(exc), '제외 사유 코드가 <표 1> 범주에 모두 대응하지 않는다'
L += ['## <표 1> 분석 코퍼스 제외 기준\n', '| 구분 | 사유 코드 | 제외 편수 |', '|---|---|---|']
out['table1'] = {}
for lab, cs in EXCL:
    k = sum(rc[c] for c in cs)
    out['table1'][lab] = k
    L.append(f'| {lab} | {"·".join(cs)} | {k} |')
L.append(f'| 계 | | {len(exc)} |')

# 학습자 맥락(한국어군), 3.2 각주
lc = Counter(r['learner'] or '미명시' for r in by['한국어'])
out['korean_learner'] = dict(lc)
L += ['', '## 한국어군의 학습자 맥락(3.2 각주)\n',
      f'모어 화자(L1) {lc["L1"]}편({pct(lc["L1"], n["한국어"]):.1f}%), 외국어 학습자(L2) {lc["L2"]}편, 미명시 {lc["미명시"]}편.']

# 연도별·언어군별(<그림 2>, 4.1)
years = sorted({int(r['year']) for r in inc})
yc = {y: Counter(r['group'] for r in inc if int(r['year']) == y) for y in years}
out['year_group'] = {y: {g: yc[y][g] for g in G} for y in years}
L += ['', '## 연도별·언어군별 편수(<그림 2>, 4.1)\n', '| 연도 | 영어 | 한국어 | 중국어 | 계 | 영어 비중 | 중국어 비중 |', '|---|---|---|---|---|---|---|']
for y in years:
    t = sum(yc[y].values())
    L.append(f'| {y} | {yc[y]["영어"]} | {yc[y]["한국어"]} | {yc[y]["중국어"]} | {t} | {pct(yc[y]["영어"], t):.1f}% | {pct(yc[y]["중국어"], t):.1f}% |')
L.append(f'| 계 | {n["영어"]} | {n["한국어"]} | {n["중국어"]} | {N} | | |')
early = [r for r in inc if int(r['year']) <= 2022]
late = [r for r in inc if int(r['year']) >= 2023]
tc = Counter(r['tool'] for r in early)
out['tools_2020_2022'] = dict(tc)
L += ['', f'2020–2022년 {len(early)}편의 핵심 도구: ' + ', '.join(f'{k} {v}편({pct(v, len(early)):.1f}%)' for k, v in tc.most_common()) + '.']

# <표 2> 연구방법 분포
mc = {g: Counter(r['meth'] for r in by[g]) for g in G}
out['table2'] = {m: {g: mc[g][m] for g in G} for m in METHS}
L += ['', '## <표 2> 연구방법 분포\n', '| 방법 | 영어 | 한국어 | 중국어 | 논문 수 | 비율 |', '|---|---|---|---|---|---|']
for m in METHS:
    t = sum(mc[g][m] for g in G)
    L.append(f'| {m} | {mc["영어"][m]} | {mc["한국어"][m]} | {mc["중국어"][m]} | {t} | {pct(t, N):.1f}% |')
L.append(f'| 합계 | {n["영어"]} | {n["한국어"]} | {n["중국어"]} | {N:,} | 100.0% |')
dsq = sum(mc[g][m] for g in G for m in ('개발연구', '조사연구', '질적·사례'))
L.append(f'\n개발연구·조사연구·질적·사례 합 {dsq}편({pct(dsq, N):.1f}%).')
L += ['', '시기별 비중(ChatGPT 공개 이전 2020–2022년, 이후 2023–2026년):\n', '| 지표 | 2020–2022 | 2023–2026 |', '|---|---|---|',
      f'| 편수 | {len(early)} | {len(late)} |']
out['period'] = {}
for lab, ms in (('실험연구', ('실험연구',)), ('성능평가', ('성능평가',)), ('조사연구+질적·사례', ('조사연구', '질적·사례'))):
    a = pct(sum(r['meth'] in ms for r in early), len(early)); b = pct(sum(r['meth'] in ms for r in late), len(late))
    out['period'][lab] = [a, b]
    L.append(f'| {lab} | {a:.1f}% | {b:.1f}% |')

# <그림 3> 실험연구와 구축·평가형
L += ['', '## <그림 3> 언어군별 실험연구와 구축·평가형(개발연구+성능평가) 비중\n', '| 언어군 | 실험연구 | 구축·평가형 |', '|---|---|---|']
out['figure3'] = {}
for g in G:
    x = mc[g]['실험연구']; b = mc[g]['개발연구'] + mc[g]['성능평가']
    out['figure3'][g] = dict(exp=x, build=b)
    L.append(f'| {g} | {x}편({pct(x, n[g]):.1f}%) | {b}편({pct(b, n[g]):.1f}%) |')
tx = sum(mc[g]['실험연구'] for g in G)
L.append(f'\n실험연구 {tx}편 가운데 영어군 {mc["영어"]["실험연구"]}편({pct(mc["영어"]["실험연구"], tx):.1f}%).')
zl = [r for r in by['중국어'] if r['meth'] == '문헌·리뷰']
L.append(f'중국어군 문헌·리뷰 {len(zl)}편 가운데 담론·시론 {sum(r["paper_type"] == "담론" for r in zl)}편(4.2 각주).')

# <표 3> 기능 비특정 연구의 초점
ns = [r for r in inc if r['func'] == '기능비특정']
fc = {g: Counter(r['focus'] for r in ns if r['group'] == g) for g in G}
out['table3'] = {f: {g: fc[g][f] for g in G} for f in FOCUS}
L += ['', f'## <표 3> 기능 비특정 연구의 초점 분포\n', f'특정 기능 {N - len(ns)}편({pct(N - len(ns), N):.1f}%), 기능 비특정 {len(ns)}편({pct(len(ns), N):.1f}%).\n',
      '| 연구 초점 | 영어 | 한국어 | 중국어 | 합계 | 비중 |', '|---|---|---|---|---|---|']
for f in FOCUS:
    t = sum(fc[g][f] for g in G)
    L.append(f'| {f} | {fc["영어"][f]} | {fc["한국어"][f]} | {fc["중국어"][f]} | {t} | {pct(t, len(ns)):.1f}% |')
L.append(f'| 합계 | {sum(fc["영어"].values())} | {sum(fc["한국어"].values())} | {sum(fc["중국어"].values())} | {len(ns)} | 100.0% |')
acc = sum(fc[g][f] for g in G for f in FOCUS[:2]); acc3 = acc + sum(fc[g][FOCUS[2]] for g in G)
zg = [r for r in ns if r['group'] == '중국어' and r['focus'] == '일반 논의·활용 제언']
L.append(f'\n학습자·교사 초점 합 {acc}편({pct(acc, len(ns)):.1f}%), 연구동향을 더하면 {acc3}편({pct(acc3, len(ns)):.1f}%). '
         f'중국어군 일반 논의·활용 제언 {len(zg)}편 가운데 담론·시론 {sum(r["paper_type"] == "담론" for r in zg)}편.')

# <표 4> 언어기능 분포
fu = {g: Counter(r['func'] for r in by[g]) for g in G}
out['table4'] = {f: {g: fu[g][f] for g in G} for f in FUNCS}
L += ['', '## <표 4> 언어군별 언어기능 분포\n', '| 기능 | 영어 | 한국어 | 중국어 | 합계 | 전체 비율 |', '|---|---|---|---|---|---|']
for f in FUNCS:
    t = sum(fu[g][f] for g in G)
    L.append(f'| {"기능 비특정" if f == "기능비특정" else f} | ' + ' | '.join(f'{fu[g][f]}({pct(fu[g][f], n[g]):.1f}%)' for g in G) + f' | {t} | {pct(t, N):.1f}% |')
L.append(f'| 합계 | {n["영어"]} | {n["한국어"]} | {n["중국어"]} | {N:,} | 100.0% |')
grid = {g: n[g] - fu[g]['기능비특정'] for g in G}
out['grid_papers'] = grid
prod = sum(fu[g][f] for g in G for f in ('쓰기', '말하기'))
ko_l1_eval = sum(1 for r in by['한국어'] if r['func'] == '평가·채점' and r['learner'] == 'L1')
L.append(f'\n격자 대상(기능 비특정 제외) {sum(grid.values())}편: ' + ', '.join(f'{g} {grid[g]}편' for g in G) + '. '
         f'쓰기+말하기 {prod}편({pct(prod, N):.1f}%). 영어군 쓰기+말하기 {fu["영어"]["쓰기"] + fu["영어"]["말하기"]}편'
         f'({pct(fu["영어"]["쓰기"] + fu["영어"]["말하기"], n["영어"]):.1f}%). 한국어군 평가·채점 {fu["한국어"]["평가·채점"]}편 가운데 모어 화자(L1) {ko_l1_eval}편.')

forms = {k.strip() for r in recs for f in ('kw_ko', 'kw_en') for k in re.split(r'[;,]', r.get(f) or '') if k.strip()}
out['keyword_forms_1644'] = len(forms)
L.append(f'\n1차 수집 {len(recs):,}편의 주제어(국문·영문, 쌍반점·쉼표로 나누고 앞뒤 공백만 정리) 서로 다른 표기 {len(forms):,}개(부록 B.4).')

io.open(f'{REPO}/analysis/descriptives_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
io.open(f'{REPO}/analysis/descriptives_{DATE}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print('\n'.join(L))
