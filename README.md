# AI 활용 중국어교육 연구의 현황과 공백: 공개 자료

논문 「AI 활용 중국어교육 연구의 현황과 공백: 영어·한국어교육과의 계량서지·네트워크 비교」의 판정 결과, 분석 스크립트, 결과 파일, 논문별 집계를 담은 저장소이다. 논문의 부록 A·B·C도 함께 둔다.

**English summary.** Data and code for *Current Status and Research Gaps in AI-Assisted Chinese Language Education: A Bibliometric and Network Comparison with English and Korean Language Education*. The corpus consists of 1,161 articles indexed in the Korea Citation Index (KCI) from 2020 to June 2026 (English 709, Korean 384, Chinese 68), selected from 1,644 candidates. This repository contains the coding results, coding guidelines, analysis scripts, result files, and per-article aggregates. Every table and number in the paper can be regenerated from the files here with `python scripts/analysis/run_all.py` (Python 3.9+, standard library only). Abstracts and reference lists retrieved from KCI are not redistributed; the articles can be looked up in KCI by their identifiers (artiId).

## 재현: 공개 자료만으로 원고의 모든 수치를 다시 만든다

Python 3.9 이상이 필요하다. 표준 라이브러리만 쓰므로 따로 설치할 패키지는 없다. 저장소 최상위 폴더에서 다음을 실행한다.

```
python scripts/analysis/run_all.py
```

`run_all.py`는 아래 분석 스크립트를 차례로 실행해 `analysis/`의 결과 파일과 `부록C_판정재현성_불일치.md`를 다시 쓴다. 다시 쓴 파일이 배포한 파일과 바이트 단위로 같으면 "배포본과 같음"을 출력한다. 난수를 쓰는 분석(희박화, 재추출)은 시드가 스크립트에 고정되어 있어 몇 번을 실행해도 같은 값이 나온다. 스크립트를 하나씩 실행해도 된다(`python scripts/analysis/<이름>.py`).

| 스크립트 | 결과 파일(`analysis/`) | 원고 |
|---|---|---|
| `descriptives.py` | `descriptives_1161_20261001.md`, `.json` | 3.1의 편수, <표 1>~<표 4>, <그림 1>~<그림 3>, 4.1의 연도별 편수와 핵심 도구, 4.2의 시기별 비중, 3.2 각주의 한국어군 학습자 맥락, 부록 B.4의 주제어 표기 수 |
| `rarefaction_final.py` | `rarefaction_1161_20261001.md`, `.json` | <표 5>, 4.3의 희박화와 기능 비특정 제외율 민감도, 4.2 각주의 실험연구·구축·평가형 초기하 확률 |
| `scale_checks.py` | `scale_checks_1161_20261001.md`, `.json` | 4.3의 공백 유형과 임계값 민감도, <표 6>과 확산대기 좌표의 기대값, 4.2 각주의 연구방법별 기대값, 4.3 각주의 언어기능별 기대값 |
| `keyword_diffusion.py` | `keyword_diffusion_1161_20261001.md`, `.json` | 4.4.1의 공유 키워드 수와 시차 중앙값, <표 7>·<그림 5>, 규모를 맞춘 최초 출현 연도 |
| `tables_8to11.py` | `tables_8to11_1161_20261001.md`, `.json` | <표 8>(위 세 행), <표 9>~<표 11>, 4.4.3의 총 피인용 수 |
| `network_scale.py` | `network_scale_1161_20261001.md`, `.json` | <표 8>의 아래 두 행, 4.4.2의 68편 추출 범위와 비율 |
| `references_school.py` | `references_school_1161_20261001.md` | <표 12>와 4.4.3 각주, 5.2의 학교급 편수와 각주 |
| `journal_field.py` | `journal_field_1161_20261001.md` | 4.4.3 각주의 게재 학술지 분야, 5.2의 학문 공동체 |
| `kappa_compute.py` | `kappa_1161_20261001.md`, `kappa_불일치_1161_20261001.md` | 3.3의 Cohen's κ, 부록 C.3의 불일치 목록 |
| `appendix_c.py` | `부록C_판정재현성_불일치.md`(최상위 폴더) | 부록 C, 4.3 각주의 독립 재판정 민감도 |

그림의 값은 결과 파일에 있다. <그림 1>~<그림 3>은 `descriptives`, <그림 4>는 엑셀 4번 시트(격자), <그림 5>는 `keyword_diffusion`의 <표 7>, <그림 6>은 `tables_8to11`의 <표 8>과 `network_scale`에 있다.

## 구성

| 경로 | 내용 |
|---|---|
| `부록A_판정지침_판정결과.md` | 부록 A. 판정 지침과 판정 결과 |
| `부록B_처리흐름_변수정의.md` | 부록 B. 처리 흐름, 변수 정의, 지표 산출식, 핵심 개념 정규화표 |
| `부록C_판정재현성_불일치.md` | 부록 C. 판정의 재현성(독립 재판정과의 일치도, 불일치 사례). `appendix_c.py`가 만든다 |
| `data/KCI_코퍼스확정.xlsx` | 논문별 판정 결과와 서지 정보(초록 열 없음). 시트: 1 포함 코퍼스 1,161편, 2 제외 483편과 제외 사유, 3 경계 검수 438편(판정자가 경계로 표시했거나 사전 규칙 판정과 결과가 달라진 논문, 마지막 열에 연구자의 확정 표시), 4 언어기능×연구방법 격자, 5 연도×언어군, 6 한국어군 학습자 맥락(L1·L2) |
| `data/rejudge/merged_1161_20261001.json` | 위 엑셀과 같은 판정 결과의 JSON(후보 1,644편, `include`가 `Y`인 1,161편이 분석 코퍼스). 분석 스크립트의 입력이다 |
| `data/rejudge/CODING_GUIDE.md` | 판정·코딩 지침(판정자에게 준 그대로이며 투고번호만 지웠다) |
| `data/rejudge/l1/L1_RULE.md`, `data/rejudge/r3/R3_RULE.md` | 경계 범주의 처리 규칙(부록 A의 2·3차 판정) |
| `data/rejudge/out/`, `data/rejudge/l1/out/`, `data/rejudge/r3/out/` | 언어모델의 판정 출력 원본(1차 28묶음, 2·3차 재판정) |
| `data/kappa/` | 일치도 표본 200편의 확정 판정값(`κ표본_정답키_1161_20261001.json`), 독립 재판정 지침(`ai2/AI2_GUIDE.md`)과 출력(`ai2/out/`, 병합본 `ai2/ai2_merged_1161_20261001.json`) |
| `analysis/keyword_concepts.json` | 20개 핵심 개념 정규화표(부록 B의 <표 B3>) |
| `analysis/ref_aggregate_1161_20261001.csv` | 논문별 참고문헌 분류 집계: 참고문헌 수, 국내(한글)·중문(한자)·그 밖 국제 문헌 수, 학술지명이 있는 문헌 수, 교육·언어학·문학·기타 분야 문헌 수 |
| `analysis/school_level_1161_20261001.csv` | 논문별 학교급 표지(제목·초록에 초·중등 또는 대학 맥락이 드러나는지) |
| `analysis/` 나머지 | 분석 결과 파일(위 표) |
| `scripts/analysis/` | 공개 자료로 실행하는 분석 스크립트(위 표) |
| `scripts/rejudge/`, `scripts/*.js`, `scripts/kci_engine/` | 수집·판정 단계의 스크립트. 처리 절차를 기록하기 위해 공개하며, 실행하려면 원자료가 필요하다(아래) |
| `.env.example` | KCI Open API 인증키 설정 예시. 수집 스크립트를 실행할 때만 필요하다 |

## 수집·판정 단계(원자료가 필요한 부분)

다음 단계는 KCI Open API 인증키(`.env.example`을 `.env`로 복사해 넣는다)와, 재배포하지 않는 원자료(초록·참고문헌이 든 상세 조회 응답, 판정 입력 묶음)가 있어야 실행된다. 공개 결과는 이 단계의 산출물이며, 원고의 수치는 모두 위의 분석 단계로 다시 만들 수 있다.

| 순서 | 명령 | 내용 |
|---|---|---|
| 1 | `node scripts/import_full.js` | 1차 수집 후보 목록(1,644편, `input/KCI_corpus_정리.xlsx`)을 `data/details_full.json`으로 가져온다 |
| 2 | `node scripts/harvest_supp.js` | 보충 검색(부록 B.1, 재현율 점검용) |
| 3 | `node scripts/build_corpus_full.js` | 상세 조회 응답(캐시 `data/cache`)으로 서지·초록·참고문헌을 보강해 `data/corpus_full_merged.json`을 만든다 |
| 4 | `python scripts/rejudge/merge_rejudge.py --date 20260930` | 1차 판정 출력(`data/rejudge/out/`)을 병합·검증한다 |
| 5 | `python scripts/rejudge/apply_l1.py` | 2차 판정(대학 교양 교육 규칙) 반영 |
| 6 | `python scripts/rejudge/apply_r3.py --date 1166_20260930` | 3차 판정(AI 디지털교과서·평가 도구 규칙) 반영 |
| 7 | `python scripts/rejudge/apply_r4.py --date 1161_20261001` | 4차 판정(언어 범주 셋, 복수언어 연구 제외) 반영 |
| 8 | `python scripts/rejudge/school_level.py`, `perl scripts/rejudge/ref_aggregate.pl` | 공개용 논문별 집계 두 개 |
| 9 | `python scripts/rejudge/make_public.py` | 초록을 뺀 공개용 JSON과 엑셀(`release/`) |

일치도 표본과 코딩지는 `python scripts/rejudge/kappa_sample.py`로 만들었다. `node scripts/reextract_originals.js`는 상세 조회 응답을 다시 받아 캐시와 대조한 점검 스크립트이다. 엑셀을 만드는 단계에는 `openpyxl`이, 집계 하나(`ref_aggregate.pl`)에는 Perl이 필요하다.

## 재배포하지 않는 자료

- KCI에서 받은 초록과 참고문헌 목록: 저작권과 KCI 이용 조건을 고려하여 싣지 않았다. 대신 논문 식별자(artiId)와 KCI 링크를 엑셀에 두었고, 이 자료가 필요한 두 지표(참고문헌의 출처·분야 구성, 학교급)는 논문별 집계로 제공한다.
- 판정에 넣은 입력 묶음: 초록이 들어 있어 싣지 않았다. 판정 지침과 판정 출력은 모두 실었다.
- 공개본을 만들면서 KCI 응답에서 잘못 옮겨진 값 두 가지를 비웠다: DOI 칸에 참고문헌 블록이 섞인 158편의 DOI, 영문 주제어 칸에 영문 초록이 들어간 1편(제외 논문)의 영문 주제어. 분석 결과에는 영향이 없다.

## 판정 방식

포함 여부와 코딩은 연구자가 정한 지침(`data/rejudge/CODING_GUIDE.md`, 부록 A)에 따라 대규모 언어모델이 수행하였다. 판정자가 경계로 표시했거나 사전 규칙 판정과 결과가 달라진 438편은 연구자가 초록을 직접 검토하여 판정을 확정하였다(엑셀 3번 시트). 같은 지침을 다른 언어모델이 확정 판정값을 보지 않고 적용한 독립 재판정과의 일치도는 부록 C에 있다. 두 판정자는 같은 계열의 언어모델이므로 이 일치도는 판정의 재현성을 보여 줄 뿐 연구자 판정과의 일치를 보여 주지 않는다.

## 라이선스

자료(판정·코딩 결과, 지침, 판정 출력, 집계, 결과 파일, 부록, README)는 CC BY 4.0(`LICENSE-DATA.md`), `scripts/`의 코드는 MIT(`LICENSE`)를 따른다. 논문별 서지 정보는 KCI의 자료이며 KCI 이용 조건이 적용된다.
