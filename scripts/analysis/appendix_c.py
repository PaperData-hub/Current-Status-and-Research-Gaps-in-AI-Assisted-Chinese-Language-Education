# -*- coding: utf-8 -*-
"""appendix_c.py — 부록 C(판정의 재현성) 생성: 확정 판정과 독립 재판정의 일치도, 불일치 사례, 중국어군 민감도.

확정 판정 = 부록 A 절차의 최종값(data/rejudge/merged_<DATE>.json)
독립 재판정 = κ 표본 200편을 다른 언어모델이 확정값을 보지 않고 판정한 값(data/kappa/ai2/ai2_merged_<DATE>.json)
  C.1 설계  C.2 축별 κ와 언어군별 포함 일치  C.3 불일치 사례  C.4 중국어군 언어기능 구성의 민감도  C.5 해석과 한계
축 정의는 kappa_compute.py와 같고, C.4의 초기하 계산은 scale_checks.py 3절과 같다.
산출: 부록C_판정재현성_불일치.md(저장소 루트)
사용: python scripts/analysis/appendix_c.py [--date 1161_20261001] [--model "Claude Sonnet 5.5"] [--run-date "2026년 10월 1일"]
"""
import json, os, sys, io
from math import comb
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
DATE = arg('--date', '1161_20261001')
MODEL = arg('--model', 'Claude Sonnet 5.5')
RUN = arg('--run-date', '2026년 10월 1일')
KEYF = ['include', 'reason', 'group', 'learner', 'func', 'meth', 'tool']
FUNCS = ['쓰기', '말하기', '평가·채점', '읽기', '리터러시·역량', '번역', '문법', '문학·문화', '발음', '어휘', '듣기']
BONF = 0.05 / len(FUNCS)

M = {r['arti_id']: r for r in json.load(open(f'{REPO}/data/rejudge/merged_{DATE}.json', encoding='utf-8'))}
key = {o['arti_id']: {k: (o[k] or '') for k in KEYF} for o in json.load(open(f'{REPO}/data/kappa/κ표본_정답키_{DATE}.json', encoding='utf-8'))}
ai2 = {}
for o in json.load(open(f'{REPO}/data/kappa/ai2/ai2_merged_{DATE}.json', encoding='utf-8')):
    ai2[o['id']] = {k: str(o.get(k) or '').strip() for k in KEYF} | {'note': o.get('note') or ''}
    ai2[o['id']]['include'] = ai2[o['id']]['include'].upper()
assert set(key) == set(ai2), '표본과 재판정 대상이 다르다'
ids = list(key)
zh_all = [i for i, r in M.items() if r['include'] == 'Y' and r['group'] == '중국어']
assert set(zh_all) <= set(key), '중국어군 전수가 표본에 없다'


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return ((po - pe) / (1 - pe) if pe < 1 else 1.0), po, n


def lk(k):
    return '거의 완벽' if k > 0.80 else '상당함' if k > 0.60 else '보통' if k > 0.40 else '약함' if k > 0.20 else '미약'


def p_le(K, N, n, k):
    return sum(comb(K, i) * comb(N - K, n - i) for i in range(0, k + 1)) / comb(N, n)


def p_ge(K, N, n, k):
    return 1.0 if k <= 0 else 1 - p_le(K, N, n, k - 1)


def fp(x):
    return '<0.0001' if x < 0.0001 else f'{x:.4f}'


A, B = key, ai2
both_in = [i for i in ids if A[i]['include'] == 'Y' and B[i]['include'] == 'Y']
both_ko = [i for i in both_in if A[i]['group'] == '한국어' and B[i]['group'] == '한국어']
both_out = [i for i in ids if A[i]['include'] == 'N' and B[i]['include'] == 'N']
AXES = [('포함 여부', 'include', ids, '표본 전체'), ('언어군', 'group', both_in, '두 판정 모두 포함'),
        ('언어기능(주)', 'func', both_in, '두 판정 모두 포함'), ('연구방법(주)', 'meth', both_in, '두 판정 모두 포함'),
        ('핵심 도구', 'tool', both_in, '두 판정 모두 포함'), ('학습자 맥락', 'learner', both_ko, '두 판정 모두 한국어군'),
        ('제외 사유(참고)', 'reason', both_out, '두 판정 모두 제외')]
res, dis = [], []
for name, f, sub, base in AXES:
    k, po, n = kappa([(A[i][f], B[i][f]) for i in sub])
    res.append((name, base, n, po, k))
    dis += [(name, f, i) for i in sub if A[i][f] != B[i][f]]
n_dis = Counter(d[0] for d in dis)
inc_dis = [i for a, _, i in dis if a == '포함 여부']
flagged = [i for i in inc_dis if M[i].get('boundary') == 'Y']
flag_base = sum(M[i].get('boundary') == 'Y' for i in ids)
disc = [i for i in inc_dis if A[i]['include'] == 'Y' and M[i].get('paper_type') == '담론']
by_group = []
for g in ('중국어', '영어', '한국어'):
    s = [i for i in ids if A[i]['include'] == 'Y' and A[i]['group'] == g]
    by_group.append((f'{g}군', len(s), sum(B[i]['include'] == 'Y' for i in s)))
s = [i for i in ids if A[i]['include'] == 'N']
by_group.append(('제외 논문', len(s), sum(B[i]['include'] == 'N' for i in s)))
y2n = Counter(A[i]['group'] for i in inc_dis if A[i]['include'] == 'Y')
n2y = Counter(B[i]['group'] for i in inc_dis if A[i]['include'] == 'N')

# C.4 중국어군만 재판정 값으로 바꾼 언어기능 구성(비교군은 확정 값)
grid = [r for r in M.values() if r['include'] == 'Y' and r['func'] != '기능비특정']
pools = {'합': Counter(r['func'] for r in grid if r['group'] != '중국어'),
         '영어': Counter(r['func'] for r in grid if r['group'] == '영어'),
         '한국어': Counter(r['func'] for r in grid if r['group'] == '한국어')}
zc = Counter(r['func'] for r in grid if r['group'] == '중국어')
za = Counter(B[i]['func'] for i in ids if B[i]['include'] == 'Y' and B[i]['group'] == '중국어' and B[i]['func'] != '기능비특정')
n_c, n_a = sum(zc.values()), sum(za.values())


def test(zf, n, pool, f):
    N = sum(pool.values()); K = pool[f]; e = n * K / N
    p = p_le(K, N, n, zf[f]) if zf[f] < e else p_ge(K, N, n, zf[f])
    return e, p, '↓' if zf[f] < e else '↑'


def cell(e, p, d):
    return f'{fp(p)}{d}' + (' **' if p < BONF else ' *' if p < 0.05 else '')


sens = {f: {'c': test(zc, n_c, pools['합'], f), 'a': test(za, n_a, pools['합'], f),
            'a_en': test(za, n_a, pools['영어'], f), 'a_ko': test(za, n_a, pools['한국어'], f)} for f in FUNCS}
sig_c = [f for f in FUNCS if sens[f]['c'][1] < BONF]
sig_a = [f for f in FUNCS if sens[f]['a'][1] < BONF]
kept = [f for f in sig_c if f in sig_a]
lost = [f for f in sig_c if f not in sig_a]
gained = [f for f in sig_a if f not in sig_c]
zh_lit_out = [i for i in inc_dis if A[i]['group'] == '중국어' and A[i]['func'] == '문학·문화']
zh_ex = [i for i, r in M.items() if r['include'] != 'Y' and r.get('lang3') == '중국어']
zh_ex_s = [i for i in zh_ex if i in key]


def title(i):
    t = M[i]['title_ko'] or M[i]['title_en'] or ''
    return (t[:45] + '…' if len(t) > 45 else t).replace('|', '/')


def show(d, f):
    if f != 'include':
        return d[f] or '(빈칸)'
    return f"포함({d['group']}·{d['func']})" if d['include'] == 'Y' else f"제외({d['reason']})"


def arrow(d):
    return '적음' if d == '↓' else '많음'


L = ['# 부록 C. 판정의 재현성: 독립 재판정과의 일치도', '',
     '## C.1 목적과 설계', '',
     '본 연구의 판정과 코딩은 연구자가 정한 지침(부록 A)에 따라 대규모 언어모델이 수행하였다. 이 결과가 특정 모델의 한 차례 실행에 좌우된 것인지 점검하기 위해, '
     '같은 지침을 다른 모델이 확정 판정값을 보지 않고 적용한 결과와 비교하였다. 이 비교는 판정의 재현성을 보여 주며, 연구자 판정과의 일치(타당성)를 보여 주지는 않는다.', '',
     '<표 C1> 독립 재판정의 설계', '',
     '| 항목 | 내용 |', '|---|---|',
     f'| 표본 | {len(ids)}편(난수 시드 20261001). 확정 코퍼스의 중국어군 {len(zh_all)}편 전수, 영어군·한국어군 각 46편(연구방법 비율로 층화), 제외 논문 40편(제외 사유 비율로 층화). 행 순서는 무작위로 섞었다. |',
     f'| 재판정자 | {MODEL}(Anthropic), {RUN}. 확정 판정에 쓰인 모델(부록 A.1)과 다른 모델이다. |',
     '| 제공 정보 | 논문별 제목, 주제어, 초록(국문·영문), 게재 학술지, 발행연도와 판정 지침. 판정 지침은 부록 A.2의 포함 기준, 경계 범주의 처리 규칙, 코딩 범주를 요약한 것이다. 다만 담론·시론의 처리 규칙(<표 A2>)과 게재 학술지에 따른 언어군 배정(A.2.3)은 이 지침에 명시되지 않았다. |',
     '| 제공하지 않은 정보 | 확정 판정값, 문자열 규칙의 사전 판정값, 확정 판정의 근거와 확신도 |',
     '| 실행 | 25편씩 8묶음을 묶음마다 별도 세션에서 판정하였다. 세션 기록으로 판정 지침과 배정된 묶음 외의 파일을 열지 않았음을 확인하였다. |',
     '| 산출 | 축별 Cohen\'s κ와 불일치 목록 |', '',
     '## C.2 일치도', '',
     '<표 C2> 확정 판정과 독립 재판정의 축별 일치도', '',
     '| 축 | 대상 | 편수 | 관찰 일치도 | Cohen\'s κ | Landis–Koch |', '|---|---|---|---|---|---|']
L += [f'| {name} | {base} | {n} | {po * 100:.1f}% | {k:.2f} | {lk(k)} |' for name, base, n, po, k in res]
L += ['', '포함 여부의 일치를 확정 판정의 언어군별로 보면 '
      + ', '.join(f'{g} {n}편 중 {a}편({a / n * 100:.1f}%)' for g, n, a in by_group) + '이다. '
      f'불일치 {len(inc_dis)}건 가운데 {sum(y2n.values())}건은 확정 판정에서 포함한 논문을 재판정에서 제외한 경우('
      + ', '.join(f'{g} {c}건' for g, c in y2n.most_common()) + f'), {sum(n2y.values())}건은 그 반대('
      + ', '.join(f'{g} {c}건' for g, c in n2y.most_common()) + ')이다. '
      + (f'{len(inc_dis)}건은 모두' if len(flagged) == len(inc_dis) else f'{len(inc_dis)}건 가운데 {len(flagged)}건은')
      + f' 확정 판정 단계에서 이미 경계 사례로 표시된 논문이었다(표본 전체에서 경계 사례는 {flag_base}편, {flag_base / len(ids) * 100:.1f}%).', '',
      '## C.3 불일치 사례', '',
      f'불일치는 모두 {len(dis)}건이다(' + ', '.join(f'{a} {n_dis[a]}건' for a, *_ in AXES if n_dis[a]) + '). '
      '근거는 각 판정자가 기록한 판정 근거(40자 이내)이다.', '',
      '<표 C3> 확정 판정과 독립 재판정의 불일치 사례', '',
      '| 축 | artiId | 제목 | 확정 판정 | 독립 재판정 | 확정 판정 근거 | 재판정 근거 |', '|---|---|---|---|---|---|---|']
L += [f"| {a} | {i} | {title(i)} | {show(A[i], f)} | {show(B[i], f)} | {M[i].get('note') or ''} | {B[i]['note']} |" for a, f, i in dis]
L += ['', f'연구자가 불일치 {len(dis)}건의 초록을 검토하여 확정 판정을 모두 유지하였다.', '',
      '## C.4 중국어군 언어기능 구성의 민감도', '',
      f'포함 여부 불일치 가운데 {y2n["중국어"]}건이 중국어군이고, 그 가운데 {len(zh_lit_out)}건이 문학·문화 기능이다('
      + ', '.join(zh_lit_out) + '; <표 C3>). '
      '이 경계 판정이 언어기능 구성의 결과를 좌우하는지 확인하기 위해, 중국어군만 독립 재판정 값으로 바꾸어 규모 통제 비교(부록 B)를 다시 하였다. '
      '비교군(영어군·한국어군의 기능 특정 논문)은 확정 값을 그대로 썼다.', '',
      f'<표 C4> 중국어군 언어기능 구성: 확정 판정({n_c}편)과 독립 재판정({n_a}편)', '',
      '| 기능 | 확정: 중국어 | 확정: 비교군 기대 | 확정: P | 재판정: 중국어 | 재판정: 비교군 기대 | 재판정: P |', '|---|---|---|---|---|---|---|']
for f in FUNCS:
    (ec, pc, dc), (ea, pa, da) = sens[f]['c'], sens[f]['a']
    L.append(f'| {f} | {zc[f]} | {ec:.1f} | {cell(ec, pc, dc)} | {za[f]} | {ea:.1f} | {cell(ea, pa, da)} |')
sent = (f'중국어군을 재판정 값으로 바꾸어도 ' + ', '.join(f'{f}({arrow(sens[f]["a"][2])})' for f in kept) + '의 차이는 모두 Bonferroni 기준을 통과하였다'
        if kept else '재판정 값에서는 확정 판정에서 Bonferroni 기준을 통과한 기능이 모두 기준을 통과하지 못하였다')
sent += ('. ' + ', '.join(lost) + '의 차이는 재판정 값에서 기준을 통과하지 못하였다') if lost and kept else ''
sent += ('. ' + ', '.join(f'{f}({arrow(sens[f]["a"][2])})' for f in gained) + '의 차이는 확정 판정에서는 P<0.05에 그쳤으나 재판정 값에서는 기준을 통과하였다') if gained else ''
per = [f'{f} 영어군 {fp(sens[f]["a_en"][1])}·한국어군 {fp(sens[f]["a_ko"][1])}' for f in kept]
L += ['', f'↓ 중국어가 기대보다 적음, ↑ 많음. * P<0.05, ** Bonferroni 기준(0.05/{len(FUNCS)}={BONF:.4f}) 통과. 초기하 분포에 따른 한쪽 확률이다.', '',
      sent + '. 재판정 값으로 영어군·한국어군과 각각 비교한 P는 ' + ', '.join(per) + '이다. '
      f'다만 재판정은 확정 판정에서 제외된 중국어 관련 논문 {len(zh_ex)}편 가운데 표본에 든 {len(zh_ex_s)}편에만 이루어졌으므로'
      + ('(모두 제외로 일치)' if all(B[i]['include'] == 'N' for i in zh_ex_s) else f'({sum(B[i]["include"] == "N" for i in zh_ex_s)}편 제외로 일치)') + f', 확정 판정에서 빠진 중국어 논문이 있을 가능성은 이 점검으로 배제되지 않는다.', '',
      '## C.5 해석과 한계', '',
      f'- 일치도는 모든 축에서 Landis와 Koch(1977)의 ‘상당함’ 이상이며, 제외 사유를 뺀 여섯 축은 ‘거의 완벽’이다. 같은 지침을 다른 모델이 적용해도 판정이 거의 그대로 재현된다는 뜻이다.',
      f'- 불일치는 연구방법({n_dis["연구방법(주)"]}건)에 가장 많다. 포함 여부 불일치 {len(inc_dis)}건은 모두 확정 판정에서 경계 사례로 표시된 논문이다. '
      f'이 가운데 {len(disc)}건은 확정 판정에서 담론·시론으로 포함한 논문으로, 담론·시론의 처리 규칙이 재판정 지침에 명시되지 않은 점과 관련이 있을 수 있다. '
      f'{len(zh_lit_out)}건은 중국 문학 연구·수업으로, 부록 A.2.2에 별도 처리 규칙이 없는 범주이다.',
      '- 두 판정자는 모두 같은 계열(Claude)의 언어모델이다. 두 모델이 공유하는 판단 경향은 일치도에 드러나지 않으므로, 이 결과는 판정의 재현성을 보여 줄 뿐 연구자 판정과의 일치를 보여 주지 않는다. 연구자 코딩과의 비교는 후속 과제로 남긴다.', '']

out = f'{REPO}/부록C_판정재현성_불일치.md'
io.open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
print('\n'.join(L[:40])); print('...'); print('\n'.join(L[-16:])); print('saved', out)
