# -*- coding: utf-8 -*-
"""school_level.py — 논문별 학교급 표지(원고 5.2 첫째 문단과 각주의 공개용 입력). 초록이 든 원자료가 필요하다.

초록은 재배포하지 않으므로, 제목·초록에서 판정한 학교급 표지만 논문마다 남긴다.
  - 초·중등: 초등·중학·고등학교·고교·중등·다문화 학생/아동(중문 小学·中学·高中)
  - 대학: 대학(대학수학능력시험 제외)·학부·유학생·교양·전공·학문 목적(중문 大学·本科, 영문 university·undergraduate·college)
  - 한 논문이 두 범주에 모두 들 수 있다.
입력: data/rejudge/merged_<DATE>.json 가운데 초록(abstract_ko)이 있는 판정 결과(공개본에는 초록이 없다)
산출: analysis/school_level_<DATE>.csv(UTF-8, BOM). 원고 수치는 scripts/analysis/references_school.py가 이 파일로 계산한다.
사용: python scripts/rejudge/school_level.py [--date 1161_20261001]
"""
import io, json, os, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
RE_SCHOOL = re.compile(r'초등|중학|고등학교|고교|중등|다문화 ?(?:학생|아동)|小学|中学|高中')
RE_UNIV = re.compile(r'대학(?!수학능력)|학부|유학생|교양|전공|학문 목적|大学|本科|university|undergraduate|college', re.I)

recs = json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8'))
inc = [r for r in recs if r['include'] == 'Y']
if not any(r.get('abstract_ko') for r in inc):
    sys.exit('초록이 없는 판정 결과다(공개본). 학교급 집계는 배포한 analysis/school_level_<DATE>.csv를 쓴다. 덮어쓰지 않고 멈춘다.')
rows = []
for r in inc:
    txt = (r.get('title_ko') or '') + ' ' + (r.get('abstract_ko') or '')
    rows.append([r['arti_id'], r['group'], r['learner'] if r['group'] == '한국어' else '',
                 int(bool(RE_SCHOOL.search(txt))), int(bool(RE_UNIV.search(txt)))])
rows.sort()
out = f'{REPO}/analysis/school_level_{DATE}.csv'
with io.open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write('artiId,언어군,학습자맥락,초중등,대학\n')
    for row in rows: f.write(','.join(map(str, row)) + '\n')
print(f'확정 코퍼스 {len(rows)}편 → {out}')
