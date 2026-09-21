#!/usr/bin/env python3
"""은행거래·통화내역 샘플 CSV 생성 (2000 / 10000).

피의자 조직(두목·gate-keeper·영업/보고-hub·영업) + 일반인 혼재 + 대포폰 패턴.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from police_graph.sample_gen import generate_sample_data


def main() -> None:
    parser = argparse.ArgumentParser(description="경찰 사건 분석용 샘플 CSV 생성")
    parser.add_argument(
        "--size",
        type=int,
        choices=[2000, 10000],
        default=2000,
        help="은행·통화 각각 생성할 건수 (2000 또는 10000)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data"),
        help="출력 디렉터리 (기본: data/)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--civilians",
        type=int,
        default=80,
        help="일반인 수 (피의자 17명과 혼재)",
    )
    args = parser.parse_args()

    result = generate_sample_data(
        args.out,
        n_bank=args.size,
        n_call=args.size,
        seed=args.seed,
        n_civilians=args.civilians,
    )
    print(
        f"생성 완료: bank={result['n_bank']} call={result['n_call']} "
        f"civilians={result['n_civilians']}\n"
        f"  역할: {result['role_counts']}\n"
        f"  {result['bank_path']}\n"
        f"  {result['call_path']}\n"
        f"  {result['roster_path']}\n"
        f"  {result['timeline_path']}"
    )


if __name__ == "__main__":
    main()
