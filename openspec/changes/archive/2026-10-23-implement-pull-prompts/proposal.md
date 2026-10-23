# Proposal

## Why

O `src/pull_prompts.py` é só um esqueleto (`...`), mas o README define o pull como o primeiro requisito do desafio: trazer o prompt semente `leonanluppi/bug_to_user_story_v1` do LangSmith Prompt Hub para o ambiente local, para que ele sirva de base à otimização da v2.

## What Changes

- Implementar `src/pull_prompts.py` para:
  - validar as credenciais do LangSmith no `.env` antes de qualquer chamada de rede;
  - fazer pull de `leonanluppi/bug_to_user_story_v1` com `dangerously_pull_public_prompt=True`;
  - extrair o template do system prompt e do user prompt do `ChatPromptTemplate` retornado;
  - gravar o resultado em `prompts/bug_to_user_story_v1.yml`, no mesmo formato do arquivo que já existe (chave raiz `bug_to_user_story_v1` com `description`, `system_prompt`, `user_prompt`, `version`, `tags`);
  - imprimir o progresso e terminar com código 0 em caso de sucesso e 1 em caso de falha.
- Separar a conversão "prompt do Hub → dicionário YAML" em uma função pura, testável sem rede.
- Adicionar testes unitários dessa conversão em `tests/test_pull_prompts.py`.

## Capabilities

### New Capabilities
- `prompt-pull`: baixar um prompt do LangSmith Prompt Hub e persisti-lo localmente como YAML no formato usado pelo projeto.

### Modified Capabilities
<!-- Nenhuma: não há specs existentes em openspec/specs/. -->

## Impact

- **Código:** `src/pull_prompts.py` (implementação) e `tests/test_pull_prompts.py` (novo).
- **Arquivo gerado:** `prompts/bug_to_user_story_v1.yml` é sobrescrito. Os comentários explicativos no topo do arquivo atual se perdem, porque o `save_yaml` não preserva comentários.
- **Dependências:** nenhuma nova. Usa `langsmith`, `langchain-core`, `python-dotenv` e `pyyaml`, que já estão em `requirements.txt`, e reaproveita `save_yaml`, `check_env_vars` e `print_section_header` de `src/utils.py`.
- **Ambiente:** exige `LANGSMITH_API_KEY` no `.env` e acesso de rede ao LangSmith.
- **Arquivos que não mudam:** `src/evaluate.py`, `src/metrics.py`, `src/utils.py` e o dataset, que o README marca como "não alterar".
