# -*- coding: utf-8 -*-
"""references_school.py — 공개한 논문별 집계 두 개로 원고의 해당 수치를 다시 계산한다.
  analysis/ref_aggregate_<DATE>.csv  → <표 12> 언어군별 참고문헌 지식 원천과 4.4.3 각주(대상 편수, 학술지명 없는 비율)
  analysis/school_level_<DATE>.csv   → 5.2 첫째 문단과 각주의 학교급 편수
두 집계는 KCI 원자료(참고문헌 목록, 초록)에서 scripts/pipeline/ref_aggregate.pl, school_level.py로 만들었다.
원자료는 재배포하지 않는다(README 참조).

산출: analysis/references_school_<DATE>.md
사용: python scripts/analysis/references_school.py [--date 1161_20261001]
"""
import csv, io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
G = ['영어', '한국어', '중국어']


def read_csv(name):
    with open(f'{REPO}/analysis/{name}_{DATE}.csv', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


L = [f'# 참고문헌 지식 원천과 학교급 ({DATE})\n', '## <표 12> 언어군별 참고문헌 지식 원천\n',
     '| 언어군 | 대상 편수 | 편당 평균 참고문헌 | 국내 문헌 | 국제 문헌(그 가운데 중문) | 학술지명 없음 | 교육 | 언어학 | 문학 | 기타 |',
     '|---|---|---|---|---|---|---|---|---|---|']
ref = read_csv('ref_aggregate')
K = ['참고문헌수', '국내_한글', '중문_한자', '그밖_국제', '학술지명있음', '교육', '언어학', '문학', '기타']
for g in G:
    allg = [r for r in ref if r['언어군'] == g]
    w = [r for r in allg if r['참고문헌목록'] == 'Y']
    s = {k: sum(int(r[k]) for r in w) for k in K}
    n, nj = s['참고문헌수'], s['학술지명있음']
    L.append(f'| {g} | {len(w)}/{len(allg)} | {n / len(w):.1f}건 | {100 * s["국내_한글"] / n:.1f}% | '
             f'{100 * (s["중문_한자"] + s["그밖_국제"]) / n:.1f}% ({100 * s["중문_한자"] / n:.1f}%) | {100 - 100 * nj / n:.0f}% | '
             f'{100 * s["교육"] / nj:.1f}% | {100 * s["언어학"] / nj:.1f}% | {100 * s["문학"] / nj:.1f}% | {100 * s["기타"] / nj:.1f}% |')
L += ['', '국내·국제는 참고문헌 전체를, 분야(교육·언어학·문학·기타)는 학술지명이 있는 문헌을 분모로 한다. '
      '중문은 참고문헌 전체에서 차지하는 비율이다.', '']

sch = read_csv('school_level')
L += ['## 5.2 학교급(제목·초록에 드러난 맥락)\n', '| 언어군 | 편수 | 초·중등 | 대학 | 둘 다 없음 |', '|---|---|---|---|---|']
for g in ('영어', '한국어(L1)', '한국어(L2)', '한국어(미명시)', '중국어'):
    r = [x for x in sch if (f"한국어({x['학습자맥락']})" if x['언어군'] == '한국어' else x['언어군']) == g]
    if not r: continue
    s = sum(1 for x in r if x['초중등'] == '1'); u = sum(1 for x in r if x['대학'] == '1')
    none = sum(1 for x in r if x['초중등'] != '1' and x['대학'] != '1')
    L.append(f'| {g} | {len(r)} | {s} | {u} | {none} |')
L += ['', '한 논문이 두 범주에 모두 들 수 있다. 원고는 한국어군 가운데 외국어 학습자(L2) 연구만 보고한다.']
io.open(f'{REPO}/analysis/references_school_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
