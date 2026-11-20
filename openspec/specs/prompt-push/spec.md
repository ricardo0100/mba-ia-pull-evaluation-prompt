# prompt-push Specification

## Purpose

Publicar o prompt local em YAML (`prompts/bug_to_user_story_v2.yml`) no LangSmith Prompt Hub como prompt público versionado, com validação prévia e metadados, para que a avaliação automática possa puxá-lo e medi-lo.

## Requirements

### Requirement: Validar credenciais e handle antes do push
O script de push SHALL verificar se `LANGSMITH_API_KEY` e `USERNAME_LANGSMITH_HUB` estão definidas antes de qualquer chamada ao LangSmith. Se alguma faltar, o script MUST listar as variáveis faltantes e terminar com código 1, sem chamadas de rede.

#### Scenario: Variável obrigatória ausente
- **WHEN** o script é executado sem `LANGSMITH_API_KEY` ou sem `USERNAME_LANGSMITH_HUB`
- **THEN** a saída lista cada variável faltante
- **AND** o processo termina com código 1
- **AND** nenhum prompt é publicado

### Requirement: Ler o prompt otimizado do YAML local
O script SHALL ler `prompts/bug_to_user_story_v2.yml`, relativo à raiz do repositório e não ao diretório atual, e usar os dados sob a chave raiz `bug_to_user_story_v2`. Se o arquivo não existir, não for YAML válido ou não tiver essa chave, o script MUST informar o motivo e terminar com código 1, sem publicar.

#### Scenario: Arquivo lido a partir de outro diretório
- **WHEN** o script é executado de um diretório diferente da raiz do repositório
- **THEN** ele lê `<raiz>/prompts/bug_to_user_story_v2.yml`

#### Scenario: Arquivo ausente ou inválido
- **WHEN** `prompts/bug_to_user_story_v2.yml` não existe ou não pode ser lido como YAML
- **THEN** a saída mostra o erro
- **AND** o processo termina com código 1 sem publicar

#### Scenario: Chave raiz incorreta
- **WHEN** o YAML não tem a chave raiz `bug_to_user_story_v2` (por exemplo, uma cópia da v1 que manteve `bug_to_user_story_v1`)
- **THEN** a saída informa que a chave `bug_to_user_story_v2` não foi encontrada e lista as chaves presentes
- **AND** o processo termina com código 1 sem publicar

### Requirement: Bloquear o push quando houver erros de estrutura
Antes do push, o script SHALL validar o prompt e MUST recusar a publicação, listando todos os erros e saindo com código 1, quando: faltar `description`, `system_prompt` ou `version`; `system_prompt` estiver vazio; o texto contiver `TODO`; `{bug_report}` não aparecer em nenhuma mensagem; ou houver variável de template diferente de `bug_report`.

#### Scenario: System prompt vazio
- **WHEN** `system_prompt` está ausente ou só tem espaços
- **THEN** a saída lista o erro
- **AND** o processo termina com código 1 sem publicar

#### Scenario: TODO esquecido
- **WHEN** `system_prompt` ou `user_prompt` contém `TODO`
- **THEN** a saída lista o erro e o processo termina com código 1 sem publicar

#### Scenario: Variável de entrada ausente
- **WHEN** nem `system_prompt` nem `user_prompt` contêm `{bug_report}`
- **THEN** a saída informa que `{bug_report}` é obrigatória e o processo termina com código 1 sem publicar

#### Scenario: Variável desconhecida
- **WHEN** o template usa uma variável diferente de `bug_report` (ex.: `{contexto}`)
- **THEN** a saída nomeia a variável desconhecida e o processo termina com código 1 sem publicar

#### Scenario: Vários erros ao mesmo tempo
- **WHEN** o prompt tem mais de um erro de estrutura
- **THEN** a saída lista todos eles numa única execução

### Requirement: Avisar sem bloquear quando faltarem técnicas
O script SHALL emitir um aviso, e MUST continuar com o push, quando `techniques_applied` estiver ausente ou tiver menos de 2 itens. Isso permite publicar a linha de base (conteúdo da v1) para medir as notas iniciais.

#### Scenario: Linha de base sem técnicas
- **WHEN** o YAML é estruturalmente válido mas não tem `techniques_applied`
- **THEN** a saída mostra um aviso dizendo que o mínimo de 2 técnicas não foi atingido
- **AND** o prompt é publicado normalmente

#### Scenario: Prompt com técnicas suficientes
- **WHEN** `techniques_applied` tem 2 ou mais itens
- **THEN** nenhum aviso de técnicas é exibido

### Requirement: Montar o prompt com mensagens de sistema e de usuário
O prompt publicado SHALL ter uma mensagem de sistema com o texto de `system_prompt` e, quando `user_prompt` não estiver vazio, uma mensagem de usuário com o texto de `user_prompt`, nessa ordem e sem alterar os textos ou as variáveis.

#### Scenario: Sistema e usuário presentes
- **WHEN** o YAML tem `system_prompt` e `user_prompt` preenchidos
- **THEN** o prompt publicado tem a mensagem de sistema seguida da de usuário, com os textos idênticos aos do YAML

#### Scenario: User prompt vazio
- **WHEN** `user_prompt` está ausente ou vazio e `system_prompt` contém `{bug_report}`
- **THEN** o prompt publicado tem apenas a mensagem de sistema

### Requirement: Publicar como prompt público com metadados
O script SHALL publicar em `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2` como prompt **público**, usando `description` do YAML como descrição e, como tags, as `tags` do YAML mais as `techniques_applied`, sem duplicatas. Ao concluir, MUST imprimir a URL do prompt e terminar com código 0.

#### Scenario: Push bem-sucedido
- **WHEN** o prompt é válido e o Hub aceita o push
- **THEN** o prompt `{handle}/bug_to_user_story_v2` fica público no Hub com a descrição e as tags do YAML e as técnicas aplicadas
- **AND** a saída mostra a URL do prompt
- **AND** o processo termina com código 0

#### Scenario: Conteúdo idêntico ao último commit
- **WHEN** o prompt publicado no Hub já é igual ao do YAML
- **THEN** a saída informa que não havia mudanças para publicar
- **AND** o processo termina com código 0

#### Scenario: Falha ao publicar
- **WHEN** o Hub recusa o push (credencial inválida, handle inexistente, erro de rede)
- **THEN** a saída mostra o motivo do erro e lembra de conferir `USERNAME_LANGSMITH_HUB`
- **AND** o processo termina com código 1
