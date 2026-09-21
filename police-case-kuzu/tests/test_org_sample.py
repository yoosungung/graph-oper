"""조직·대포폰(일시 교체)·일반인 혼재 샘플 생성 테스트."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from police_graph.sample_gen import (
    ORG_ROLE_COUNTS,
    active_phone_at,
    build_population,
    generate_sample_data,
)


def test_org_role_counts() -> None:
    pop = build_population(seed=42, n_civilians=100)
    assert pop["role_counts"] == ORG_ROLE_COUNTS
    assert sum(ORG_ROLE_COUNTS.values()) == 17
    assert len(pop["civilians"]) == 100
    assert len(pop["suspects"]) == 17


def test_suspects_have_timed_phone_switches() -> None:
    """피의자 대포폰 = 특정 일시 이후 사용 번호가 바뀜."""
    pop = build_population(seed=42, n_civilians=50)
    for s in pop["suspects"]:
        timeline = s["phone_timeline"]
        assert len(timeline) >= 2, f"{s['name']} 교체 이력 부족"
        # 시간순·서로 번호가 달라짐
        assert timeline[0]["active_from"] < timeline[1]["active_from"]
        assert timeline[0]["phone"] != timeline[1]["phone"]

        before = timeline[1]["active_from"] - timedelta(minutes=1)
        after = timeline[1]["active_from"] + timedelta(minutes=1)
        assert active_phone_at(s, before) == timeline[0]["phone"]
        assert active_phone_at(s, after) == timeline[1]["phone"]


def test_calls_follow_phone_timeline(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=400, n_call=400, seed=42)
    call = pd.read_csv(result["call_path"])
    timeline = pd.read_csv(result["timeline_path"])
    boss_tl = timeline[timeline["name"] == "김철수"].sort_values("active_from")
    assert len(boss_tl) >= 2

    switch_at = datetime.fromisoformat(str(boss_tl.iloc[1]["active_from"]))
    phone_before = boss_tl.iloc[0]["phone"]
    phone_after = boss_tl.iloc[1]["phone"]

    boss_calls = call[call["발신인"] == "김철수"].copy()
    boss_calls["dt"] = pd.to_datetime(
        boss_calls["시작일자"] + " " + boss_calls["시작시간"]
    )
    early = boss_calls[boss_calls["dt"] < switch_at]
    late = boss_calls[boss_calls["dt"] >= switch_at]
    assert len(early) >= 1 and len(late) >= 1
    assert set(early["발신번호"]) == {phone_before}
    assert set(late["발신번호"]) == {phone_after}


def test_mac_only_on_bank_and_notes_empty(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=300, n_call=300, seed=7)
    bank = pd.read_csv(result["bank_path"])
    call = pd.read_csv(result["call_path"])

    assert bank["MAC주소"].astype(str).str.len().gt(0).any()
    assert (bank["비고1"].fillna("") == "").all()
    assert (bank["비고2"].fillna("") == "").all()
    assert (call["비고1"].fillna("") == "").all()
    assert (call["비고2"].fillna("") == "").all()


def test_meta_files_live_under_meta_dir(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=50, n_call=50, seed=1)
    assert result["bank_path"].parent == tmp_path
    assert result["call_path"].parent == tmp_path
    assert result["roster_path"].parent == tmp_path / "meta"
    assert result["timeline_path"].parent == tmp_path / "meta"
    assert result["roster_path"].exists()
    assert result["timeline_path"].exists()


def test_generated_data_mixes_civilians_and_suspects(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=500, n_call=500, seed=42)
    call = pd.read_csv(result["call_path"])
    roster = pd.read_csv(result["roster_path"])

    suspect_names = set(roster.loc[roster["role"] != "일반인", "name"])
    civilian_names = set(roster.loc[roster["role"] == "일반인", "name"])
    assert len(suspect_names) == 17
    assert len(civilian_names) >= 50

    call_people = set(call["발신인"]) | set(call["착신인"])
    assert suspect_names & call_people
    assert civilian_names & call_people


def test_boss_rarely_calls_sales_directly(tmp_path: Path) -> None:
    result = generate_sample_data(tmp_path, n_bank=800, n_call=800, seed=1)
    call = pd.read_csv(result["call_path"])
    roster = pd.read_csv(result["roster_path"]).set_index("name")

    boss = roster.index[roster["role"] == "두목"][0]
    sales = set(roster.index[roster["role"] == "영업"])

    def involves(a: str, b: str) -> pd.Series:
        return ((call["발신인"] == a) & (call["착신인"] == b)) | (
            (call["발신인"] == b) & (call["착신인"] == a)
        )

    direct = sum(involves(boss, s).sum() for s in sales)
    gk = roster.index[roster["role"] == "gate-keeper"][0]
    via_gk = involves(boss, gk).sum()
    assert via_gk > direct
