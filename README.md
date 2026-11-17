# Detecção de fraudes e anomalias com agente de IA

Protótipo que identifica transações suspeitas com regras determinísticas e usa um modelo do **Azure AI Foundry** para explicar os alertas em linguagem clara. O agente não calcula nada por conta própria: ele aciona as ferramentas do projeto e interpreta o resultado.

> Os alertas são indícios para revisão humana, não conclusões sobre fraude.

## Como funciona

1. **Regras (`src/tools.py`):**
   - `valor_atipico`: valor muito fora do padrão do estabelecimento (z-score robusto).
   - `possivel_duplicidade`: mesma conta, estabelecimento, valor e dia.
   - `rajada_de_transacoes`: muitas transações da mesma conta em 10 minutos.
2. **Agente (`src/agent.py`):** o modelo implantado no Foundry recebe a pergunta, chama `run_anomaly_rules` e escreve a explicação.
3. **Interface (`src/app.py`):** Streamlit para enviar um CSV, ver os alertas e pedir a explicação.

O motivo dessa separação está em `docs/decisions.md`.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Testes das regras (não precisam de Azure)
python -m pytest -q

# Gerar o exemplo sintético
python data/generate_sample.py

# Interface
streamlit run src/app.py
```

## Configurar o Azure AI Foundry

1. No portal do Azure, crie ou abra um recurso de Azure OpenAI / Foundry e implante um modelo de chat.
2. Copie `.env.example` para `.env`, preencha o endpoint e o nome da implantação.
3. A chave da API vem de um destes lugares:
   - **Key Vault (recomendado):** defina `KEY_VAULT_URL` e guarde a chave como segredo `AZURE-OPENAI-API-KEY`. Rode `az login` antes, e sua conta precisa da função **Key Vault Secrets User**.
   - **Local:** defina `AZURE_OPENAI_API_KEY` no `.env`.
4. O arquivo `.env` está no `.gitignore`. Nunca commite chaves.

Se o Key Vault estiver configurado, ele tem prioridade sobre `AZURE_OPENAI_API_KEY`. Sem essas variáveis, a interface roda normalmente e só desativa o botão de explicação.

## Formato do CSV

| coluna           | exemplo              |
|------------------|----------------------|
| transaction_id   | T00042               |
| account_id       | ACC001               |
| timestamp        | 2026-10-14 13:05:00  |
| amount           | 129.90               |
| merchant         | Supermercado         |

## Limitações

- Regras heurísticas, com limites escolhidos para o exemplo. Não substituem um modelo treinado com dados rotulados de fraude.
- Os dados do repositório são sintéticos.
- A integração com o Azure foi escrita com o cliente `AzureOpenAI`, mas ainda não foi testada contra uma implantação real aqui.

## Estrutura

```
src/tools.py          regras de detecção (determinísticas, testadas)
src/config.py         leitura de configuração (chave do Key Vault ou do ambiente)
src/agent.py          agente que usa o Azure AI Foundry
src/app.py            interface Streamlit
data/generate_sample.py  gera transações sintéticas com anomalias plantadas
tests/test_tools.py   testes das regras
docs/decisions.md     decisões de projeto e limitações
```
