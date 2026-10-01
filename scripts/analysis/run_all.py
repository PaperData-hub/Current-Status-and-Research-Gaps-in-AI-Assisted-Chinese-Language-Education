# -*- coding: utf-8 -*-
"""run_all.py — 공개 자료만으로 원고의 모든 분석 결과(analysis/)와 부록 C를 다시 만들고, 배포한 파일과 같은지 확인한다.

사용: python scripts/analysis/run_all.py
  1) analysis/와 부록C_판정재현성_불일치.md의 현재 내용을 기억한다.
  2) 분석 스크립트를 차례로 실행해 같은 파일을 다시 쓴다.
  3) 다시 쓴 파일이 배포본과 바이트 단위로 같은지 비교해 결과를 보고한다.
난수를 쓰는 분석(희박화, 재추출)은 시드가 스크립트에 고정되어 있어 실행할 때마다 같은 값이 나온다.
"""
import hashlib, io, os, subprocess, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATE = '1161_20261001'
STEPS = [
    ['descriptives.py'],
    ['rarefaction_final.py'],
    ['scale_checks.py'],
    ['keyword_diffusion.py'],
    ['tables_8to11.py'],
    ['network_scale.py'],
    ['references_school.py'],
    ['journal_field.py'],
    ['kappa_compute.py', '--coded', f'data/kappa/ai2/ai2_merged_{DATE}.json', '--name1', '독립 재판정'],
    ['appendix_c.py'],
]


def snapshot():
    files = [os.path.join('analysis', f) for f in sorted(os.listdir(os.path.join(REPO, 'analysis')))] + ['부록C_판정재현성_불일치.md']
    return {f: hashlib.sha256(open(os.path.join(REPO, f), 'rb').read()).hexdigest() for f in files if os.path.isfile(os.path.join(REPO, f))}


before = snapshot()
env = dict(os.environ, PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8')
for step in STEPS:
    cmd = [sys.executable, os.path.join(REPO, 'scripts', 'analysis', step[0])] + step[1:] + ['--date', DATE]
    r = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True)
    print(('ok  ' if r.returncode == 0 else 'ERR ') + ' '.join(step))
    if r.returncode:
        print(r.stderr.decode('utf-8', 'replace')); sys.exit(1)
after = snapshot()
changed = [f for f in after if before.get(f) != after[f]]
new = [f for f in after if f not in before]
print()
if not changed:
    print(f'배포본과 같음: {len(after)}개 파일 모두 바이트 단위로 일치한다.')
else:
    print(f'배포본과 다른 파일 {len(changed)}개:'); [print('  ', f, '(새 파일)' if f in new else '') for f in changed]
    sys.exit(2)
