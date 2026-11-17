"""Agente que usa o Azure AI Foundry (modelo implantado) para investigar anomalias.

O modelo não calcula nada por conta própria: ele decide chamar a ferramenta
`run_anomaly_rules`, que executa as regras determinísticas de tools.py, e
depois explica os alertas em linguagem clara.

Variáveis de ambiente (veja .env.example):
    AZURE_OPENAI_ENDPOINT     https://<seu-recurso>.openai.azure.com/
    AZURE_OPENAI_API_KEY      chave do recurso
    AZURE_OPENAI_DEPLOYMENT   nome da implantação do modelo no Foundry
    AZURE_OPENAI_API_VERSION  versão da API (opcional)
"""

from __future__ import annotations

import json
import os

import pandas as pd

from src.tools import run_all_rules

SYSTEM_PROMPT = (
    "Você é um analista de prevenção a fraudes. Use a ferramenta run_anomaly_rules "
    "para obter os alertas antes de responder. Nunca invente transações ou valores: "
    "cite apenas os IDs e detalhes retornados pela ferramenta. Para cada alerta "
    "relevante, explique o motivo em português, em linguagem objetiva, e diga que "
    "se trata de um indício que precisa de revisão humana, e não de uma conclusão."
)

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "run_anomaly_rules",
        "description": "Executa as regras de detecção de fraudes e devolve os alertas.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}

MAX_ALERTS_IN_CONTEXT = 50


def _client():
    from openai import AzureOpenAI

    missing = [v for v in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT") if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Configure as variáveis de ambiente: {', '.join(missing)}")
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def explain_alerts(df: pd.DataFrame, question: str = "Quais transações merecem revisão e por quê?") -> str:
    """Roda o agente sobre o DataFrame e devolve a explicação em texto."""
    client = _client()
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    first = client.chat.completions.create(model=deployment, messages=messages, tools=[TOOL_SPEC])
    reply = first.choices[0].message

    if not reply.tool_calls:
        return reply.content or ""

    messages.append(reply)
    for call in reply.tool_calls:
        if call.function.name != "run_anomaly_rules":
            continue
        alerts = run_all_rules(df)
        payload = {
            "total_alertas": int(len(alerts)),
            "alertas": alerts.head(MAX_ALERTS_IN_CONTEXT).to_dict(orient="records"),
        }
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "content": json.dumps(payload, ensure_ascii=False)}
        )

    final = client.chat.completions.create(model=deployment, messages=messages)
    return final.choices[0].message.content or ""
