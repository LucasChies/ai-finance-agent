import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402

ALL_VARS = [
    "KEY_VAULT_URL",
    "AZURE_OPENAI_KEY_SECRET_NAME",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ALL_VARS:
        monkeypatch.delenv(var, raising=False)
    config.get_api_key.cache_clear()
    yield
    config.get_api_key.cache_clear()


def test_falls_back_to_env_key_without_vault(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "chave-local")
    assert config.get_api_key() == "chave-local"


def test_reads_key_from_key_vault_with_default_secret_name(monkeypatch):
    requested = {}

    class FakeClient:
        def __init__(self, vault_url, credential):
            requested["vault_url"] = vault_url

        def get_secret(self, name):
            requested["name"] = name
            return SimpleNamespace(value="chave-do-kv")

    import azure.identity
    import azure.keyvault.secrets

    monkeypatch.setattr(azure.keyvault.secrets, "SecretClient", FakeClient)
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", lambda: object())
    monkeypatch.setenv("KEY_VAULT_URL", "https://quantra-kv.vault.azure.net/")

    assert config.get_api_key() == "chave-do-kv"
    assert requested["name"] == "AZURE-OPENAI-API-KEY"
    assert requested["vault_url"] == "https://quantra-kv.vault.azure.net/"


def test_key_vault_takes_precedence_over_env_key(monkeypatch):
    class FakeClient:
        def __init__(self, vault_url, credential):
            pass

        def get_secret(self, name):
            return SimpleNamespace(value="do-kv")

    import azure.identity
    import azure.keyvault.secrets

    monkeypatch.setattr(azure.keyvault.secrets, "SecretClient", FakeClient)
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", lambda: object())
    monkeypatch.setenv("KEY_VAULT_URL", "https://quantra-kv.vault.azure.net/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "do-env")

    assert config.get_api_key() == "do-kv"


def test_missing_key_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="Chave não encontrada"):
        config.get_api_key()


def test_missing_settings_lists_what_is_absent(monkeypatch):
    monkeypatch.setenv("KEY_VAULT_URL", "https://quantra-kv.vault.azure.net/")
    missing = config.missing_settings()
    assert "AZURE_OPENAI_ENDPOINT" in missing
    assert "AZURE_OPENAI_DEPLOYMENT" in missing
    assert not any("KEY_VAULT_URL" in m for m in missing)


def test_is_configured_true_when_everything_set(monkeypatch):
    monkeypatch.setenv("KEY_VAULT_URL", "https://quantra-kv.vault.azure.net/")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt")
    assert config.is_configured()
