# Tasks

## 1. Leitura, validação e montagem (offline)

- [x] 1.1 Em `src/push_prompts.py`, definir `PROMPT_KEY = "bug_to_user_story_v2"` e `INPUT_PATH` ancorado na raiz, e implementar `load_prompt_data(path)`, que usa `load_yaml`, extrai a chave raiz e, quando ela falta, imprime as chaves encontradas e retorna `None`. Verificação: os testes de `load_prompt_data` em `tests/test_push_prompts.py` (chave correta, chave `bug_to_user_story_v1`, arquivo inexistente, via `tmp_path`) passam.
- [x] 1.2 Implementar `build_prompt_template(prompt_data)` (sistema e, se `user_prompt` não estiver vazio, usuário) e `build_tags(prompt_data)` (`tags + techniques_applied`, sem duplicatas e mantendo a ordem). Verificação: testes de template com e sem `user_prompt`, textos idênticos ao YAML e tags deduplicadas passam.
- [x] 1.3 Implementar `validate_prompt(prompt_data)`, que retorna só erros (campos obrigatórios, `system_prompt` vazio, `TODO` em `system_prompt`/`user_prompt`, `{bug_report}` ausente e variáveis diferentes de `bug_report` via `input_variables`), e `technique_warnings(prompt_data)` para menos de 2 técnicas. Verificação: testes para cada erro, vários erros juntos, prompt válido sem erros, aviso com 0 técnicas, nenhum aviso com 2 e `{{literal}}` sem falso positivo passam.

## 2. Push e CLI

- [x] 2.1 Implementar `push_prompt_to_langsmith(prompt_name, prompt_data)`: `Client().push_prompt(...)` com `object`, `is_public=True`, `description`, `tags`, `readme` (versão e técnicas) e `commit_description` (até 1000 caracteres). Tratar `LangSmithConflictError` como "sem mudanças" (imprime a URL e retorna `True`); qualquer outra exceção imprime o erro e a dica de `USERNAME_LANGSMITH_HUB` e retorna `False`. Verificação: teste com `Client` mockado (`monkeypatch`) confirma os argumentos enviados, o retorno `True` no conflito e `False` em erro genérico.
- [x] 2.2 Implementar `main()`: cabeçalho, `check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"])`, carga, validação (erros → código 1 sem push), avisos de técnicas, push e retorno 0 ou 1. Atualizar o docstring do módulo para descrever o comportamento real (avisos vs. erros). Verificação: `LANGSMITH_API_KEY= USERNAME_LANGSMITH_HUB= venv/bin/python src/push_prompts.py` lista as duas variáveis e sai com código 1.
- [x] 2.3 Rodar `venv/bin/python -m pytest tests/`. Verificação: `test_push_prompts.py` e `test_pull_prompts.py` passam.

## 3. Verificação integrada (linha de base)

- [x] 3.1 Com o `prompts/bug_to_user_story_v2.yml` atual (chave `bug_to_user_story_v1`), rodar `python src/push_prompts.py`. Verificação: sai com código 1, informa que a chave `bug_to_user_story_v2` não foi encontrada e lista `bug_to_user_story_v1`.
- [x] 3.2 Trocar a chave raiz para `bug_to_user_story_v2` e rodar `python src/push_prompts.py` com `.env` válido. Verificação: aparece o aviso de técnicas, o processo sai com código 0, imprime a URL, e o prompt aparece público no Hub com descrição e tags.
- [x] 3.3 Rodar o push de novo sem alterar o YAML. Verificação: sai com código 0 com a mensagem "sem mudanças". Se o servidor usar outra exceção, ajustar o `except` e o teste da 2.1.
- [x] 3.4 Rodar `cd /tmp && <repo>/venv/bin/python <repo>/src/push_prompts.py`. Verificação: lê `<repo>/prompts/bug_to_user_story_v2.yml` e sai com código 0 ("sem mudanças").

## Workflow follow-up

- Rodar `python src/evaluate.py` para registrar a linha de base (iteração 0) antes de escrever o prompt otimizado.
- Arquivar a change com `/opsx:archive` depois da revisão.
