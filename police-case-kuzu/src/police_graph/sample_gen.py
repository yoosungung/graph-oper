"""가상 은행거래·통화내역 샘플 CSV 생성.

조직 구조(피의자 17명) + 일반인 혼재 + 대포폰(일시별 번호 교체) 패턴.

웹·판례에서 보강한 패턴:
- 게이트키퍼가 두목과 하부 조직을 잇는 브릿지
- 짧은 버스트 통화·순차 콜체인(보고-hub ← 영업)
- 영업-hub의 높은 fan-out
- 대포폰: 피의자가 특정 일자·시각 이후 다른 번호로 교체 (통화 기록에 반영)
- MAC주소: 은행거래 단말 필드만 사용 (통화/대포폰과 무관)
- 자금: 피해자/일반인 → 영업 → 영업-hub → gate-keeper → 두목
- 일반인 트래픽으로 위장
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .formats import (
    BANK_COLUMNS,
    BANK_FILENAME,
    CALL_COLUMNS,
    CALL_FILENAME,
    META_DIRNAME,
    ROSTER_FILENAME,
    TIMELINE_FILENAME,
)

ORG_ROLE_COUNTS: dict[str, int] = {
    "두목": 1,
    "gate-keeper": 1,
    "영업-hub": 3,
    "보고-hub": 2,
    "영업": 10,
}

_BANKS = ["국민은행", "신한은행", "우리은행", "하나은행", "카카오뱅크", "토스뱅크", "농협"]
_CARRIERS = ["SKT", "KT", "LGU+"]
_LOCATIONS = [
    "서울 강남",
    "서울 서초",
    "서울 영등포",
    "부산 해운대",
    "인천 부평",
    "대전 유성",
    "대구 수성",
    "수원 영통",
]

_FIXED_SUSPECTS: list[dict[str, str]] = [
    {"name": "김철수", "role": "두목"},
    {"name": "이영희", "role": "gate-keeper"},
    {"name": "박민수", "role": "영업-hub"},
    {"name": "최지훈", "role": "영업-hub"},
    {"name": "정하늘", "role": "영업-hub"},
    {"name": "오세진", "role": "보고-hub"},
    {"name": "윤다은", "role": "보고-hub"},
    {"name": "한지우", "role": "영업"},
    {"name": "강민재", "role": "영업"},
    {"name": "서유진", "role": "영업"},
    {"name": "조현우", "role": "영업"},
    {"name": "임수빈", "role": "영업"},
    {"name": "배성호", "role": "영업"},
    {"name": "홍예린", "role": "영업"},
    {"name": "문재혁", "role": "영업"},
    {"name": "신소희", "role": "영업"},
    {"name": "권태영", "role": "영업"},
]

_CIVILIAN_POOL = [
    "남지연", "송우진", "류하준", "황미경", "전성호", "고은비", "양준석", "차미래",
    "유태경", "노시우", "도하린", "마준호", "변서연", "설진우", "안채원", "장도윤",
]

# 시나리오 기간 (통화/이체 생성 범위)
_SCENARIO_START = datetime(2024, 1, 1)
_SCENARIO_DAYS = 280


def _rand_dt(rng: random.Random, start: datetime, days: int) -> datetime:
    return start + timedelta(
        days=rng.randint(0, days),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )


def _bank_mac(rng: random.Random) -> str:
    """은행 단말/접속 MAC (통화·대포폰과 무관)."""
    return ":".join(f"{rng.randint(0, 255):02X}" for _ in range(6))


def _phone(prefix: int, idx: int, slot: int = 0) -> str:
    return f"010-{prefix + idx:04d}-{1000 + slot * 100 + (idx % 90):04d}"


def _account(bank_idx: int, idx: int) -> tuple[str, str]:
    bank = _BANKS[bank_idx % len(_BANKS)]
    return bank, f"{100 + bank_idx:03d}-{200 + idx:03d}-{3000 + idx:04d}"


def _build_phone_timeline(
    phones: list[str], rng: random.Random, start: datetime
) -> list[dict[str, Any]]:
    """번호 목록을 시간순 교체 구간으로 만든다. active_from 이후 해당 번호 사용."""
    assert phones
    timeline: list[dict[str, Any]] = [
        {"phone": phones[0], "active_from": start}
    ]
    # 교체 시점을 시나리오 중반에 골고루 배치
    span = _SCENARIO_DAYS
    for i, phone in enumerate(phones[1:], start=1):
        # i번째 교체: 대략 span*(i)/(n) 근처 ± 여유
        n = len(phones)
        center_day = int(span * i / n)
        jitter = rng.randint(-10, 10)
        day = max(5, min(span - 5, center_day + jitter))
        switch_at = start + timedelta(
            days=day,
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        # 단조 증가 보장
        if switch_at <= timeline[-1]["active_from"]:
            switch_at = timeline[-1]["active_from"] + timedelta(days=3, hours=1)
        timeline.append({"phone": phone, "active_from": switch_at})
    return timeline


def active_phone_at(person: dict[str, Any], when: datetime) -> str:
    """해당 시각에 피의자/일반인이 사용 중인 번호."""
    timeline = person["phone_timeline"]
    current = timeline[0]["phone"]
    for seg in timeline:
        if when >= seg["active_from"]:
            current = seg["phone"]
        else:
            break
    return current


def build_population(
    seed: int = 42, n_civilians: int = 80
) -> dict[str, Any]:
    """피의자 조직 + 일반인 인구를 구성한다."""
    rng = random.Random(seed)
    assert len(_FIXED_SUSPECTS) == sum(ORG_ROLE_COUNTS.values())
    start = _SCENARIO_START

    suspects: list[dict[str, Any]] = []
    for i, fixed in enumerate(_FIXED_SUSPECTS):
        role = fixed["role"]
        n_phones = {
            "두목": 2,
            "gate-keeper": 4,
            "영업-hub": 3,
            "보고-hub": 3,
            "영업": 3,
        }[role]
        phones = [_phone(1100 + i * 10, i, s) for s in range(n_phones)]
        bank, acct = _account(i, i)
        timeline = _build_phone_timeline(phones, rng, start)
        suspects.append(
            {
                "name": fixed["name"],
                "role": role,
                "phones": phones,
                "phone": phones[0],
                "phone_timeline": timeline,
                "bank": bank,
                "account": acct,
            }
        )

    civilians: list[dict[str, Any]] = []
    for j in range(n_civilians):
        name = f"{_CIVILIAN_POOL[j % len(_CIVILIAN_POOL)]}{j:03d}"
        phone = _phone(8000, j, 0)
        bank, acct = _account(j + 20, j + 100)
        civilians.append(
            {
                "name": name,
                "role": "일반인",
                "phones": [phone],
                "phone": phone,
                # 일반인은 번호 고정
                "phone_timeline": [{"phone": phone, "active_from": start}],
                "bank": bank,
                "account": acct,
            }
        )

    role_counts = {
        role: sum(1 for s in suspects if s["role"] == role)
        for role in ORG_ROLE_COUNTS
    }
    return {
        "suspects": suspects,
        "civilians": civilians,
        "everyone": suspects + civilians,
        "role_counts": role_counts,
        "by_role": {
            role: [s for s in suspects if s["role"] == role]
            for role in ORG_ROLE_COUNTS
        },
    }


def _call_row(
    a: dict[str, Any],
    b: dict[str, Any],
    rng: random.Random,
    start: datetime,
    *,
    short: bool,
    note1: str,
    force_dt: datetime | None = None,
) -> dict[str, Any]:
    dt = force_dt or _rand_dt(rng, start, _SCENARIO_DAYS)
    mins = round(rng.uniform(0.2, 1.5) if short else rng.uniform(1.0, 18.0), 2)
    end = dt + timedelta(seconds=int(mins * 60))
    a_phone = active_phone_at(a, dt)
    b_phone = active_phone_at(b, dt)
    _ = note1  # 시나리오 태그용 인자(CSV 비고에는 기록하지 않음)
    return {
        "발신인": a["name"],
        "발신번호": a_phone,
        "착신인": b["name"],
        "착신번호": b_phone,
        "시작일자": dt.strftime("%Y-%m-%d"),
        "시작시간": dt.strftime("%H:%M:%S"),
        "종료일자": end.strftime("%Y-%m-%d"),
        "종료시간": end.strftime("%H:%M:%S"),
        "통화시간(분)": str(mins),
        "업체명": rng.choice(_CARRIERS),
        "발신위치": rng.choice(_LOCATIONS),
        "발신종료": rng.choice(_LOCATIONS),
        "비고1": "",
        "비고2": "",
    }


def _bank_out(
    src: dict[str, Any],
    dst: dict[str, Any],
    amount: int,
    rng: random.Random,
    start: datetime,
    note1: str,
) -> dict[str, Any]:
    dt = _rand_dt(rng, start, _SCENARIO_DAYS)
    return {
        "입출금구분": "출금",
        "계좌주": src["name"],
        "금융기관": src["bank"],
        "계좌번호": src["account"],
        "거래일자": dt.strftime("%Y-%m-%d"),
        "거래시간": dt.strftime("%H:%M:%S"),
        "거래종류": "이체",
        "취급점": f"{rng.choice(['강남', '역삼', '종로', '여의도'])}지점",
        "임금적요": "",
        "입금액": "0",
        "출금적요": note1 or "이체",
        "출금액": str(amount),
        "거래후잔액": str(rng.randint(50_000, 15_000_000)),
        "상대은행": dst["bank"],
        "상대예금주": dst["name"],
        "상대계좌번호": dst["account"],
        "단말번호": f"ATM{rng.randint(1000, 9999)}",
        "IP주소": f"203.0.113.{rng.randint(1, 254)}",
        "MAC주소": _bank_mac(rng),
        "비고1": "",
        "비고2": "",
    }


def _ensure_timeline_coverage_calls(
    person: dict[str, Any],
    partner: dict[str, Any],
    rng: random.Random,
    start: datetime,
) -> list[dict[str, Any]]:
    """각 번호 구간에서 최소 1통 이상 나가도록 보장 (테스트·분석용)."""
    rows: list[dict[str, Any]] = []
    tl = person["phone_timeline"]
    for i, seg in enumerate(tl):
        seg_start = seg["active_from"]
        seg_end = (
            tl[i + 1]["active_from"] - timedelta(minutes=5)
            if i + 1 < len(tl)
            else start + timedelta(days=_SCENARIO_DAYS)
        )
        if seg_end <= seg_start:
            seg_end = seg_start + timedelta(hours=6)
        delta = (seg_end - seg_start).total_seconds()
        when = seg_start + timedelta(seconds=rng.randint(60, max(120, int(delta * 0.4))))
        if when >= seg_end:
            when = seg_start + timedelta(minutes=30)
        rows.append(
            _call_row(
                person,
                partner,
                rng,
                start,
                short=False,
                note1="번호구간확보",
                force_dt=when,
            )
        )
    return rows


def _generate_org_calls(
    pop: dict[str, Any], rng: random.Random, start: datetime, budget: int
) -> list[dict[str, Any]]:
    by = pop["by_role"]
    boss = by["두목"][0]
    gk = by["gate-keeper"][0]
    sales_hubs = by["영업-hub"]
    report_hubs = by["보고-hub"]
    sales = by["영업"]
    civilians = pop["civilians"]
    rows: list[dict[str, Any]] = []

    # 두목·게이트키퍼 타임라인 구간별 통화 보장
    rows.extend(_ensure_timeline_coverage_calls(boss, gk, rng, start))
    rows.extend(_ensure_timeline_coverage_calls(gk, boss, rng, start))

    for _ in range(max(15, budget // 25)):
        a, b = (boss, gk) if rng.random() < 0.55 else (gk, boss)
        rows.append(_call_row(a, b, rng, start, short=False, note1="지휘"))

    for hub in sales_hubs + report_hubs:
        for _ in range(max(8, budget // 40)):
            a, b = (gk, hub) if rng.random() < 0.6 else (hub, gk)
            rows.append(_call_row(a, b, rng, start, short=True, note1="중계"))

    for rh in report_hubs:
        agents = rng.sample(sales, k=min(6, len(sales)))
        for agent in agents:
            for _ in range(rng.randint(2, 5)):
                rows.append(
                    _call_row(agent, rh, rng, start, short=True, note1="보고버스트")
                )

    for sh in sales_hubs:
        for agent in sales:
            for _ in range(rng.randint(1, 4)):
                a, b = (sh, agent) if rng.random() < 0.7 else (agent, sh)
                rows.append(
                    _call_row(a, b, rng, start, short=False, note1="영업조율")
                )

    for _ in range(max(30, budget // 4)):
        agent = rng.choice(sales)
        civ = rng.choice(civilians)
        rows.append(
            _call_row(agent, civ, rng, start, short=False, note1="영업통화")
        )

    for _ in range(2):
        rows.append(
            _call_row(
                boss, rng.choice(sales), rng, start, short=True, note1="예외직접"
            )
        )

    return rows[:budget] if len(rows) > budget else rows


def _generate_org_banks(
    pop: dict[str, Any], rng: random.Random, start: datetime, budget: int
) -> list[dict[str, Any]]:
    by = pop["by_role"]
    boss = by["두목"][0]
    gk = by["gate-keeper"][0]
    sales_hubs = by["영업-hub"]
    sales = by["영업"]
    civilians = pop["civilians"]
    rows: list[dict[str, Any]] = []

    for _ in range(max(40, budget // 3)):
        rows.append(
            _bank_out(
                rng.choice(civilians),
                rng.choice(sales),
                rng.choice([300_000, 500_000, 1_000_000, 2_000_000, 3_000_000]),
                rng,
                start,
                "피해금",
            )
        )
    for _ in range(max(25, budget // 5)):
        rows.append(
            _bank_out(
                rng.choice(sales),
                rng.choice(sales_hubs),
                rng.choice([1_000_000, 2_500_000, 5_000_000]),
                rng,
                start,
                "집금",
            )
        )
    for _ in range(max(15, budget // 8)):
        rows.append(
            _bank_out(
                rng.choice(sales_hubs),
                gk,
                rng.choice([3_000_000, 5_000_000, 7_500_000]),
                rng,
                start,
                "상납",
            )
        )
    for _ in range(max(10, budget // 10)):
        rows.append(
            _bank_out(
                gk,
                boss,
                rng.choice([5_000_000, 7_500_000, 10_000_000]),
                rng,
                start,
                "최종상납",
            )
        )
    return rows[:budget] if len(rows) > budget else rows


def _generate_civilian_noise(
    pop: dict[str, Any],
    rng: random.Random,
    start: datetime,
    n_call: int,
    n_bank: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    people = pop["everyone"]
    civilians = pop["civilians"]
    calls: list[dict[str, Any]] = []
    banks: list[dict[str, Any]] = []

    while len(calls) < n_call:
        a, b = (
            rng.sample(civilians, 2)
            if rng.random() < 0.75
            else (rng.choice(people), rng.choice(people))
        )
        if a["name"] == b["name"]:
            continue
        if a["role"] != "일반인" and b["role"] != "일반인" and rng.random() < 0.85:
            continue
        calls.append(
            _call_row(
                a,
                b,
                rng,
                start,
                short=rng.random() < 0.3,
                note1="일상",
            )
        )

    while len(banks) < n_bank:
        a, b = (
            rng.sample(civilians, 2)
            if rng.random() < 0.8
            else (rng.choice(people), rng.choice(people))
        )
        if a["account"] == b["account"]:
            continue
        if a["role"] != "일반인" and b["role"] != "일반인" and rng.random() < 0.9:
            continue
        banks.append(
            _bank_out(a, b, rng.randint(10_000, 800_000), rng, start, "생활비")
        )

    return calls, banks


def generate_sample_data(
    out_dir: str | Path,
    n_bank: int = 2000,
    n_call: int = 2000,
    seed: int = 42,
    n_civilians: int = 80,
    **_ignored: Any,
) -> dict[str, Any]:
    """은행·통화 CSV는 out_dir/, 보조 메타는 out_dir/meta/ 에 생성한다."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = out / META_DIRNAME
    meta.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start = _SCENARIO_START

    pop = build_population(seed=seed, n_civilians=n_civilians)

    org_call_budget = max(200, n_call * 35 // 100)
    org_bank_budget = max(150, n_bank * 30 // 100)

    org_calls = _generate_org_calls(pop, rng, start, org_call_budget)
    org_banks = _generate_org_banks(pop, rng, start, org_bank_budget)

    noise_calls, noise_banks = _generate_civilian_noise(
        pop,
        rng,
        start,
        n_call=max(0, n_call - len(org_calls)),
        n_bank=max(0, n_bank - len(org_banks)),
    )

    call_rows = (org_calls + noise_calls)[:n_call]
    bank_rows = (org_banks + noise_banks)[:n_bank]
    rng.shuffle(call_rows)
    rng.shuffle(bank_rows)

    while len(call_rows) < n_call:
        extra, _ = _generate_civilian_noise(pop, rng, start, 20, 0)
        call_rows.extend(extra)
    while len(bank_rows) < n_bank:
        _, extra = _generate_civilian_noise(pop, rng, start, 0, 20)
        bank_rows.extend(extra)
    call_rows = call_rows[:n_call]
    bank_rows = bank_rows[:n_bank]

    bank_path = out / BANK_FILENAME
    call_path = out / CALL_FILENAME
    roster_path = meta / ROSTER_FILENAME
    timeline_path = meta / TIMELINE_FILENAME

    pd.DataFrame(bank_rows, columns=BANK_COLUMNS).to_csv(bank_path, index=False)
    pd.DataFrame(call_rows, columns=CALL_COLUMNS).to_csv(call_path, index=False)

    roster_rows = []
    timeline_rows = []
    for p in pop["everyone"]:
        roster_rows.append(
            {
                "name": p["name"],
                "role": p["role"],
                "primary_phone": p["phone"],
                "phones": "|".join(p["phones"]),
                "account": p["account"],
                "bank": p["bank"],
            }
        )
        tl = p["phone_timeline"]
        for i, seg in enumerate(tl):
            active_to = (
                tl[i + 1]["active_from"].isoformat(sep=" ", timespec="seconds")
                if i + 1 < len(tl)
                else ""
            )
            timeline_rows.append(
                {
                    "name": p["name"],
                    "role": p["role"],
                    "phone": seg["phone"],
                    "active_from": seg["active_from"].isoformat(
                        sep=" ", timespec="seconds"
                    ),
                    "active_to": active_to,
                }
            )

    pd.DataFrame(roster_rows).to_csv(roster_path, index=False)
    pd.DataFrame(timeline_rows).to_csv(timeline_path, index=False)

    return {
        "bank_path": bank_path,
        "call_path": call_path,
        "roster_path": roster_path,
        "timeline_path": timeline_path,
        "n_bank": n_bank,
        "n_call": n_call,
        "people": [p["name"] for p in pop["everyone"]],
        "role_counts": pop["role_counts"],
        "n_civilians": n_civilians,
    }
