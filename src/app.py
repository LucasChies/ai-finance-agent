"""Interface simples: envie um CSV de transações, rode as regras e, se configurado, peça uma explicação ao agente.

Execute com:
    streamlit run src/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools import load_transactions, run_all_rules  # noqa: E402

st.set_page_config(page_title="Detecção de anomalias", layout="wide")
st.title("Detecção de fraudes e anomalias")
st.caption("Os alertas são indícios para revisão humana, não conclusões.")

uploaded = st.file_uploader("CSV de transações", type="csv")
sample = Path(__file__).resolve().parents[1] / "data" / "sample_transactions.csv"
use_sample = st.checkbox("Usar o arquivo de exemplo sintético", value=uploaded is None)

source = None
if uploaded is not None:
    source = uploaded
elif use_sample and sample.exists():
    source = sample

if source is None:
    st.info("Envie um CSV ou use o exemplo. Colunas: transaction_id, account_id, timestamp, amount, merchant.")
    st.stop()

try:
    transactions = load_transactions(source)
except ValueError as error:
    st.error(str(error))
    st.stop()

alerts = run_all_rules(transactions)

col1, col2 = st.columns(2)
col1.metric("Transações analisadas", len(transactions))
col2.metric("Alertas", len(alerts))

st.subheader("Alertas")
if alerts.empty:
    st.success("Nenhum alerta com as regras atuais.")
else:
    st.dataframe(alerts, use_container_width=True)

st.subheader("Explicação com IA")
if not all(os.getenv(v) for v in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")):
    st.info("Para ativar, configure as variáveis do Azure AI Foundry (veja .env.example).")
elif st.button("Explicar alertas"):
    from src.agent import explain_alerts

    with st.spinner("Consultando o modelo no Azure AI Foundry..."):
        try:
            st.markdown(explain_alerts(transactions))
        except Exception as error:  # mostra o erro sem derrubar a interface
            st.error(f"Falha ao consultar o modelo: {error}")
