"""Gera transações sintéticas com anomalias plantadas, para teste e demonstração.

Uso:
    python data/generate_sample.py
Gera data/sample_transactions.csv. Nenhum dado real é usado.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MERCHANTS = ["Supermercado", "Posto", "Restaurante", "Farmácia", "Streaming", "Transporte", "Loja Online"]


def generate(n: int = 800, seed: int = 7) -> tuple[pd.DataFrame, set[str]]:
    """Devolve (transações, ids das anomalias plantadas)."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-10-01")
    accounts = [f"ACC{i:03d}" for i in range(1, 21)]

    rows = []
    for i in range(n):
        rows.append(
            {
                "transaction_id": f"T{i:05d}",
                "account_id": rng.choice(accounts),
                "timestamp": start + pd.Timedelta(minutes=int(rng.integers(0, 60 * 24 * 30))),
                "amount": round(float(rng.lognormal(mean=3.5, sigma=0.4)), 2),
                "merchant": rng.choice(MERCHANTS),
            }
        )

    planted: set[str] = set()

    # 1) Valor muito acima do padrão de uma loja online
    rows.append(
        {
            "transaction_id": "P_OUTLIER",
            "account_id": "ACC001",
            "timestamp": start + pd.Timedelta(days=15),
            "amount": 9500.00,
            "merchant": "Loja Online",
        }
    )
    planted.add("P_OUTLIER")

    # 2) Cópia quase idêntica de T00010, dois minutos depois
    original = rows[10]
    rows.append(
        {
            **original,
            "transaction_id": "P_DUP",
            "timestamp": original["timestamp"] + pd.Timedelta(minutes=2),
        }
    )
    planted.add("P_DUP")

    # 3) Rajada: oito transações da mesma conta em quatro minutos
    burst_start = start + pd.Timedelta(days=20)
    for k in range(8):
        rows.append(
            {
                "transaction_id": f"P_BURST{k}",
                "account_id": "ACC005",
                "timestamp": burst_start + pd.Timedelta(seconds=30 * k),
                "amount": round(40 + k * 3.5, 2),
                "merchant": "Posto",
            }
        )
        planted.add(f"P_BURST{k}")

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df, planted


if __name__ == "__main__":
    df, _ = generate()
    out = Path(__file__).parent / "sample_transactions.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} transações gravadas em {out}")
