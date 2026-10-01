# -*- coding: utf-8 -*-
"""merge_rejudge.py — 초록 재판정 배치 결과(data/rejudge/out/*.json)를 병합·검증하고
판정 결과 JSON과 엑셀, 요약을 만든다. 공개본은 make_public.py가 이 결과에서 만든다.

사용:  python scripts/rejudge/merge_rejudge.py [--date 20260930]
산출:  data/rejudge/merged_YYYYMMDD.json           (전 1,644편 판정+코딩+서지)
       data/KCI_코퍼스확정_YYYYMMDD.xlsx            (초록 열 없음)
       data/KCI_코퍼스확정_YYYYMMDD_초록포함.xlsx   (저자 검수용, 재배포하지 않음)
       analysis/rejudge_summary_YYYYMMDD.md         (편수·분포, 작업용. analysis/paper_targets.json이 있을 때만)
"""
import json, os, sys, glob, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import Counter, defaultdict

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '20260930'
GROUPS = ['영어', '한국어', '중국어']
FUNCS = ['쓰기', '말하기', '평가·채점', '읽기', '리터러시·역량', '번역', '문법', '문학·문화', '발음', '어휘', '듣기', '기능비특정']
METHS = ['개발연구', '조사연구', '질적·사례', '실험연구', '문헌·리뷰', '성능평가', '코퍼스분석', '기타·혼합']
TOOLS = ['ChatGPT', '생성형AI일반', '중국어LLM', '챗봇', '기계번역', '음성인식·TTS', 'BERT·NLP', '기타']
FOCUS = ['교사·교육주체', '학습자 인식·수용·정의적', '연구동향·메타분석', '일반 논의·활용 제언', '도구·자원 개발']
REASONS = ['제2외국어', '언어비특정', 'AI신호부재', '비AI에듀테크', '메타버스VR', '교육맥락없음', '번역품질', '국어교과담론', '기타']
LEARNERS = ['L1', 'L2', '미명시', '']

# 동의어 정규화(코더가 약간 다르게 쓴 값)
NORM = {
    'func': {'리터러시': '리터러시·역량', '평가': '평가·채점', '채점': '평가·채점', '문학': '문학·문화', '문화': '문학·문화', '비특정': '기능비특정'},
    'meth': {'개발': '개발연구', '조사': '조사연구', '실험': '실험연구', '코퍼스': '코퍼스분석', '질적': '질적·사례', '사례': '질적·사례',
             '문헌': '문헌·리뷰', '리뷰': '문헌·리뷰', '기타': '기타·혼합', '혼합': '기타·혼합', '성능': '성능평가'},
    'tool': {'생성형AI': '생성형AI일반', '생성형 AI': '생성형AI일반', 'GPT': 'ChatGPT', '챗GPT': 'ChatGPT', 'chatgpt': 'ChatGPT',
             'NLP': 'BERT·NLP', 'BERT': 'BERT·NLP', '음성인식': '음성인식·TTS', 'TTS': '음성인식·TTS', 'MT': '기계번역', '번역기': '기계번역'},
}

def norm(kind, v, allowed):
    v = (v or '').strip()
    if v in allowed: return v
    if v in NORM[kind]: return NORM[kind][v]
    for a in allowed:
        if v and (v in a or a in v): return a
    return v

def main():
    rows = json.load(open(f'{REPO}/data/corpus_full_merged.json', encoding='utf-8'))
    orig = {r['arti_id']: r for r in rows if r['src'] in ('원본', '원본+보충')}
    batches = {}
    for f in sorted(glob.glob(f'{REPO}/data/rejudge/batches/b*.json')):
        for rec in json.load(open(f, encoding='utf-8')):
            batches[rec['id']] = (os.path.basename(f), rec)
    outs = {}
    problems = []
    for f in sorted(glob.glob(f'{REPO}/data/rejudge/out/b*.json')):
        try:
            data = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            problems.append(f'{os.path.basename(f)}: JSON 파싱 실패 {e}'); continue
        for o in data:
            if o['id'] in outs: problems.append(f'{o["id"]} 중복 판정'); continue
            outs[o['id']] = o
    missing = [i for i in batches if i not in outs]
    done_batches = sorted({batches[i][0] for i in outs})
    print(f'배치 {len(done_batches)}/{len(set(b for b, _ in batches.values()))} 완료, 판정 {len(outs)} / {len(batches)}, 누락 {len(missing)}')
    if missing:
        mb = Counter(batches[i][0] for i in missing)
        print('  누락 배치:', dict(mb))

    merged = []
    for aid, (bname, rec) in batches.items():
        r = orig[aid]; o = outs.get(aid)
        m = dict(arti_id=aid, batch=bname, sheet=r['orig_group'], year=r['year'], journal=r['journal'], publisher=r.get('publisher'),
                 kci_field=r.get('kci_field'), title_ko=r.get('title_ko'), title_en=r.get('title_en'), authors=r.get('authors'),
                 n_authors=r.get('n_authors'), kw_ko=r.get('kw_ko'), kw_en=r.get('kw_en'), abstract_ko=r.get('abstract_ko'),
                 abstract_en=r.get('abstract_en'), cited=r.get('cited'), n_refs=r.get('n_refs'), doi=r.get('doi'), permalink=r.get('permalink'),
                 prev_include=rec['prev_include'], prev_group=rec['prev_group'], prev_reason=rec['prev_reason'])
        if o is None:
            m.update(include='', reason='미판정'); merged.append(m); continue
        inc = (o.get('include') or '').strip().upper()[:1]
        m['include'] = 'Y' if inc == 'Y' else 'N'
        m['group'] = norm('func', o.get('group'), GROUPS) if o.get('group') in GROUPS else (o.get('group') or '')
        m['learner'] = (o.get('learner') or '').strip()
        m['func'] = norm('func', o.get('func'), FUNCS) if m['include'] == 'Y' else ''
        m['meth'] = norm('meth', o.get('meth'), METHS) if m['include'] == 'Y' else ''
        m['tool'] = norm('tool', o.get('tool'), TOOLS) if m['include'] == 'Y' else ''
        m['focus'] = (o.get('focus') or '').strip()
        m['ai_role'] = (o.get('ai_role') or '').strip()
        m['paper_type'] = (o.get('paper_type') or '').strip()
        m['confidence'] = (o.get('confidence') or '').strip().lower()
        m['boundary'] = 'Y' if (o.get('boundary') or '').strip().upper().startswith('Y') else 'N'
        m['note'] = (o.get('note') or '').strip()
        m['reason'] = (o.get('reason') or '').strip() if m['include'] == 'N' else ''
        # 검증
        if m['include'] == 'Y':
            if m['group'] not in GROUPS: problems.append(f'{aid} 포함이나 언어군 불명: {o.get("group")}')
            if m['func'] not in FUNCS: problems.append(f'{aid} 기능 값 불명: {o.get("func")}')
            if m['meth'] not in METHS: problems.append(f'{aid} 방법 값 불명: {o.get("meth")}')
            if m['tool'] not in TOOLS: problems.append(f'{aid} 도구 값 불명: {o.get("tool")}')
            if m['func'] == '기능비특정' and m['focus'] not in FOCUS: problems.append(f'{aid} 기능비특정인데 초점 불명: {o.get("focus")}')
            if m['group'] == '한국어' and m['learner'] not in ('L1', 'L2', '미명시'): problems.append(f'{aid} 한국어군 학습자맥락 불명: {o.get("learner")}')
            if m['group'] != '한국어': m['learner'] = ''
        else:
            if m['reason'] not in REASONS: problems.append(f'{aid} 제외사유 불명: {o.get("reason")}')
        merged.append(m)
    json.dump(merged, open(f'{REPO}/data/rejudge/merged_{DATE}.json', 'w', encoding='utf-8'), ensure_ascii=False)
    if problems:
        print(f'검증 문제 {len(problems)}건:'); [print('  ', p) for p in problems[:60]]
    return merged, problems, missing

def summarize(merged, problems, missing):
    if not os.path.exists(f'{REPO}/analysis/paper_targets.json'):
        print('analysis/paper_targets.json이 없어 작업용 요약은 건너뛴다.')
        return None
    PT = json.load(open(f'{REPO}/analysis/paper_targets.json', encoding='utf-8'))
    inc = [m for m in merged if m['include'] == 'Y']
    exc = [m for m in merged if m['include'] == 'N']
    L = []
    L.append(f'# 초록 재판정 결과 요약 ({DATE})\n')
    L.append(f'판정 대상 {len(merged)}편(1차 수집본) 중 포함 {len(inc)} · 제외 {len(exc)} · 미판정 {len(missing)}. 검증 문제 {len(problems)}건.\n')
    cg = Counter(m['group'] for m in inc)
    L.append('## 1. 언어군 편수 (논문 → 정직 판정본 → 재판정)\n')
    L.append('| 언어군 | 논문 | 규칙 판정(9/29) | 초록 재판정 | 비율 |\n|---|---|---|---|---|')
    prev = Counter(m['prev_group'] for m in merged if m['prev_include'] == 'Y')
    for g in GROUPS:
        L.append(f'| {g} | {PT["groups"][g]} | {prev[g]} | {cg[g]} | {100*cg[g]/max(1,len(inc)):.1f}% |')
    L.append(f'| 계 | {sum(PT["groups"].values())} | {sum(prev.values())} | {len(inc)} | 100% |\n')
    if merged and 'lang3' in merged[0]:
        L.append('### 언어 범주 (1차 수집 전체, 영어·한국어·중국어 세 범주)\n')
        L.append('| 언어 범주 | 포함 | 제외 | 계 |\n|---|---|---|---|')
        for g in GROUPS + ['해당 없음']:
            a = sum(1 for m in inc if m['lang3'] == g); b = sum(1 for m in exc if m['lang3'] == g)
            L.append(f'| {g} | {a} | {b} | {a + b} |')
        L.append(f'| 계 | {len(inc)} | {len(exc)} | {len(merged)} |\n')
        L.append('‘해당 없음’은 세 언어에 속하지 않거나(제2외국어) 대상 언어가 없는(언어비특정·복수언어) 제외 논문이다.\n')
    L.append('## 2. 판정 변화\n')
    ch = Counter((m['prev_include'], m['include']) for m in merged if m['include'])
    L.append(f'- 규칙 포함→재판정 제외: {ch[("Y","N")]}편, 규칙 제외→재판정 포함: {ch[("N","Y")]}편, 유지: {ch[("Y","Y")]+ch[("N","N")]}편')
    L.append('- 규칙 포함→제외 사유: ' + ', '.join(f'{k} {v}' for k, v in Counter(m['reason'] for m in merged if m['prev_include']=='Y' and m['include']=='N').most_common()))
    L.append('- 규칙 제외→포함의 원 제외사유: ' + ', '.join(f'{k} {v}' for k, v in Counter(m['prev_reason'] for m in merged if m['prev_include']=='N' and m['include']=='Y').most_common()))
    gc = Counter((m['prev_group'], m['group']) for m in inc if m['prev_include']=='Y' and m['prev_group'] != m['group'])
    L.append('- 언어군 재배정: ' + (', '.join(f'{a}→{b} {n}' for (a, b), n in gc.most_common()) or '없음') + '\n')
    L.append('## 3. 제외 사유 분포 (각주 2 대응)\n')
    L.append('| 사유 | 재판정 | 논문 각주 2 |\n|---|---|---|')
    er = Counter(m['reason'] for m in exc)
    for k in REASONS: L.append(f'| {k} | {er[k]} | {PT["footnote2_exclusions"].get(k, "-")} |')
    L.append(f'| 계 | {len(exc)} | {PT["footnote2_exclusions"]["total"]} |\n')
    L.append('## 4. 한국어군 학습자 맥락\n')
    lc = Counter(m['learner'] for m in inc if m['group'] == '한국어')
    L.append(', '.join(f'{k or "(빈값)"} {v}' for k, v in lc.most_common()) + f' · 담론형(paper_type=담론) 한국어군 {sum(1 for m in inc if m["group"]=="한국어" and m["paper_type"]=="담론")}편\n')
    L.append('## 5. 연도별 편수 (그림 2)\n')
    L.append('| 연도 | 영어 | 한국어 | 중국어 | 계 | 논문 계 |\n|---|---|---|---|---|---|')
    yc = defaultdict(Counter)
    for m in inc: yc[m['year']][m['group']] += 1
    for y in range(2020, 2027):
        L.append(f'| {y} | ' + ' | '.join(str(yc[y][g]) for g in GROUPS) + f' | {sum(yc[y].values())} | {PT["year_total"][str(y)]} |')
    L.append('')
    L.append('## 6. 연구방법 분포 (표 2)\n')
    L.append('| 방법 | 영어 | 한국어 | 중국어 | 계 | 비율 | 논문(영/한/중) |\n|---|---|---|---|---|---|---|')
    mc = defaultdict(Counter)
    for m in inc: mc[m['meth']][m['group']] += 1
    for k in METHS:
        tot = sum(mc[k].values()); L.append(f'| {k} | ' + ' | '.join(str(mc[k][g]) for g in GROUPS) + f' | {tot} | {100*tot/max(1,len(inc)):.1f}% | {"/".join(map(str, PT["table2_method"][k]))} |')
    exp = {g: mc['실험연구'][g] for g in GROUPS}
    L.append('\n실험연구 비중(그림 3): ' + ', '.join(f'{g} {100*exp[g]/max(1,cg[g]):.1f}%' for g in GROUPS) + f' (논문 {PT["fig3_exp_share"]})')
    be = {g: mc['개발연구'][g] + mc['성능평가'][g] for g in GROUPS}
    L.append('구축·평가형 비중(그림 3): ' + ', '.join(f'{g} {100*be[g]/max(1,cg[g]):.1f}%' for g in GROUPS) + f' (논문 {PT["fig3_build_eval_share"]})\n')
    L.append('## 7. 언어기능 분포 (표 10)\n')
    L.append('| 기능 | 영어 | 한국어 | 중국어 | 계 | 논문(영/한/중) |\n|---|---|---|---|---|---|')
    fc = defaultdict(Counter)
    for m in inc: fc[m['func']][m['group']] += 1
    for k in FUNCS:
        L.append(f'| {k} | ' + ' | '.join(str(fc[k][g]) for g in GROUPS) + f' | {sum(fc[k].values())} | {"/".join(map(str, PT["table10_function"][k]))} |')
    L.append('')
    L.append('## 8. 기능비특정 초점 (표 9)\n')
    L.append('| 초점 | 영어 | 한국어 | 중국어 | 계 | 논문 |\n|---|---|---|---|---|---|')
    foc = defaultdict(Counter)
    for m in inc:
        if m['func'] == '기능비특정': foc[m['focus']][m['group']] += 1
    for k in FOCUS:
        L.append(f'| {k} | ' + ' | '.join(str(foc[k][g]) for g in GROUPS) + f' | {sum(foc[k].values())} | {"/".join(map(str, PT["table9_nonspecific_focus"][k]))} |')
    L.append('')
    L.append('## 9. 기능×방법 격자 (표 11·12, 그림 6)\n')
    grid = {g: Counter() for g in GROUPS}
    for m in inc:
        if m['func'] != '기능비특정': grid[m['group']][(m['func'], m['meth'])] += 1
    L.append('| 언어군 | 격자 편수 | 점유 칸 | 점유율(88칸) | 논문 점유 칸 |\n|---|---|---|---|---|')
    for i, g in enumerate(GROUPS):
        L.append(f'| {g} | {sum(grid[g].values())} | {len(grid[g])} | {100*len(grid[g])/88:.1f}% | {PT["table11_occupancy"]["filled_cells"][i]} |')
    zh_le1 = sum(1 for f in FUNCS[:-1] for mth in METHS if grid['중국어'][(f, mth)] <= 1)
    struct = sum(1 for f in FUNCS[:-1] for mth in METHS if grid['중국어'][(f, mth)] == 0 and grid['영어'][(f, mth)] == 0 and grid['한국어'][(f, mth)] == 0)
    L.append(f'\n공백 좌표(중국어 ≤1편): {zh_le1}칸 (논문 79) · 구조공백(세 군 모두 0): {struct}칸 (논문 18)\n')
    L.append('확산 대기 상위(영·한 합 기준, 중국어 ≤1):\n')
    pend = sorted(((grid['영어'][(f, mth)] + grid['한국어'][(f, mth)], f, mth) for f in FUNCS[:-1] for mth in METHS if grid['중국어'][(f, mth)] <= 1), reverse=True)[:10]
    L.append('| 기능 | 방법 | 영어 | 한국어 | 중국어 |\n|---|---|---|---|---|')
    for _, f, mth in pend: L.append(f'| {f} | {mth} | {grid["영어"][(f, mth)]} | {grid["한국어"][(f, mth)]} | {grid["중국어"][(f, mth)]} |')
    L.append('')
    L.append('## 10. 핵심도구 · 신뢰도 · 경계\n')
    L.append('- 도구: ' + ', '.join(f'{k} {v}' for k, v in Counter(m['tool'] for m in inc).most_common()))
    L.append('- 유형: ' + ', '.join(f'{k or "(빈값)"} {v}' for k, v in Counter(m['paper_type'] for m in inc).most_common()))
    L.append('- 신뢰도: ' + ', '.join(f'{k or "(빈값)"} {v}' for k, v in Counter(m['confidence'] for m in merged if m['include']).most_common()))
    L.append(f'- 저자 검수 대상(boundary=Y): 포함 {sum(1 for m in inc if m["boundary"]=="Y")}편, 제외 {sum(1 for m in exc if m["boundary"]=="Y")}편')
    L.append('- 중국어군 포함 목록:')
    for m in sorted([m for m in inc if m['group'] == '중국어'], key=lambda m: (m['year'], m['arti_id'])):
        L.append(f'  - {m["year"]} [{m["func"]}/{m["meth"]}/{m["tool"]}] {(m["title_ko"] or m["title_en"] or "")[:60]}' + (' ★경계' if m['boundary'] == 'Y' else ''))
    open(f'{REPO}/analysis/rejudge_summary_{DATE}.md', 'w', encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L[:40]))
    return grid

AUTHOR_CONFIRMED = 'Y'   # 2026-10-01 저자가 경계 검수 대상 전부를 확인해 확정했다(3번 시트 '저자 확정' 열)


def build_xlsx(merged, with_abstract, public=False):
    """public=True: 공개용. 안내 시트와 작업용 대조 시트를 빼고 시트 번호를 1–6으로 매긴다(make_public.py)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    BOLD = Font(bold=True); HEAD = PatternFill('solid', fgColor='DDEBF7'); ORANGE = PatternFill('solid', fgColor='FCE4D6'); YEL = PatternFill('solid', fgColor='FFF2CC')
    wb = Workbook(); ws0 = wb.active; ws0.title = '0. 안내'
    sheet_no = {'격자': 4, '연도': 5, 'L1L2': 6} if public else {'격자': 5, '연도': 6, 'L1L2': 7}
    _inc = [r for r in merged if r['include'] == 'Y']
    _cg = Counter(r['group'] for r in _inc)
    _d = DATE.split('_')[-1]
    _date = f'{_d[:4]}-{_d[4:6]}-{_d[6:]}' if len(_d) == 8 and _d.isdigit() else _d
    guide = [
        f'KCI 재수집 코퍼스 — 초록 재판정·재코딩 확정본 ({_date})',
        '논문: AI 활용 중국어교육 연구의 현황과 공백: 영어·한국어교육과의 계량서지·네트워크 비교',
        '',
        f'확정 코퍼스 {len(_inc):,}편 — 영어 {_cg["영어"]:,} · 한국어 {_cg["한국어"]:,} · 중국어 {_cg["중국어"]:,} (제외 {len(merged)-len(_inc):,}편)',
        '',
        '1) 자료 성격: KCI Open API로 수집한 1차 수집본 1,644편(2026-09-29 조회) 전편에 대해, 논문 3.1·3.2의 포함·제외 기준과',
        '   저자 결정을 적용해 논문 단위로 초록을 읽고 포함 여부·언어군·학습자맥락·언어기능(주)·연구방법(주)·핵심도구를 다시 코딩한 것이다.',
        '2) 적용한 저자 결정: 오직 [AI + 언어교육]의 융합만 대상으로 한다.',
        '   ① 국어 교과 담론형(AI 시대 교과의 대응 방향만 논의) 제외  ② 대학 교양의 글쓰기·읽기·토론 교육 제외',
        '   ③ AI 디지털교과서(AIDT) 자체를 대상으로 한 연구 제외 — 교육 정책·플랫폼 사업이지 언어교육과 AI의 융합이 아님',
        '   ④ 통번역 수업은 AI를 번역 교육에 적용했으면 포함  ⑤ 문법·NLP 논문은 교육적 적용·시사점이 초록에 있으면 포함',
        '   ⑥ AI 자동채점·자동피드백·화법 평가 도구를 개발·검증한 연구는 대학 교양 맥락이어도 포함(언어 능력을 평가하는 AI 도구이므로)',
        '   교양 제외는 대상 언어 기준이다. 교양 영작문·교양 중국어처럼 외국어 교과로 개설된 수업은 영어교육·중국어교육 연구이므로 유지했다.',
        '   AIDT도 같은 방식으로 가렸다. AIDT가 배경·맥락일 뿐 실제 대상이 AI 도구의 언어 교수·학습 효과인 연구는 유지했다.',
        '   ⑦ 복수언어 비교 연구 제외(2026-10-01): 두 개 이상의 언어를 함께 다루거나 비교한 연구는 제외하고, 대상 언어를 명시하지 않은 연구는',
        '      언어 비특정으로 제외한다. 복수언어 검색 범주로 수집되었더라도 한 언어만 다룬 연구는 그 언어로 분류해 유지했다.',
        '   언어 범주: 모든 논문은 영어·한국어·중국어 세 범주로만 구분한다. 통·번역 연구도 대상 언어쌍에 따라 세 언어 가운데 하나로 분류했고,',
        '      여러 언어를 함께 다룬 복수언어 연구는 제외했다. 포함 논문은 분석 언어군이고, 제외 논문은 판정된 대상 언어다.',
        '      세 언어에 속하지 않거나(제2외국어) 대상 언어가 없는(언어 비특정·복수언어) 제외 논문은 ‘해당 없음’으로 적는다.',
        '3) 코딩 지침: data/rejudge/CODING_GUIDE.md, 교양 판정 data/rejudge/l1/L1_RULE.md, AIDT·평가도구 판정 data/rejudge/r3/R3_RULE.md. 범주 정의는 부록 A와 같다.',
        '4) 시트: 1. 포함코퍼스 / 2. 제외 / 3. 경계검수(저자 확인 대상) / 4. 대조표(작업용) / 5. 격자(기능×방법) / 6. 연도×언어군 / 7. 한국어군 L1·L2',
        '5) 주황색 열은 코딩 값, 노란색 열은 저자 검수 표시. "이전판정" 열은 2026-09-29 규칙 판정본(1,312편)의 값으로 변화 추적용이다.',
        '6) 피인용·참고문헌수는 KCI 2026-09-29 조회값이다.',
        '7) 규칙 판정 1,312편(이전판정 열)은 초록을 읽지 않은 사전 판정이다.',
        '8) 초록·참고문헌은 KCI 원자료이므로 재배포하지 않는다.' + ('' if with_abstract else ' (이 파일은 초록 열을 뺀 판)'),
    ]
    for t in guide: ws0.append([t])
    ws0.column_dimensions['A'].width = 140
    if public: wb.remove(ws0)
    inc = [m for m in merged if m['include'] == 'Y']; exc = [m for m in merged if m['include'] == 'N']
    base_cols = ['순번', 'artiId', '언어 범주', '언어군', '학습자맥락', '언어기능(주)', '연구방법(주)', '핵심도구', '비특정초점', 'AI역할', '논문유형', '신뢰도', '검수대상', '판정메모',
                 '이전판정', '이전언어군', '제목(국문)', '제목(영문)', '저자(소속)', '저자수', '학술지', '발행기관', '연도', 'KCI분류', '주제어(국문)', '주제어(영문)']
    if with_abstract: base_cols += ['초록(국문)', '초록(영문)']
    base_cols += ['피인용(KCI)', '참고문헌수', 'DOI', 'KCI링크']
    def row_of(i, m):
        r = [i, m['arti_id'], m.get('lang3', m['sheet']), m['group'], m['learner'], m['func'], m['meth'], m['tool'], m['focus'], m['ai_role'], m['paper_type'], m['confidence'], m['boundary'], m['note'],
             m['prev_include'], m['prev_group'], m['title_ko'], m['title_en'], m['authors'], m['n_authors'], m['journal'], m['publisher'], m['year'], m['kci_field'], m['kw_ko'], m['kw_en']]
        if with_abstract: r += [m['abstract_ko'], m['abstract_en']]
        r += [m['cited'], m['n_refs'], m['doi'], m['permalink']]
        return r
    ws1 = wb.create_sheet(f'1. 포함코퍼스_{len(inc)}'); ws1.append(base_cols)
    for c in range(1, len(base_cols) + 1):
        ws1.cell(1, c).font = BOLD; ws1.cell(1, c).fill = ORANGE if 4 <= c <= 11 else (YEL if 12 <= c <= 14 else HEAD)
    for i, m in enumerate(sorted(inc, key=lambda m: (GROUPS.index(m['group']), m['year'], m['arti_id'])), 1): ws1.append(row_of(i, m))
    ws1.freeze_panes = 'E2'; ws1.auto_filter.ref = ws1.dimensions
    exc_cols = ['순번', 'artiId', '언어 범주', '제외사유', '언어군(판단)', '신뢰도', '검수대상', '판정메모', '이전판정', '이전사유', '제목(국문)', '제목(영문)', '학술지', '연도', 'KCI분류', '주제어(국문)'] + (['초록(국문)'] if with_abstract else []) + ['KCI링크']
    ws2 = wb.create_sheet(f'2. 제외_{len(exc)}'); ws2.append(exc_cols)
    for c in range(1, len(exc_cols) + 1): ws2.cell(1, c).font = BOLD; ws2.cell(1, c).fill = HEAD
    for i, m in enumerate(sorted(exc, key=lambda m: (m['reason'], m.get('lang3', m['sheet']), m['year'])), 1):
        ws2.append([i, m['arti_id'], m.get('lang3', m['sheet']), m['reason'], m['group'], m['confidence'], m['boundary'], m['note'], m['prev_include'], m['prev_reason'],
                    m['title_ko'], m['title_en'], m['journal'], m['year'], m['kci_field'], m['kw_ko']] + ([m['abstract_ko']] if with_abstract else []) + [m['permalink']])
    ws2.freeze_panes = 'E2'; ws2.auto_filter.ref = ws2.dimensions
    bd = [m for m in merged if m['boundary'] == 'Y' or (m['prev_include'] != m['include'] and m['include'])]
    ws3 = wb.create_sheet(f'3. 경계검수_{len(bd)}')
    cols3 = ['구분', 'artiId', '언어 범주', '판정', '제외사유', '언어군', '학습자맥락', '언어기능(주)', '연구방법(주)', '신뢰도', '판정메모', '이전판정', '이전언어군/사유', '제목(국문)', '학술지', '연도', '주제어(국문)'] + (['초록(국문)'] if with_abstract else []) + ['저자 확정(기입)', 'KCI링크']
    ws3.append(cols3)
    for c in range(1, len(cols3) + 1): ws3.cell(1, c).font = BOLD; ws3.cell(1, c).fill = YEL
    for m in sorted(bd, key=lambda m: (m['include'], m['group'], m['year'])):
        kind = ('경계 표시' if m['boundary'] == 'Y' else '') + (' / 규칙과 상이' if m['prev_include'] != m['include'] else '')
        ws3.append([kind.strip(' /'), m['arti_id'], m.get('lang3', m['sheet']), m['include'], m['reason'], m['group'], m['learner'], m['func'], m['meth'], m['confidence'], m['note'],
                    m['prev_include'], m['prev_group'] or m['prev_reason'], m['title_ko'] or m['title_en'], m['journal'], m['year'], m['kw_ko']] + ([m['abstract_ko']] if with_abstract else []) + [AUTHOR_CONFIRMED, m['permalink']])
    ws3.freeze_panes = 'E2'; ws3.auto_filter.ref = ws3.dimensions
    # 4. 대조표(작업용 대조값과 비교. 공개본에는 넣지 않는다)
    cg = Counter(m['group'] for m in inc)
    if not public and os.path.exists(f'{REPO}/analysis/paper_targets.json'):
      PT = json.load(open(f'{REPO}/analysis/paper_targets.json', encoding='utf-8'))
      ws4 = wb.create_sheet('4. 대조표')
      ws4.append(['(1) 언어군 편수', '논문', '재판정', '차이']); ws4.cell(1, 1).font = BOLD
      for g in GROUPS: ws4.append([g, PT['groups'][g], cg[g], cg[g] - PT['groups'][g]])
      ws4.append(['계', sum(PT['groups'].values()), len(inc), len(inc) - sum(PT['groups'].values())]); ws4.append([])
      ws4.append(['(2) 연구방법', '논문 영', '논문 한', '논문 중', '재판정 영', '재판정 한', '재판정 중']); ws4.cell(ws4.max_row, 1).font = BOLD
      mc = defaultdict(Counter)
      for m in inc: mc[m['meth']][m['group']] += 1
      for k in METHS: ws4.append([k] + PT['table2_method'][k] + [mc[k][g] for g in GROUPS])
      ws4.append([])
      ws4.append(['(3) 언어기능', '논문 영', '논문 한', '논문 중', '재판정 영', '재판정 한', '재판정 중']); ws4.cell(ws4.max_row, 1).font = BOLD
      fc = defaultdict(Counter)
      for m in inc: fc[m['func']][m['group']] += 1
      for k in FUNCS: ws4.append([k] + PT['table10_function'][k] + [fc[k][g] for g in GROUPS])
      ws4.append([])
      ws4.append(['(4) 제외 사유', '논문', '재판정']); ws4.cell(ws4.max_row, 1).font = BOLD
      er = Counter(m['reason'] for m in exc)
      for k in REASONS: ws4.append([k, PT['footnote2_exclusions'].get(k, ''), er[k]])
    # 5. 격자
    ws5 = wb.create_sheet(f"{sheet_no['격자']}. 격자")
    for g in GROUPS:
        grid = Counter((m['func'], m['meth']) for m in inc if m['group'] == g and m['func'] != '기능비특정')
        ws5.append([f'{g} — 기능×방법 (기능비특정 제외, {sum(grid.values())}편)']); ws5.cell(ws5.max_row, 1).font = BOLD
        ws5.append(['기능＼방법'] + METHS + ['계'])
        for f in FUNCS[:-1]: ws5.append([f] + [grid[(f, mth)] for mth in METHS] + [sum(grid[(f, mth)] for mth in METHS)])
        ws5.append(['계'] + [sum(grid[(f, mth)] for f in FUNCS[:-1]) for mth in METHS] + [sum(grid.values())]); ws5.append([])
    # 6. 연도
    ws6 = wb.create_sheet(f"{sheet_no['연도']}. 연도×언어군"); ws6.append(['연도'] + GROUPS + ['계'])
    yc = defaultdict(Counter)
    for m in inc: yc[m['year']][m['group']] += 1
    for y in range(2020, 2027): ws6.append([y] + [yc[y][g] for g in GROUPS] + [sum(yc[y].values())])
    ws6.append(['계'] + [cg[g] for g in GROUPS] + [len(inc)])
    # 7. 한국어군 L1/L2
    ws7 = wb.create_sheet(f"{sheet_no['L1L2']}. 한국어군_L1L2"); ws7.append(['학습자맥락', '편수'] + FUNCS)
    for Lv in ('L1', 'L2', '미명시'):
        ko = [m for m in inc if m['group'] == '한국어' and m['learner'] == Lv]; cf = Counter(m['func'] for m in ko)
        ws7.append([Lv, len(ko)] + [cf[f] for f in FUNCS])
    for ws in [w for w in wb.worksheets if w.title != '0. 안내']:
        for c in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(c)].width = 14
    for ws, wide in ((ws1, {17: 50, 18: 40, 19: 30, 21: 22, 25: 30, 26: 30, 14: 36}), (ws2, {11: 50, 12: 40, 8: 36, 16: 30}), (ws3, {14: 50, 11: 36, 17: 30})):
        for c, w in wide.items(): ws.column_dimensions[get_column_letter(c)].width = w
    if with_abstract:
        for ws, cs in ((ws1, (27, 28)), (ws2, (17,)), (ws3, (18,))):
            for c in cs: ws.column_dimensions[get_column_letter(c)].width = 60
    if public: os.makedirs(f'{REPO}/release/data', exist_ok=True)
    out = f'{REPO}/release/data/KCI_코퍼스확정.xlsx' if public else f'{REPO}/data/KCI_코퍼스확정_{DATE}' + ('_초록포함' if with_abstract else '') + '.xlsx'
    wb.save(out); print('saved', out)

if __name__ == '__main__':
    merged, problems, missing = main()
    if not missing or '--partial' in sys.argv:
        summarize(merged, problems, missing)
        if '--xlsx' in sys.argv:
            build_xlsx([m for m in merged if m['include']], False)
            build_xlsx([m for m in merged if m['include']], True)
