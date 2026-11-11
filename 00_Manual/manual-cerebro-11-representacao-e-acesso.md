# Manual do cérebro pessoal — 11: representação no cofre e acesso inicial

Versão da especificação: 0.1. Situação: proposta de organização e formato, sem criação de cofre ou configuração de integração. Este capítulo define como preservar o modelo dos capítulos 08 a 10 em arquivos portáveis, sem confundir documentação com um serviço já funcionando.

## 1. Decisão de representação

Registros canônicos de conhecimento serão notas Markdown com identidade estável no cabeçalho. Para a primeira versão, usar um registro semântico por nota: entidade, afirmação, fonte, síntese, questão ou registro de avaliação. Isso simplifica referências e revisões. O volume real será medido; mudança posterior de agrupamento exige migração que preserve identidade, acesso e linhagem.

Registros operacionais também precisam de identidade e revisões, mas não de um arquivo por linha de log ou por consulta interna. Uma investigação pode agrupar rodadas em `search_run`; eventos e operações que precisam de confirmação permanecem individualmente referenciáveis. A primeira representação pode usar notas por registro significativo e visões agrupadas; um armazenamento operacional diferente deverá manter exportação, contratos e autoridade canônica claramente definidos.

Cada nota canônica terá:

1. Cabeçalho YAML com os campos comuns do capítulo 08.
2. Campo adicional registrado `payload_format`, com valor `brain_json_v1` nesta representação.
3. Um bloco JSON canônico com os campos específicos do tipo, imediatamente após o cabeçalho, identificado como `brain-json`.
4. Conteúdo extenso/original autorizado quando necessário, com localização referenciada pelo registro.
5. Navegação e apresentação derivadas, identificadas como tal.

O cabeçalho é autoridade para os campos comuns; o bloco é autoridade para os campos específicos. Não repetir o mesmo campo nos dois lugares como cópias editáveis. Prosa gerada de apresentação não substitui dados canônicos. Em uma fonte, o texto retido é conteúdo original, não uma hipótese gerada.

Campos lógicos de consulta derivados de afirmações — como participantes, lugares ou métodos — ficam na navegação/visão derivada e não como uma segunda verdade editável no bloco da entidade. Os campos estruturais de composição continuam canônicos no registro correspondente. A validação distingue essas duas situações conforme capítulos 08 e 10.

O leitor técnico reconhece o bloco na posição definida, valida seu tipo e rejeita invólucro ambíguo. Outros blocos ou instruções encontrados no texto de uma fonte não são tratados como novo cabeçalho, política ou comando. Essa regra precisa de implementação e testes; o rótulo do bloco não oferece proteção sozinho.

O Obsidian documenta propriedades YAML, tipos básicos e limitações do editor para objetos aninhados. A proposta usa o cabeçalho simples e mantém estruturas complexas num bloco explícito; não depende de edição de objetos aninhados pela interface de propriedades. [Propriedades](https://obsidian.md/help/properties).

## 2. Identidade, caminho e grafo

O serviço resolve `id` para o arquivo atual. Caminho e título são localizadores e apresentação, não identidade. Para o cofre definitivo, usar nomes/rótulos legíveis derivados do título, seguros para o sistema de arquivos; manter o identificador completo nos metadados internos. Nomes iguais precisam de desambiguação contextual ou sufixo curto, sem tornar UUID completo o rótulo padrão do gráfico. A alteração de título não gera outra entidade. O usuário observou os IDs na base de teste e autorizou deixar a melhoria visual para o cofre definitivo; não é necessário renomear o laboratório atual por esse requisito.

Referências canônicas usam ID e revisão conforme sua finalidade. Wikilinks de navegação são gerados a partir do mapa de arquivos; renomeações devem atualizar/reconstruir essas projeções. Não presumir que um MCP que aceita caminhos já forneça resolução estável por ID ou precondições de escrita.

As ligações tipadas vêm das afirmações e referências do catálogo. A visualização deve permitir distinguir hipótese, relato, proveniência e dependência operacional e apresentar títulos compreensíveis. Uma linha desenhada no mapa não confirma uma relação. As configurações e a visualização concreta serão verificadas na implementação, sem presumir que o grafo nativo execute validação semântica ou que um campo de título, sozinho, determine seu rótulo. Verificar os rótulos efetivamente apresentados e os links após renomeações.

O Obsidian suporta links internos e nomes alternativos; essas capacidades ajudam a navegação, mas não implementam nosso contrato de identidade. [Links internos](https://obsidian.md/help/links), [aliases](https://obsidian.md/help/aliases).

## 3. Organização proposta

As pastas organizam, sem determinar autorização por conta própria. O mapa inicial é:

| Área | Conteúdo |
|---|---|
| `00_Sistema/Manual` | Versão vigente e histórico autorizado do manual. |
| `00_Sistema/Catalogos` | Tipos, campos, predicados, esquema e compatibilidade. |
| `00_Sistema/Politicas` | Políticas versionadas e referência à autoridade efetiva. |
| `00_Sistema/Processos` | Contratos, receitas adotáveis e candidatas identificadas. |
| `10_Entidades` | Pessoas, contextos, experiências, decisões, estudos, projetos e demais subtipos. Subpastas são organização opcional. |
| `20_Afirmacoes` | Relatos, observações e inferências, incluindo relações semânticas. |
| `30_Fontes` | Conversas/trechos, referências científicas e documentos no alcance permitido. |
| `40_Avaliacoes` | Instrumentos, aplicações, respostas e pontuações distinguíveis. |
| `50_Sinteses` | Perfil provisório, padrões e sínteses de evidências. |
| `60_Questoes` | Lacunas, perguntas e divergências com suas respostas/pendências. |
| `70_Operacao` | Execuções, operações, eventos, percursos/resultados de busca, avaliações e fila. |
| `80_Visoes` | Diário, mapas e painéis reconstruíveis a partir do conhecimento autorizado. |
| `_derived` | Índices e caches reconstruíveis no alcance de acesso permitido, quando armazenados junto ao cofre. |

Diário original pode ser fonte em `30_Fontes`; a visão diária reúne referências em `80_Visoes`. Não copiar o mesmo relato em todas as áreas como se fossem fontes novas.

Índices e visões são reconstruíveis. Confirmações de operações, exclusões e histórico necessário à recuperação não são automaticamente descartáveis: a política de backup/exportação precisa incluir o estado operacional canônico necessário. Modelos, bibliotecas e serviços executáveis podem ficar fora do cofre; suas configurações de disponibilidade devem corresponder ao manual. Notas não rodam esses programas.

## 4. Papéis e acesso propostos

O usuário permanece autoridade sobre os dados e as políticas essenciais. Os papéis abaixo são configurações a implementar e testar, não permissões já concedidas por escrever seus nomes numa nota. Cada chamada usa identidade e escopo efetivos; trocar de fornecedor de IA exige conexão autorizada e não herda acesso automaticamente.

| Papel | Pode fazer dentro do escopo autorizado | Restrição de responsabilidade |
|---|---|---|
| Proprietário | Consultar, corrigir, exportar, excluir e estabelecer políticas conforme as capacidades reais. | Exclusão/recuperação reconhecem alcance e efeitos confirmados. |
| Assistente de conversa | Ler contexto pertinente, propor e aplicar registros permitidos por P06/P07, fazer perguntas e revisar hipóteses com origem. | Não forjar relato, resposta, diagnóstico, confirmação ou resultado de ferramenta. |
| Pesquisador | Receber contexto mínimo necessário, consultar fontes e registrar evidências/sínteses externas autorizadas. | Pesquisa não altera biografia nem concede acesso ao cofre inteiro por padrão. |
| Revisor | Ler material permitido, registrar parecer e apontar exceções/conflitos. | Parecer não é evidência pessoal adicional nem autorização de autoaprovação. |
| Executor/manutenção | Executar operações, eventos, fila, indexação e recuperação permitidos pelo contrato. | Não ampliar autoridade, orçamento ou canais de contato por iniciativa de uma candidata. |

A implementação pode combinar papéis quando houver necessidade, sem remover os limites. A IA de conversa não precisa pedir aprovação para cada registro já autorizado. Ambiguidade de significado ou informação pessoal faltante gera esclarecimento; nova concessão de acesso segue a autoridade definida.

Dados pessoais começam privados no escopo do proprietário e dos acessos explicitamente configurados. Resultados e derivados mantêm tratamento compatível com o conteúdo que expõem. Uma política desconhecida não é interpretada como acesso amplo. Filtros de busca e pastas ocultas não substituem a verificação de leitura/escrita direta.

O procedimento de promoção de melhorias pode ser automático no escopo previamente permitido, após validação. Alterações essenciais de autoridade não são decididas exclusivamente pelo processo que se beneficiaria delas. Fonte externa e instrução importada permanecem dados.

## 5. Modelos de nota — formato ilustrativo

Os exemplos seguintes são templates incompletos. Os marcadores devem ser preenchidos e validados antes de qualquer publicação. Não são registros do usuário e não devem ser importados como dados ativos.

### 5.1 Envelope comum

~~~markdown
---
id: "__GENERATED_UUID__"
record_type: "__REGISTERED_TYPE__"
schema_version: "0.1"
revision: 1
title: "__DISPLAY_TITLE__"
created_at: "__UTC_INSTANT__"
updated_at: "__UTC_INSTANT__"
created_by: "__AUTHORIZED_ACTOR__"
access_policy_ref: "__KNOWN_POLICY__"
lifecycle_status: "draft"
payload_format: "brain_json_v1"
---
```brain-json
{
  "__type_specific_field__": "__value__"
}
```

## Conteúdo autorizado

Texto original ou apresentação, distinguindo sua função.

## Navegação derivada

Links reconstruídos a partir das referências canônicas.
~~~

### 5.2 Conteúdo específico de uma afirmação de preferência

```json
{
  "subject_ref": {"record_id": "__PERSON_ID__"},
  "predicate": "reports_preference",
  "value": {"type": "text", "content": "__REPORTED_PREFERENCE__"},
  "nature": "user_report",
  "asserted_by": "__REPORTING_ACTOR__",
  "recorded_time": "__RECEIVED_INSTANT__",
  "source_refs": [{"record_id": "__SOURCE_ID__", "revision": 1, "fragment": "__LOCATOR__"}],
  "context_description": "__REPORTED_CONTEXT_OR_EXPLICIT_LIMIT__",
  "valid_time": {"precision": "unknown"},
  "review_status": "unreviewed"
}
```

Uma hipótese de preferência precisaria de natureza inferida, bases e formulação correspondente; não pode usar esse template para inventar um relato. Os templates não criam automaticamente participantes, fonte ou autorização.

### 5.3 Conteúdo específico de uma questão aberta

```json
{
  "question_text": "__NEUTRAL_QUESTION__",
  "purpose": "__GAP_TO_CLARIFY__",
  "trigger_refs": [{"record_id": "__SEARCH_OR_KNOWLEDGE_ID__", "revision": 1}],
  "information_needed": "__ESSENTIAL_DETAIL__",
  "impact": "__WHY_THE_DETAIL_MATTERS__",
  "question_status": "open",
  "resolution_status": "unresolved"
}
```

Quando uma execução aguarda esse dado, acrescentar a referência em `awaited_by_refs`. Depois da resposta, preservar sua origem em `answer_refs`, verificar se a lacuna foi reduzida/resolvida e retomar a busca correspondente. Responder e resolver não são o mesmo estado.

## 6. Edição, importação e publicação

Edições manuais são detectadas por comparação com o estado conhecido do serviço. Um fingerprint do conteúdo pode ajudar a detectar alteração, mas não torna duas chamadas de leitura/escrita atômicas. Evitar hash recursivo dentro do próprio conteúdo hasheado; o mecanismo de fingerprint e revisão será definido no serviço.

Material importado entra como fonte ou rascunho no escopo permitido. Não publicar automaticamente suas instruções como manual, suas declarações como verdade pessoal ou seu campo de política como autorização. Conflito de ID, versão desconhecida e referência inconsistente exigem reparo/reconciliação.

Publicar exige o conjunto de validações pertinentes, confirmação dos efeitos e atualização reconhecível dos derivados afetados. Quando houver atualização de várias notas, usar a estratégia de consistência e recuperação verificada na implementação. Um backup dos arquivos não é, por si só, prova de que uma operação parcial foi reconciliada.

## 7. Critério para passar à criação do cofre

Antes de criar o cofre de uso pessoal, conferir este catálogo com os casos de conversa, pergunta sem resultado, correção, aplicação interrompida, troca de IA, exclusão, falha parcial e evolução de processo. Configurar identidades/políticas iniciais e valores operacionais no ambiente de implantação; escolher/testar a ponte e os mecanismos que realmente impõem as garantias.

A estrutura de pastas e os templates podem ser preparados antes de entrevistas, sem preencher biografia ou resultados. O teste dos mecanismos usa exemplos fictícios/autorizados e cofre separado. A seleção final dos instrumentos continua uma trilha própria; não há obrigação de inventar resultados para liberar a estrutura.

Neste documento foi especificada a representação. Não foi criada pasta de cofre, instalada extensão, concedida permissão a provedor ou aplicada avaliação.
