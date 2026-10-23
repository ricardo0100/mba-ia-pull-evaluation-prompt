# Spec Delta

## Purpose

Trazer prompts publicados no LangSmith Prompt Hub para o repositório como arquivos YAML locais, que servem de ponto de partida para a otimização e o versionamento dos prompts.

## ADDED Requirements

### Requirement: Validar credenciais antes do pull
O script de pull SHALL verificar se `LANGSMITH_API_KEY` está definida no ambiente antes de qualquer chamada ao LangSmith. Se ela não estiver definida, o script MUST informar a variável faltante e terminar com código de saída 1, sem fazer chamadas de rede.

#### Scenario: Chave do LangSmith ausente
- **WHEN** o script é executado sem `LANGSMITH_API_KEY` no ambiente ou no `.env`
- **THEN** a saída lista `LANGSMITH_API_KEY` como variável faltante
- **AND** o processo termina com código 1
- **AND** nenhum arquivo em `prompts/` é criado ou alterado

### Requirement: Baixar o prompt semente do desafio
O script de pull SHALL buscar o prompt `leonanluppi/bug_to_user_story_v1` no LangSmith Prompt Hub, aceitando explicitamente o pull de um prompt público com dono identificado (`owner/nome`).

#### Scenario: Pull bem-sucedido
- **WHEN** o script é executado com credenciais válidas e o prompt existe no Hub
- **THEN** o prompt `leonanluppi/bug_to_user_story_v1` é obtido do Hub
- **AND** a saída informa o nome do prompt baixado

#### Scenario: Falha ao acessar o Hub
- **WHEN** o pull falha (credencial inválida, prompt inexistente ou erro de rede)
- **THEN** a saída mostra uma mensagem de erro com o motivo
- **AND** o processo termina com código 1
- **AND** o arquivo local existente não é alterado

### Requirement: Persistir o prompt como YAML local
O script de pull SHALL gravar o prompt em `prompts/bug_to_user_story_v1.yml` sob a chave raiz `bug_to_user_story_v1`, contendo `description`, `system_prompt`, `user_prompt`, `version` e `tags`. Os templates MUST manter as variáveis (ex.: `{bug_report}`) exatamente como vieram do Hub.

#### Scenario: Arquivo gerado com a estrutura esperada
- **WHEN** o pull termina com sucesso
- **THEN** `prompts/bug_to_user_story_v1.yml` existe e pode ser lido como YAML
- **AND** contém a chave raiz `bug_to_user_story_v1` com os campos `description`, `system_prompt`, `user_prompt`, `version` e `tags`
- **AND** `system_prompt` e `user_prompt` são o texto do template de sistema e do template de usuário do prompt baixado, com `{bug_report}` preservado
- **AND** o processo termina com código 0

#### Scenario: Arquivo já existente
- **WHEN** `prompts/bug_to_user_story_v1.yml` já existe e o pull termina com sucesso
- **THEN** o arquivo é sobrescrito com o conteúdo atual do Hub

#### Scenario: Execução fora da raiz do repositório
- **WHEN** o script é executado a partir de um diretório diferente da raiz do repositório
- **THEN** o arquivo é gravado em `prompts/bug_to_user_story_v1.yml` relativo à raiz do repositório, e não ao diretório atual

### Requirement: Mapear mensagens do prompt por papel
A conversão do prompt SHALL associar a mensagem de sistema a `system_prompt` e a mensagem de usuário a `user_prompt`. Quando o prompt não tiver uma delas, o campo correspondente MUST ser uma string vazia.

#### Scenario: Prompt com sistema e usuário
- **WHEN** o prompt baixado tem uma mensagem de sistema e uma de usuário
- **THEN** cada template vai para o campo do seu papel, independentemente da ordem das mensagens

#### Scenario: Prompt sem mensagem de usuário
- **WHEN** o prompt baixado tem apenas a mensagem de sistema
- **THEN** `system_prompt` recebe o template de sistema
- **AND** `user_prompt` é uma string vazia
