"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

HUB_PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
LOCAL_PROMPT_KEY = "bug_to_user_story_v1"

# Ancorado na raiz do repositório para funcionar fora dela também
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{LOCAL_PROMPT_KEY}.yml"


def prompt_to_dict(prompt: ChatPromptTemplate) -> dict:
    """
    Converte o ChatPromptTemplate do Hub no formato YAML usado pelo projeto.

    Args:
        prompt: Prompt retornado pelo LangSmith Hub

    Returns:
        Dicionário com a chave raiz do prompt e seus campos
    """
    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        if isinstance(message, SystemMessagePromptTemplate):
            system_prompt = message.prompt.template
        elif isinstance(message, HumanMessagePromptTemplate):
            user_prompt = message.prompt.template

    return {
        LOCAL_PROMPT_KEY: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": "v1",
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }


def _represent_multiline_str(dumper: yaml.Dumper, data: str):
    """Grava strings multilinha em bloco literal (|) em vez de aspas com \\n."""
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def pull_prompts_from_langsmith() -> bool:
    """
    Faz pull do prompt semente do LangSmith Hub e salva em prompts/.

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        print(f"Puxando prompt do LangSmith Hub: {HUB_PROMPT_NAME}")
        client = Client()
        prompt = client.pull_prompt(HUB_PROMPT_NAME, dangerously_pull_public_prompt=True)
        print("   ✓ Prompt carregado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt '{HUB_PROMPT_NAME}': {e}")
        return False

    data = prompt_to_dict(prompt)

    yaml.add_representer(str, _represent_multiline_str)
    if not save_yaml(data, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ Prompt salvo em {OUTPUT_PATH}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    return 0 if pull_prompts_from_langsmith() else 1


if __name__ == "__main__":
    sys.exit(main())
