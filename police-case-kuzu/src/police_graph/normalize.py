"""실무 CSV → 그래프용 엔티티 정규화."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _parse_amount(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text in ("", "-", "nan", "None"):
        return 0.0
    return float(text)


def _parse_minutes_to_sec(value: Any) -> int:
    minutes = _parse_amount(value)
    return int(round(minutes * 60))


def _dt(date_s: str, time_s: str) -> str:
    d = str(date_s).strip()
    t = str(time_s).strip() or "00:00:00"
    if not d:
        return ""
    return f"{d}T{t}"


def _person(name: str, role: str = "") -> dict[str, str] | None:
    name = str(name).strip()
    if not name:
        return None
    return {"id": name, "name": name, "role": role}


def _merge_persons(*maps: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for m in maps:
        out.update(m)
    return list(out.values())


def normalize_bank_rows(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """은행거래 원본 → persons/accounts/owns_account/transfers."""
    persons: dict[str, dict[str, str]] = {}
    accounts: dict[str, dict[str, str]] = {}
    owns: dict[tuple[str, str], dict[str, str]] = {}
    transfers: list[dict[str, Any]] = []

    for i, row in df.fillna("").astype(str).iterrows():
        owner = str(row.get("계좌주", "")).strip()
        bank = str(row.get("금융기관", "")).strip()
        acct = str(row.get("계좌번호", "")).strip()
        counter_owner = str(row.get("상대예금주", "")).strip()
        counter_bank = str(row.get("상대은행", "")).strip()
        counter_acct = str(row.get("상대계좌번호", "")).strip()
        direction = str(row.get("입출금구분", "")).strip()
        deposit = _parse_amount(row.get("입금액", 0))
        withdraw = _parse_amount(row.get("출금액", 0))
        at = _dt(row.get("거래일자", ""), row.get("거래시간", ""))
        memo_in = str(row.get("임금적요", "") or row.get("입금적요", "")).strip()
        memo_out = str(row.get("출금적요", "")).strip()
        memo = memo_out or memo_in

        if owner:
            persons[owner] = _person(owner)  # type: ignore[assignment]
        if counter_owner:
            persons[counter_owner] = _person(counter_owner)  # type: ignore[assignment]

        if acct:
            accounts[acct] = {
                "account_id": acct,
                "bank": bank,
                "account_type": "입출금",
            }
            if owner:
                owns[(owner, acct)] = {"from": owner, "to": acct}

        if counter_acct:
            accounts[counter_acct] = {
                "account_id": counter_acct,
                "bank": counter_bank,
                "account_type": "입출금",
            }
            if counter_owner:
                owns[(counter_owner, counter_acct)] = {
                    "from": counter_owner,
                    "to": counter_acct,
                }

        if not acct or not counter_acct:
            continue

        # 출금: 본인계좌 → 상대 / 입금: 상대 → 본인계좌
        is_withdraw = direction == "출금" or (withdraw > 0 and deposit == 0)
        is_deposit = direction == "입금" or (deposit > 0 and withdraw == 0)

        if is_withdraw and withdraw > 0:
            transfers.append(
                {
                    "from_account": acct,
                    "to_account": counter_acct,
                    "tx_id": f"B{i}",
                    "amount": withdraw,
                    "transferred_at": at,
                    "memo": memo,
                    "direction": "출금",
                    "tx_type": str(row.get("거래종류", "")).strip(),
                    "branch": str(row.get("취급점", "")).strip(),
                    "balance_after": _parse_amount(row.get("거래후잔액", 0)),
                    "terminal": str(row.get("단말번호", "")).strip(),
                    "ip": str(row.get("IP주소", "")).strip(),
                    "mac": str(row.get("MAC주소", "")).strip(),
                    "note1": str(row.get("비고1", "")).strip(),
                    "note2": str(row.get("비고2", "")).strip(),
                }
            )
        elif is_deposit and deposit > 0:
            transfers.append(
                {
                    "from_account": counter_acct,
                    "to_account": acct,
                    "tx_id": f"B{i}",
                    "amount": deposit,
                    "transferred_at": at,
                    "memo": memo,
                    "direction": "입금",
                    "tx_type": str(row.get("거래종류", "")).strip(),
                    "branch": str(row.get("취급점", "")).strip(),
                    "balance_after": _parse_amount(row.get("거래후잔액", 0)),
                    "terminal": str(row.get("단말번호", "")).strip(),
                    "ip": str(row.get("IP주소", "")).strip(),
                    "mac": str(row.get("MAC주소", "")).strip(),
                    "note1": str(row.get("비고1", "")).strip(),
                    "note2": str(row.get("비고2", "")).strip(),
                }
            )

    return {
        "persons": list(persons.values()),
        "accounts": list(accounts.values()),
        "owns_account": list(owns.values()),
        "transfers": transfers,
    }


def normalize_call_rows(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """통화내역 원본 → persons/phones/owns_phone/calls."""
    persons: dict[str, dict[str, str]] = {}
    phones: dict[str, dict[str, str]] = {}
    owns: dict[tuple[str, str], dict[str, str]] = {}
    calls: list[dict[str, Any]] = []

    for i, row in df.fillna("").astype(str).iterrows():
        caller = str(row.get("발신인", "")).strip()
        callee = str(row.get("착신인", "")).strip()
        from_num = str(row.get("발신번호", "")).strip()
        to_num = str(row.get("착신번호", "")).strip()
        carrier = str(row.get("업체명", "")).strip()
        started = _dt(row.get("시작일자", ""), row.get("시작시간", ""))
        ended = _dt(row.get("종료일자", ""), row.get("종료시간", ""))
        duration_sec = _parse_minutes_to_sec(row.get("통화시간(분)", 0))

        if caller:
            persons[caller] = _person(caller)  # type: ignore[assignment]
        if callee:
            persons[callee] = _person(callee)  # type: ignore[assignment]

        if from_num:
            phones[from_num] = {"number": from_num, "carrier": carrier}
            if caller:
                owns[(caller, from_num)] = {
                    "from": caller,
                    "to": from_num,
                    "since": "",
                }
        if to_num:
            # 착신 번호는 업체가 비어 있을 수 있음
            if to_num not in phones:
                phones[to_num] = {"number": to_num, "carrier": ""}
            if callee:
                owns[(callee, to_num)] = {
                    "from": callee,
                    "to": to_num,
                    "since": "",
                }

        if not from_num or not to_num:
            continue

        calls.append(
            {
                "from_phone": from_num,
                "to_phone": to_num,
                "call_id": f"C{i}",
                "started_at": started,
                "ended_at": ended,
                "duration_sec": duration_sec,
                "call_type": "voice",
                "company": carrier,
                "location": str(row.get("발신위치", "")).strip(),
                "end_location": str(row.get("발신종료", "")).strip(),
                "note1": str(row.get("비고1", "")).strip(),
                "note2": str(row.get("비고2", "")).strip(),
            }
        )

    return {
        "persons": list(persons.values()),
        "phones": list(phones.values()),
        "owns_phone": list(owns.values()),
        "calls": calls,
    }


def merge_graph_parts(
    bank: dict[str, list[dict[str, Any]]],
    call: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """은행·통화 정규화 결과를 하나의 그래프 파트로 합친다."""
    persons = {p["id"]: p for p in bank.get("persons", [])}
    for p in call.get("persons", []):
        persons[p["id"]] = p

    return {
        "persons": list(persons.values()),
        "phones": call.get("phones", []),
        "accounts": bank.get("accounts", []),
        "owns_phone": call.get("owns_phone", []),
        "owns_account": bank.get("owns_account", []),
        "calls": call.get("calls", []),
        "transfers": bank.get("transfers", []),
    }
