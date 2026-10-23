# Design

## Context

Veja proposal.md (seção Why) para a motivação. As restrições que influenciam a abordagem são:

- `src/utils.py` é marcado como "não alterar" no README, mas já oferece `save_yaml`, `check_env_vars` e `print_section_header`, que o esqueleto importa.
- Os scripts são rodados como `python src/pull_prompts.py`, e o `from utils import ...` depende de `src/` estar no `sys.path`. Isso acontece automaticamente porque `src/` é o diretório do script.
- `client.pull_prompt(...)` retorna um `ChatPromptTemplate`. Cada item de `prompt.messages` é um `SystemMessagePromptTemplate`, um `HumanMessagePromptTemplate` etc., e o texto do template fica em `.prompt.template`.
- O `prompts/bug_to_user_story_v1.yml` atual mostra o formato esperado: chave raiz com `description`, `system_prompt`, `user_prompt`, `version`, `created_at` e `tags`.

## Goals / Non-Goals

**Goals:**
- Script executável que cumpre a spec `prompt-pull`.
- Lógica de conversão testável sem rede e sem credenciais.

**Non-Goals:**
- Pull genérico de vários prompts ou via argumentos de linha de comando. O README pede apenas o prompt semente.
- Preservar os comentários do YAML existente.
- Usar metadados do Hub (descrição e tags do commit) para preencher o YAML.

## Decisions

### 1. Separar em três funções: `prompt_to_dict`, `pull_prompts_from_langsmith` e `main`
- `prompt_to_dict(prompt: ChatPromptTemplate) -> dict` é pura: recebe o template e devolve `{"bug_to_user_story_v1": {...}}`.
- `pull_prompts_from_langsmith()` cria o `Client`, faz o pull, chama `prompt_to_dict` e grava com `save_yaml`. Retorna `True` ou `False`.
- `main()` imprime o cabeçalho, roda `check_env_vars(["LANGSMITH_API_KEY"])` e converte o resultado em código de saída 0 ou 1.

**Por quê:** mantém os nomes do esqueleto (`pull_prompts_from_langsmith`, `main`) e isola a parte testável. A alternativa de deixar tudo em uma função só exigiria mockar o `Client` para testar o mapeamento.

### 2. Mapear o papel da mensagem por `isinstance`
Usar `SystemMessagePromptTemplate` e `HumanMessagePromptTemplate` de `langchain_core.prompts`. Mensagens de outros tipos são ignoradas, e um papel ausente vira `""`.

**Alternativa descartada:** usar a posição (`messages[0]` como system, `messages[1]` como user). Isso quebra se o Hub devolver outra ordem ou só uma mensagem.

### 3. Metadados fixos no código
`description: "Prompt para converter relatos de bugs em User Stories"`, `version: "v1"` e `tags: ["bug-analysis", "user-story", "product-management"]`, copiados do YAML atual. O campo `created_at` é removido.

**Por quê:** o Hub não expõe esses campos de forma uniforme pelo `pull_prompt`, e o arquivo v1 só serve de referência para a v2. A alternativa de chamar `client.get_prompt(...)` para pegar a descrição adiciona uma chamada de rede e mais um ponto de falha sem ganho para o desafio.

### 4. Caminho de saída ancorado na raiz do repositório
`Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"`.

**Por quê:** o script funciona mesmo rodado fora da raiz. O `evaluate.py` usa caminhos relativos ao diretório atual, mas não há motivo para repetir essa fragilidade aqui.

### 5. Strings multilinha em estilo literal (`|`)
Antes de chamar `save_yaml`, registrar um representer local do PyYAML que emite strings com `\n` em estilo bloco literal. Fazer isso dentro do próprio `pull_prompts.py`, sem tocar em `utils.py`.

**Por quê:** sem isso, o `yaml.dump` grava o system prompt como uma string entre aspas com `\n` escapados, o que dificulta a leitura e a comparação com a v2. O efeito vale só para o processo do script.

### 6. Testes em `tests/test_pull_prompts.py`
Os testes montam um `ChatPromptTemplate` local e verificam o `prompt_to_dict`: mapeamento por papel, ordem invertida, ausência de user, `{bug_report}` preservado e chaves obrigatórias. Usam o mesmo truque de `sys.path` de `tests/test_prompts.py`.

**Por quê:** `tests/test_prompts.py` é reservado aos 6 testes da v2 pedidos no README.

## Risks / Trade-offs

- **[Risco] Os comentários do topo do v1.yml são perdidos ao sobrescrever.** → Aceito: o pull deve refletir o Hub. O texto dos comentários continua no histórico do git e no README.
- **[Risco] O representer global do PyYAML afeta outros `yaml.dump` no mesmo processo.** → O script não faz outros dumps. O registro fica dentro do módulo e só é aplicado ao rodar o script.
- **[Risco] O prompt semente no Hub pode mudar ou sumir.** → O erro de pull é tratado com mensagem e código 1, e o arquivo versionado continua no repositório.
- **[Trade-off] Nome e destino do prompt fixos no código.** → É o que o README pede. Generalizar fica para quando houver um segundo prompt.
