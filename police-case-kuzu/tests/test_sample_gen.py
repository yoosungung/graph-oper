"""샘플 데이터 생성기 테스트."""

from pathlib import Path

import pandas as pd

from police_graph.formats import BANK_COLUMNS, CALL_COLUMNS
from police_graph.sample_gen import generate_sample_data


def test_generate_sample_data_2000(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=2000, n_call=2000, seed=42)

    bank = pd.read_csv(result["bank_path"])
    call = pd.read_csv(result["call_path"])

    assert list(bank.columns) == BANK_COLUMNS
    assert list(call.columns) == CALL_COLUMNS
    assert len(bank) == 2000
    assert len(call) == 2000
    # 시나리오 인물 포함
    assert "김철수" in set(bank["계좌주"]) | set(bank["상대예금주"])
    assert "김철수" in set(call["발신인"]) | set(call["착신인"])


def test_generate_sample_data_10000_row_count(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=10_000, n_call=10_000, seed=7)
    assert sum(1 for _ in open(result["bank_path"], encoding="utf-8")) == 10_001
    assert sum(1 for _ in open(result["call_path"], encoding="utf-8")) == 10_001
