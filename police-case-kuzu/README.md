# 경찰 사건 분석 (Kuzu) — 통화기록 · 은행거래

임베디드 그래프 DB [Kuzu](https://kuzudb.github.io/docs/)로 **핸드폰 통화기록**과 **은행 이체기록**을 하나의 그래프에 올려, 공범 후보·자금 흐름을 분석합니다.

> 샘플 데이터는 **가상의 수사 시나리오**입니다. 실무 적용 시 개인정보·수사 규정에 맞게 마스킹·접근통제를 하세요.

상세 문서: [docs/README.md](docs/README.md)

## 빠른 시작

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 샘플 생성 (2000 또는 10000 — 피의자 조직 + 일반인 혼재 + 대포폰)
PYTHONPATH=src python scripts/generate_sample_data.py --size 2000 --out data

pytest -q
PYTHONPATH=src python scripts/load_sample_db.py   # → sample.db
PYTHONPATH=src python scripts/run_analysis.py
# CLI: kuzu ./sample.db
```

## 입력 CSV (실무 포맷)

| 파일 | 설명 |
|------|------|
| `data/bank_transactions.csv` | 은행거래 |
| `data/call_records.csv` | 통화내역 |

보조 메타(생성 정답만, 적재 미사용): `data/meta/`

## 분석 기능

| 메서드 | 용도 |
|--------|------|
| `top_call_partners` | 통화 상대 Top-N |
| `money_flows_from` | 계좌 자금 흐름 (1·2홉) |
| `cross_link_call_and_transfer` | 통화+이체 교차 (공범 후보) |
| `activity_hubs` | 활동 허브 인물 |
