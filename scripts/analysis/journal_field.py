# -*- coding: utf-8 -*-
"""journal_field.py — 게재 학술지의 학문 분야(원고 4.4.3 각주, 5.2 둘째 층위).

학문 분야는 KCI 서지정보의 분류(kci_field, '대분류 > 중분류 > …')이며 중분류를 기준으로 센다.
산출: analysis/journal_field_<DATE>.md
사용: python scripts/analysis/journal_field.py [--date 1161_20261001]
"""
import io, json, os, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '1161_20261001'
G = ['영어', '한국어', '중국어']
inc = [r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8')) if r['include'] == 'Y']
mid = lambda r: (r['kci_field'] or '').split(' > ')[1] if len((r['kci_field'] or '').split(' > ')) > 1 else '(분류 없음)'
pct = lambda a, b: f'{100 * a / b:.1f}%'

L = [f'# 게재 학술지의 학문 분야 ({DATE})\n', 'KCI 서지정보의 학문 분류(중분류 기준).\n',
     '## 1. 교육학 분야 학술지에 실린 논문\n', '| 언어군 | 편수 | 교육학(중분류) |', '|---|---|---|']
lv2 = {g: Counter(mid(r) for r in inc if r['group'] == g) for g in G}
n = {g: sum(lv2[g].values()) for g in G}
for g in G:
    L.append(f'| {g} | {n[g]} | {lv2[g]["교육학"]} ({pct(lv2[g]["교육학"], n[g])}) |')
L += ['', '## 2. 중분류 분포(언어군별 상위 6)\n']
for g in G:
    L.append(f'- {g}: ' + ', '.join(f'{k} {v}({pct(v, n[g])})' for k, v in sorted(lv2[g].items(), key=lambda kv: (-kv[1], kv[0]))[:6]))
zl, zt = lv2['중국어']['중국어와문학'], lv2['중국어']['통역번역학']
L += ['', f'중국어군 {n["중국어"]}편 가운데 중국어와문학 {zl}편 + 통역번역학 {zt}편 = {zl + zt}편({pct(zl + zt, n["중국어"])}).', '',
      '## 3. 중국어군 게재 학술지\n',
      ', '.join(f'{k} {v}' for k, v in sorted(Counter(r['journal'] for r in inc if r['group'] == '중국어').items(), key=lambda kv: (-kv[1], kv[0])))]
io.open(f'{REPO}/analysis/journal_field_{DATE}.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
