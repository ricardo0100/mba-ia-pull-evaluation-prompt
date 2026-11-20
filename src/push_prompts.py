"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê o prompt de prompts/bug_to_user_story_v2.yml (chave raiz bug_to_user_story_v2)
2. Valida o prompt:
   - ERROS bloqueiam o push: campos obrigatórios faltando, system_prompt vazio,
     TODO no texto, {bug_report} ausente ou variáveis diferentes de bug_report
   - AVISOS não bloqueiam: menos de 2 técnicas em techniques_applied (permite
     publicar a linha de base, com o conteúdo da v1, para medir as notas iniciais)
3. Faz push PÚBLICO para {USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2
4. Adiciona metadados: descrição, tags (tags + técnicas), readme e descrição do commit

Uso:
    python src/push_prompts.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langsmith.utils import LangSmithConflictError
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
INPUT_VARIABLE = "bug_report"
REQUIRED_FIELDS = ["description", "system_prompt", "version"]
MIN_TECHNIQUES = 2
MAX_COMMIT_DESCRIPTION = 1000

# Ancorado na raiz do repositório para funcionar fora dela também
INPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def load_prompt_data(path: Path = INPUT_PATH) -> dict | None:
    """
    Lê o YAML e devolve os dados sob a chave raiz PROMPT_KEY.

    Returns:
        Dicionário do prompt ou None se o arquivo/chave for inválido
    """
    data = load_yaml(str(path))
    if data is None:
        return None

    if not isinstance(data, dict) or PROMPT_KEY not in data:
        found = list(data.keys()) if isinstance(data, dict) else []
        print(f"❌ Chave raiz '{PROMPT_KEY}' não encontrada em {path}")
        print(f"   Chaves encontradas: {', '.join(found) if found else '(nenhuma)'}")
        return None

    prompt_data = data[PROMPT_KEY]
    if not isinstance(prompt_data, dict):
        print(f"❌ O conteúdo de '{PROMPT_KEY}' deve ser um mapeamento YAML")
        return None

    return prompt_data


def _text(prompt_data: dict, field: str) -> str:
    value = prompt_data.get(field)
    return value if isinstance(value, str) else ""


def build_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o template: mensagem de sistema e, se houver, mensagem de usuário."""
    messages = [("system", _text(prompt_data, "system_prompt"))]
    user_prompt = _text(prompt_data, "user_prompt")
    if user_prompt.strip():
        messages.append(("user", user_prompt))
    return ChatPromptTemplate.from_messages(messages)


def _techniques(prompt_data: dict) -> list[str]:
    techniques = prompt_data.get("techniques_applied") or []
    return [str(t) for t in techniques] if isinstance(techniques, list) else []


def build_tags(prompt_data: dict) -> list[str]:
    """Tags do YAML + técnicas aplicadas, sem duplicatas e mantendo a ordem."""
    tags = prompt_data.get("tags") or []
    tags = [str(t) for t in tags] if isinstance(tags, list) else []
    return list(dict.fromkeys(tags + _techniques(prompt_data)))


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida a estrutura do prompt. Retorna apenas ERROS (que bloqueiam o push).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in prompt_data:
            errors.append(f"Campo obrigatório faltando: {field}")

    system_prompt = _text(prompt_data, "system_prompt")
    user_prompt = _text(prompt_data, "user_prompt")

    if not system_prompt.strip():
        errors.append("system_prompt está vazio")

    for field, text in (("system_prompt", system_prompt), ("user_prompt", user_prompt)):
        if "TODO" in text:
            errors.append(f"{field} ainda contém TODOs")

    try:
        variables = set(build_prompt_template(prompt_data).input_variables)
    except Exception as e:
        errors.append(f"Template inválido: {e}")
    else:
        if INPUT_VARIABLE not in variables:
            errors.append(
                f"A variável {{{INPUT_VARIABLE}}} é obrigatória "
                "(em system_prompt ou user_prompt)"
            )
        unknown = sorted(variables - {INPUT_VARIABLE})
        if unknown:
            errors.append(
                "Variáveis desconhecidas no template: "
                + ", ".join(f"{{{v}}}" for v in unknown)
                + f" (apenas {{{INPUT_VARIABLE}}} é suportada)"
            )

    return (len(errors) == 0, errors)


def technique_warnings(prompt_data: dict) -> list[str]:
    """Avisos que não bloqueiam o push (ex.: menos de 2 técnicas)."""
    count = len(_techniques(prompt_data))
    if count < MIN_TECHNIQUES:
        return [
            f"Mínimo de {MIN_TECHNIQUES} técnicas em techniques_applied não atingido "
            f"(encontradas: {count}). O push continua (ex.: linha de base)."
        ]
    return []


def _build_readme(prompt_data: dict) -> str:
    techniques = _techniques(prompt_data)
    lines = [
        f"# {PROMPT_KEY}",
        "",
        _text(prompt_data, "description"),
        "",
        f"**Versão:** {prompt_data.get('version', '')}",
        "",
        "## Técnicas aplicadas",
        "",
    ]
    lines += [f"- {t}" for t in techniques] if techniques else ["- nenhuma (linha de base)"]
    return "\n".join(lines) + "\n"


def _build_commit_description(prompt_data: dict) -> str:
    techniques = ", ".join(_techniques(prompt_data)) or "sem técnicas (linha de base)"
    return f"{prompt_data.get('version', '')}: {techniques}"[:MAX_COMMIT_DESCRIPTION]


def _hub_url(prompt_name: str) -> str:
    return f"https://smith.langchain.com/hub/{prompt_name}"


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"Publicando prompt no LangSmith Hub: {prompt_name}")
    try:
        client = Client()
        url = client.push_prompt(
            prompt_name,
            object=build_prompt_template(prompt_data),
            is_public=True,
            description=_text(prompt_data, "description"),
            readme=_build_readme(prompt_data),
            tags=build_tags(prompt_data),
            commit_description=_build_commit_description(prompt_data),
        )
    except LangSmithConflictError:
        print("   ✓ Nenhuma mudança no template desde o último commit (metadados atualizados)")
        print(f"   URL: {_hub_url(prompt_name)}")
        return True
    except Exception as e:
        print(f"❌ Erro ao fazer push do prompt '{prompt_name}': {e}")
        print("   Confira se USERNAME_LANGSMITH_HUB no .env é o seu handle do Hub")
        print("   (veja a seção 'Handle do LangSmith Hub' no README).")
        return False

    print("   ✓ Prompt publicado com sucesso (público)")
    print(f"   URL: {url}")
    return True


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    prompt_data = load_prompt_data(INPUT_PATH)
    if prompt_data is None:
        return 1

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido, push cancelado:")
        for error in errors:
            print(f"   - {error}")
        return 1

    for warning in technique_warnings(prompt_data):
        print(f"⚠️  {warning}")

    prompt_name = f"{username}/{PROMPT_KEY}"
    return 0 if push_prompt_to_langsmith(prompt_name, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
