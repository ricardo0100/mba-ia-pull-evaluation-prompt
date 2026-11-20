# Design

## Context

Veja proposal.md (seção Why) para a motivação e specs/prompt-push/spec.md para os requisitos. As restrições que influenciam a abordagem são:

- `src/utils.py` não pode ser alterado (README). Ele oferece `load_yaml`, `check_env_vars`, `print_section_header` e `validate_prompt_structure`. Este último trata "menos de 2 técnicas" como erro, e isso conflita com a decisão de só avisar.
- `src/evaluate.py` puxa `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2` com `client.pull_prompt(...)` e invoca o template com `{"bug_report": ...}`. Qualquer outra variável no template quebra a avaliação.
- `Client.push_prompt` (langsmith 0.13.0) cria o prompt ou atualiza os metadados (`is_public`, `description`, `readme`, `tags`) e depois chama `create_commit` com o objeto. Se o manifesto for idêntico ao último commit, o servidor responde com conflito ("Nothing to commit").
- O `src/pull_prompts.py` já usa o padrão de funções pequenas e testáveis, com o caminho ancorado em `Path(__file__).resolve().parent.parent`. O push segue o mesmo padrão.
- O `prompts/bug_to_user_story_v2.yml` atual é uma cópia da v1, ainda com a chave `bug_to_user_story_v1`.

## Goals / Non-Goals

**Goals:**
- Script executável que cumpre a spec `prompt-push`.
- Validação e montagem do template testáveis sem rede.

**Non-Goals:**
- Push de vários prompts, nomes por argumento de CLI ou flag `--baseline`.
- Converter automaticamente a chave `bug_to_user_story_v1` em `v2`. O usuário edita o YAML.
- Mudar o `evaluate.py` ou o `utils.py`.

## Decisions

### 1. Funções: `load_prompt_data`, `validate_prompt`, `build_prompt_template`, `build_tags`, `push_prompt_to_langsmith`, `main`
- `load_prompt_data(path) -> dict | None`: usa `load_yaml` e extrai a chave `bug_to_user_story_v2`. Se ela não existir, imprime as chaves encontradas e retorna `None`.
- `validate_prompt(prompt_data) -> tuple[bool, list]`: mantém a assinatura do esqueleto e retorna apenas **erros**.
- `technique_warnings(prompt_data) -> list[str]`: retorna os avisos de técnicas, separados dos erros.
- `build_prompt_template(prompt_data) -> ChatPromptTemplate`: `("system", system_prompt)` e, se houver, `("user", user_prompt)`.
- `build_tags(prompt_data) -> list[str]`: `tags + techniques_applied`, sem duplicatas e mantendo a ordem.
- `push_prompt_to_langsmith(prompt_name, prompt_data) -> bool`: o nome é o do esqueleto e é a única função com rede.
- `main()`: checa as variáveis de ambiente, carrega, valida, mostra os avisos, faz o push e devolve 0 ou 1.

**Por quê:** mantém os nomes do esqueleto (`push_prompt_to_langsmith`, `validate_prompt`, `main`) e isola tudo o que é testável. A alternativa de concentrar a lógica em `main` obrigaria a mockar o `Client` para testar a validação.

### 2. Validação própria em vez de `validate_prompt_structure`
`validate_prompt` reimplementa as checagens de campos, `system_prompt` vazio e `TODO`, e acrescenta três: `TODO` também no `user_prompt`, `{bug_report}` presente e nenhuma variável além de `bug_report`. As variáveis são lidas de `build_prompt_template(...).input_variables`, a mesma análise que o LangChain faz em tempo de execução. Assim, chaves literais escapadas (`{{ }}`) não viram falsos positivos.

**Alternativa descartada:** chamar `validate_prompt_structure` e filtrar o erro de técnicas pelo texto da mensagem. Funciona, mas depende de uma string que pode mudar e não cobre as checagens de variáveis.

### 3. Técnicas viram aviso
Se `len(techniques_applied) < 2`, o script imprime `⚠️` e segue com o push (decisão do usuário, para permitir a linha de base). O requisito de 2 técnicas do README continua garantido pelo `test_minimum_techniques` em `tests/test_prompts.py`, que roda sobre o YAML final.

### 4. Metadados no push
- `is_public=True`.
- `description`: o `description` do YAML.
- `tags`: o resultado de `build_tags`. As técnicas aparecem como tags no Hub.
- `readme`: um markdown curto com a versão e a lista de técnicas aplicadas (ou "nenhuma", na linha de base).
- `commit_description`: `f"{version}: {', '.join(techniques) or 'sem técnicas (linha de base)'}"`, truncado em 1000 caracteres. Isso deixa cada iteração identificável no histórico de commits do prompt.

**Por quê:** o README pede "tags, descrição, técnicas utilizadas". Tags e readme deixam as técnicas visíveis na página do prompt, e a descrição do commit as deixa visíveis por versão.

### 5. Push sem mudanças é sucesso
Capturar `langsmith.utils.LangSmithConflictError` em volta do `push_prompt` e tratar como "nenhuma mudança no template". Nesse caso, o script imprime a URL do prompt no Hub (`https://smith.langchain.com/hub/{identificador}`, montada a partir do identificador para não depender de método privado do `Client`) e retorna `True`. Os metadados já foram atualizados antes do commit, então a mudança de tags ou descrição é aplicada mesmo assim. Qualquer outra exceção imprime o erro e a dica sobre `USERNAME_LANGSMITH_HUB` e retorna `False`.

**Alternativa descartada:** comparar com `pull_prompt` antes do push. Custa uma chamada extra e duplica a lógica do servidor.

### 6. Caminho ancorado na raiz
`INPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"`, como no pull.

### 7. Testes em `tests/test_push_prompts.py`
São offline e montam dicionários de prompt em memória. Cobrem: prompt válido sem erros, cada erro de estrutura, vários erros juntos, aviso de técnicas (com 0 e com 2 técnicas), template com e sem mensagem de usuário, textos preservados, `build_tags` sem duplicatas e `load_prompt_data` com chave errada (usando `tmp_path`). O `tests/test_prompts.py` fica reservado aos 6 testes do README.

## Risks / Trade-offs

- **[Risco] O servidor pode sinalizar "sem mudanças" com outro tipo de erro em vez de `LangSmithConflictError`.** → A tarefa de verificação integrada roda o push duas vezes seguidas e confirma o comportamento. Se for outra exceção, o `except` é ajustado.
- **[Risco] O handle não existe ou é de outra pessoa.** → Nesse caso o push falha com erro de permissão ou 404. A mensagem de erro lembra de conferir `USERNAME_LANGSMITH_HUB` e a seção "Handle do LangSmith Hub" do README.
- **[Trade-off] As técnicas não bloqueiam o push.** → Permite publicar uma v2 entregue sem técnicas. Isso é mitigado pelo aviso visível e pelo `test_minimum_techniques`.
- **[Trade-off] As checagens de `validate_prompt_structure` ficam duplicadas.** → Aceito, porque o `utils.py` não pode mudar e as regras são poucas.

## Migration Plan

Para a linha de base, troque a chave raiz de `prompts/bug_to_user_story_v2.yml` (hoje uma cópia da v1) para `bug_to_user_story_v2`, rode `python src/push_prompts.py` e depois `python src/evaluate.py`. Em seguida, escreva o prompt otimizado no mesmo arquivo e repita o push e a avaliação a cada iteração. Para voltar atrás, basta publicar de novo uma versão anterior do YAML, porque o Hub guarda o histórico de commits.
