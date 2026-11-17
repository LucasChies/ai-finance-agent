import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.generate_sample import generate  # noqa: E402
from src.tools import (  # noqa: E402
    flag_amount_outliers,
    flag_duplicates,
    flag_velocity,
    load_transactions,
    run_all_rules,
)


def test_planted_anomalies_are_detected():
    df, planted = generate()
    alerts = run_all_rules(load_transactions(df))
    flagged = set(alerts["transaction_id"])
    missing = planted - flagged
    assert not missing, f"anomalias plantadas não detectadas: {missing}"


def test_outlier_rule_flags_extreme_amount():
    df, _ = generate()
    flags = flag_amount_outliers(load_transactions(df))
    assert "P_OUTLIER" in set(flags["transaction_id"])


def test_duplicate_rule_flags_second_occurrence_only():
    df, _ = generate()
    flags = flag_duplicates(load_transactions(df))
    ids = set(flags["transaction_id"])
    assert "P_DUP" in ids
    assert "T00010" not in ids  # a original não deve ser marcada


def test_velocity_rule_flags_burst():
    df, _ = generate()
    flags = flag_velocity(load_transactions(df))
    assert any(t.startswith("P_BURST") for t in flags["transaction_id"])


def test_clean_data_produces_no_alerts():
    import pandas as pd

    clean = pd.DataFrame(
        {
            "transaction_id": [f"C{i}" for i in range(30)],
            "account_id": ["ACC1"] * 30,
            "timestamp": pd.date_range("2026-01-01", periods=30, freq="D"),
            "amount": [50.0 + (i % 5) for i in range(30)],
            "merchant": ["Mercado"] * 30,
        }
    )
    assert run_all_rules(load_transactions(clean)).empty


def test_missing_column_raises():
    import pandas as pd
    import pytest

    with pytest.raises(ValueError, match="ausentes"):
        load_transactions(pd.DataFrame({"transaction_id": [1]}))
