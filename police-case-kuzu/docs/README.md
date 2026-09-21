# 경찰 사건 분석 (Kuzu) — 통화기록 · 은행거래

임베디드 그래프 DB [Kuzu](https://kuzudb.github.io/docs/)로 **핸드폰 통화기록**과 **은행 이체기록**을 하나의 그래프에 올려, 공범 후보·자금 흐름을 분석합니다.

> 샘플 데이터는 **가상의 수사 시나리오**입니다. 실무 적용 시 개인정보·수사 규정에 맞게 마스킹·접근통제를 하세요.

## 그래프 모델

| 종류 | 이름 | 의미 |
|------|------|------|
| Node | `Person` | 인물 (이름 = id) |
| Node | `Phone` | 전화번호 |
| Node | `Account` | 은행계좌 |
| Rel | `OwnsPhone` / `OwnsAccount` | 소유 |
| Rel | `Called` | 통화 |
| Rel | `Transferred` | 이체 (출금→상대 / 입금←상대) |

```
Person ──OwnsPhone──▶ Phone ──Called──▶ Phone ◀──OwnsPhone── Person
Person ──OwnsAccount─▶ Account ──Transferred──▶ Account ◀──OwnsAccount── Person
```

## 환경 설정

```bash
cd police-case-kuzu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실무 CSV 포맷

### 1. 은행거래 — `bank_transactions.csv`

| 컬럼 | 설명 |
|------|------|
| 입출금구분 | 입금 / 출금 |
| 계좌주 | 본인 예금주 |
| 금융기관 | 은행명 |
| 계좌번호 | 본인 계좌 |
| 거래일자 | YYYY-MM-DD |
| 거래시간 | HH:MM:SS |
| 거래종류 | 이체, ATM 등 |
| 취급점 | 지점명 |
| 임금적요 | 입금 적요 (원본 표기) |
| 입금액 | 숫자 (콤마 허용) |
| 출금적요 | 출금 적요 |
| 출금액 | 숫자 |
| 거래후잔액 | 숫자 |
| 상대은행 | 상대 금융기관 |
| 상대예금주 | 상대 예금주 |
| 상대계좌번호 | 상대 계좌 |
| 단말번호 | 단말 ID |
| IP주소 | IP |
| MAC주소 | MAC |
| 비고1 | 비고 (샘플은 값 없음) |
| 비고2 | 비고 (샘플은 값 없음) |

**그래프 매핑**

- `출금` + 출금액 > 0 → `계좌번호` → `상대계좌번호`
- `입금` + 입금액 > 0 → `상대계좌번호` → `계좌번호`

### 2. 통화내역 — `call_records.csv`

| 컬럼 | 설명 |
|------|------|
| 발신인 / 발신번호 | 발신 인물·번호 |
| 착신인 / 착신번호 | 착신 인물·번호 |
| 시작일자 / 시작시간 | 시작 시각 |
| 종료일자 / 종료시간 | 종료 시각 |
| 통화시간(분) | 분 단위 (소수 허용) → 내부 `duration_sec` |
| 업체명 | 통신사 |
| 발신위치 / 발신종료 | 위치 |
| 비고1 / 비고2 | 비고 (샘플은 값 없음) |

## 샘플 데이터 생성

```bash
# 은행 2000건 + 통화 2000건 (피의자 17 + 일반인 80 혼재)
PYTHONPATH=src python scripts/generate_sample_data.py --size 2000 --out data

# 1만건
PYTHONPATH=src python scripts/generate_sample_data.py --size 10000 --out data --civilians 200
```

### 조직 역할 (피의자 17명)

| 역할 | 인원 | 통신·자금 패턴 |
|------|------|----------------|
| 두목 | 1 | gate-keeper와만 주로 통화, 최종 상납 수신 |
| gate-keeper | 1 | 두목↔허브 브릿지 |
| 영업-hub | 3 | 영업 fan-out 조율, 집금 중간 계좌 |
| 보고-hub | 2 | 영업→짧은 버스트 보고 수신 |
| 영업 | 10 | 일시 교체 대포폰으로 일반인 아웃바운드 |

**대포폰**: 피의자마다 `meta/phone_timeline.csv`에 `active_from` 시각이 있고, 그 시각 이후 통화의 발신/착신번호가 바뀝니다. **MAC주소는 은행거래 단말 필드**이며 대포폰과 무관합니다.

### 디렉터리 배치

```
data/
  bank_transactions.csv   # 실무 입력
  call_records.csv        # 실무 입력
  meta/                   # 샘플 생성 시 정답표만 (적재에 사용하지 않음)
    persons_roster.csv
    phone_timeline.csv
```

시나리오 고정명: **김철수=두목**, **이영희=gate-keeper**.

## 테스트 / 분석 실행

```bash
pytest -q
PYTHONPATH=src python scripts/run_analysis.py
```

주요 API (`CaseAnalyzer`):

1. `top_call_partners(person_id)` — 예: `"김철수"`
2. `money_flows_from(account_id)` — 예: `"110-111-0001"`
3. `cross_link_call_and_transfer()` — 통화+이체 교차
4. `activity_hubs()` — 활동 허브

## 패키지 구조

```
src/police_graph/
  formats.py      # 실무 컬럼 상수
  normalize.py    # 원본 → 그래프 엔티티
  sample_gen.py   # 샘플 생성
  loader.py       # 정규화 후 Kuzu COPY
  schema.py / analysis.py / db.py
data/
  bank_transactions.csv
  call_records.csv
  meta/
    persons_roster.csv
    phone_timeline.csv
scripts/
  generate_sample_data.py
  run_analysis.py
tests/
```
