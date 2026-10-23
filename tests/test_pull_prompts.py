"""
Testes da conversão de prompts do LangSmith Hub para o formato YAML local.
"""
import pytest
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.prompts import ChatPromptTemplate
from pull_prompts import prompt_to_dict, LOCAL_PROMPT_KEY

SYSTEM_TEMPLATE = "Você é um assistente.\n\nRelato:\n{bug_report}"
USER_TEMPLATE = "{bug_report}"


class TestPromptToDict:
    def test_maps_system_and_user(self):
        """Cada template vai para o campo do seu papel."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_TEMPLATE),
            ("user", USER_TEMPLATE),
        ])
        data = prompt_to_dict(prompt)[LOCAL_PROMPT_KEY]

        assert data["system_prompt"] == SYSTEM_TEMPLATE
        assert data["user_prompt"] == USER_TEMPLATE

    def test_maps_by_role_not_order(self):
        """A ordem das mensagens não altera o mapeamento."""
        prompt = ChatPromptTemplate.from_messages([
            ("user", USER_TEMPLATE),
            ("system", SYSTEM_TEMPLATE),
        ])
        data = prompt_to_dict(prompt)[LOCAL_PROMPT_KEY]

        assert data["system_prompt"] == SYSTEM_TEMPLATE
        assert data["user_prompt"] == USER_TEMPLATE

    def test_missing_user_message(self):
        """Sem mensagem de usuário, user_prompt é string vazia."""
        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_TEMPLATE)])
        data = prompt_to_dict(prompt)[LOCAL_PROMPT_KEY]

        assert data["system_prompt"] == SYSTEM_TEMPLATE
        assert data["user_prompt"] == ""

    def test_preserves_template_variables(self):
        """A variável {bug_report} é mantida literalmente."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_TEMPLATE),
            ("user", USER_TEMPLATE),
        ])
        data = prompt_to_dict(prompt)[LOCAL_PROMPT_KEY]

        assert "{bug_report}" in data["system_prompt"]
        assert "{bug_report}" in data["user_prompt"]

    def test_has_required_fields(self):
        """O resultado tem a chave raiz e todos os campos obrigatórios."""
        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_TEMPLATE)])
        result = prompt_to_dict(prompt)

        assert list(result.keys()) == [LOCAL_PROMPT_KEY]
        for field in ["description", "system_prompt", "user_prompt", "version", "tags"]:
            assert field in result[LOCAL_PROMPT_KEY]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
