# Tasks

## 1. Conversão do prompt para dicionário

- [x] 1.1 Implementar `prompt_to_dict(prompt)` em `src/pull_prompts.py`: mapear por `isinstance` (`SystemMessagePromptTemplate` → `system_prompt`, `HumanMessagePromptTemplate` → `user_prompt`, papel ausente → `""`) e devolver `{"bug_to_user_story_v1": {description, system_prompt, user_prompt, version, tags}}` com os metadados fixos do design. Verificação: `python -c "import sys; sys.path.insert(0,'src'); import pull_prompts"` importa sem erro.
- [x] 1.2 Criar `tests/test_pull_prompts.py` com testes para: sistema e usuário mapeados, ordem invertida, prompt só com sistema (`user_prompt == ""`), `{bug_report}` preservado e presença das chaves obrigatórias. Verificação: `pytest tests/test_pull_prompts.py` passa.

## 2. Pull e gravação

- [x] 2.1 Implementar `pull_prompts_from_langsmith()`: chamar `Client().pull_prompt("leonanluppi/bug_to_user_story_v1", dangerously_pull_public_prompt=True)`, converter com `prompt_to_dict`, registrar o representer de string literal multilinha e gravar com `save_yaml` em `<raiz>/prompts/bug_to_user_story_v1.yml`. Em caso de exceção, imprimir o erro e retornar `False` sem gravar nada. Verificação: revisão do código conforme a spec (os cenários "Pull bem-sucedido" e "Falha ao acessar o Hub").
- [x] 2.2 Implementar `main()`: `print_section_header`, `check_env_vars(["LANGSMITH_API_KEY"])`, chamada ao pull e retorno 0 ou 1. Verificação: `LANGSMITH_API_KEY= python src/pull_prompts.py` lista a variável faltante, sai com código 1 e `git status prompts/` não mostra alterações.

## 3. Verificação integrada

- [x] 3.1 Rodar `python src/pull_prompts.py` a partir da raiz, com `.env` válido. Verificação: sai com código 0; `prompts/bug_to_user_story_v1.yml` tem a chave `bug_to_user_story_v1` com os 5 campos; `system_prompt` aparece em bloco `|` e contém `{bug_report}`.
- [x] 3.2 Rodar `cd /tmp && python <repo>/src/pull_prompts.py`. Verificação: o arquivo é gravado em `<repo>/prompts/` e não em `/tmp/prompts/`.
- [x] 3.3 Rodar `pytest tests/` para confirmar que nada quebrou. Verificação: `tests/test_pull_prompts.py` passa (os testes de `test_prompts.py` ainda são `pass` e também passam).
