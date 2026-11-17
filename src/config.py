"""Leitura de configuração do Azure AI Foundry.

Ordem de busca da chave da API:
1. Se KEY_VAULT_URL estiver definido, busca o segredo no Azure Key Vault
   usando a identidade do ambiente (az login localmente, ou identidade gerenciada).
2. Caso contrário, usa AZURE_OPENAI_API_KEY do ambiente ou do .env.

O endereço do endpoint e o nome da implantação sempre vêm do ambiente.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # carrega o .env local, se existir

DEFAULT_SECRET_NAME = "AZURE-OPENAI-API-KEY"
REQUIRED_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")


@lru_cache(maxsize=1)
def get_api_key() -> str:
    """Devolve a chave da API, do Key Vault se configurado, senão do ambiente."""
    vault_url = os.getenv("KEY_VAULT_URL")
    if vault_url:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        secret_name = os.getenv("AZURE_OPENAI_KEY_SECRET_NAME", DEFAULT_SECRET_NAME)
        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        return client.get_secret(secret_name).value

    key = os.getenv("AZURE_OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "Chave não encontrada: defina KEY_VAULT_URL ou AZURE_OPENAI_API_KEY."
        )
    return key


def missing_settings() -> list[str]:
    """Lista o que falta para chamar o modelo, sem acessar o Key Vault."""
    missing = [name for name in REQUIRED_SETTINGS if not os.getenv(name)]
    if not os.getenv("KEY_VAULT_URL") and not os.getenv("AZURE_OPENAI_API_KEY"):
        missing.append("KEY_VAULT_URL ou AZURE_OPENAI_API_KEY")
    return missing


def is_configured() -> bool:
    return not missing_settings()
