"""Regras determinísticas de detecção de fraudes e anomalias em transações.

Cada regra devolve linhas com: transaction_id, rule, detail.
O agente de IA apenas chama estas funções e explica o resultado; os
cálculos ficam aqui, testáveis e reproduzíveis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["transaction_id", "account_id", "timestamp", "amount", "merchant"]
FLAG_COLUMNS = ["transaction_id", "rule", "detail"]


def load_transactions(source) -> pd.DataFrame:
    """Lê transações de um caminho CSV ou de um DataFrame e valida o esquema."""
    df = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"])
    return df.sort_values("timestamp").reset_index(drop=True)


def flag_amount_outliers(df: pd.DataFrame, threshold: float = 6.0) -> pd.DataFrame:
    """Valores muito fora do padrão do próprio estabelecimento.

    Usa z-score robusto (mediana e MAD) por estabelecimento, para que um
    valor alto em um posto de gasolina não seja comparado com uma loja online.
    """
    rows = []
    for merchant, group in df.groupby("merchant"):
        median = group["amount"].median()
        mad = (group["amount"] - median).abs().median()
        if mad == 0:
            continue
        robust_z = 0.6745 * (group["amount"] - median) / mad
        for _, row in group[robust_z.abs() > threshold].iterrows():
            rows.append(
                {
                    "transaction_id": row["transaction_id"],
                    "rule": "valor_atipico",
                    "detail": (
                        f"R$ {row['amount']:.2f} em '{merchant}', "
                        f"mediana do estabelecimento R$ {median:.2f}"
                    ),
                }
            )
    return pd.DataFrame(rows, columns=FLAG_COLUMNS)


def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mesma conta, estabelecimento, valor e dia: marca as ocorrências repetidas."""
    dated = df.assign(_day=df["timestamp"].dt.date)
    key = ["account_id", "merchant", "amount", "_day"]
    repeated = df[dated.duplicated(subset=key, keep="first")]
    return pd.DataFrame(
        [
            {
                "transaction_id": row["transaction_id"],
                "rule": "possivel_duplicidade",
                "detail": f"mesmo valor R$ {row['amount']:.2f} em '{row['merchant']}' no mesmo dia",
            }
            for _, row in repeated.iterrows()
        ],
        columns=FLAG_COLUMNS,
    )


def flag_velocity(df: pd.DataFrame, window: str = "10min", max_tx: int = 5) -> pd.DataFrame:
    """Muitas transações da mesma conta em uma janela curta de tempo.

    Para cada transação, conta quantas da mesma conta caem em uma janela de
    `window` centrada nela. Assim, todas as transações de uma rajada são
    marcadas, e não só a que atinge o limite.
    """
    half = pd.Timedelta(window) / 2
    rows = []
    for account, group in df.groupby("account_id"):
        group = group.sort_values("timestamp")
        ts = group["timestamp"].to_numpy()
        lo = np.searchsorted(ts, ts - half.to_timedelta64(), side="left")
        hi = np.searchsorted(ts, ts + half.to_timedelta64(), side="right")
        in_window = hi - lo
        for transaction_id, count in zip(group["transaction_id"], in_window):
            if count >= max_tx:
                rows.append(
                    {
                        "transaction_id": transaction_id,
                        "rule": "rajada_de_transacoes",
                        "detail": f"conta {account} com {int(count)} transações em {window}",
                    }
                )
    return pd.DataFrame(rows, columns=FLAG_COLUMNS)


def run_all_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas as regras e devolve os alertas consolidados."""
    frames = [
        flag_amount_outliers(df),
        flag_duplicates(df),
        flag_velocity(df),
    ]
    alerts = pd.concat(frames, ignore_index=True)
    return alerts.drop_duplicates().reset_index(drop=True)
