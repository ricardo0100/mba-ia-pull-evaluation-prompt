# Proposal

## Why

O `src/evaluate.py` só avalia `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2` e sempre o puxa do LangSmith Hub, mas o `src/push_prompts.py` ainda é só um esqueleto. Sem o push não dá para rodar nenhuma avaliação: nem a linha de base (o conteúdo da v1 publicado como v2, para registrar as notas iniciais), nem as iterações do prompt otimizado.

## What Changes

- Implementar `src/push_prompts.py`, que:
  - lê `prompts/bug_to_user_story_v2.yml` (caminho ancorado na raiz do repositório);
  - valida o prompt antes de publicar, separando **erros**, que bloqueiam o push, de **avisos**, que não bloqueiam. Ter menos de 2 técnicas em `techniques_applied` é só aviso, para que a linha de base possa ser publicada;
  - monta um `ChatPromptTemplate` com as mensagens de sistema e de usuário;
  - faz push **público** para `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2` com descrição, tags e técnicas utilizadas;
  - termina com código 0 ou 1 e imprime a URL do prompt publicado.
- Adicionar `tests/test_push_prompts.py` com testes offline da validação e da montagem do template.
- `src/utils.py`, `src/evaluate.py` e `tests/test_prompts.py` não mudam.

## Capabilities

### New Capabilities
- `prompt-push`: publicar um prompt local em YAML no LangSmith Prompt Hub, com validação prévia e metadados, para que o `evaluate.py` possa avaliá-lo.

### Modified Capabilities
_Nenhuma._ A spec `prompt-pull` não muda.

## Impact

- **Código:** `src/push_prompts.py` (implementação) e `tests/test_push_prompts.py` (novo).
- **Sistemas externos:** cria ou atualiza o prompt público `{handle}/bug_to_user_story_v2` no LangSmith Hub. Cada push com conteúdo novo gera um commit no prompt.
- **Configuração:** usa `LANGSMITH_API_KEY` e `USERNAME_LANGSMITH_HUB`, que já estão no `.env.example`.
- **Fluxo:** para a linha de base, o usuário copia o conteúdo da v1 para `prompts/bug_to_user_story_v2.yml` com a chave raiz `bug_to_user_story_v2`. O push mostra um aviso de técnicas e publica mesmo assim.
