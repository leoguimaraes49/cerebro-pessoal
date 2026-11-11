# Manual do cérebro pessoal — 09: registros operacionais

Versão da especificação: 0.1. Situação: contratos de dados propostos, sem executor ou armazenamento implementado. Usa o núcleo, as referências e as convenções O/C/F do capítulo 08. Não muda os estados do capítulo 03 nem cria automaticamente agentes, agendamentos ou acesso a modelos.

## 1. Catálogo e fronteiras

| `record_type` | Responsabilidade |
|---|---|
| `process_definition` | Contrato versionado de um processo ou combinação adotável. |
| `policy_definition` | Descrição versionada de uma política, com autoridade e alcance identificados. |
| `execution` | Uma execução concreta sob contrato, dados, acesso e limites conhecidos. |
| `operation` | Intenção, tentativas e efeitos de uma alteração ou chamada que precisa de reconciliação. |
| `change_event` | Alteração confirmada e sinalização de impacto sobre referências e derivados. |
| `index_checkpoint` | Cobertura verificável de um índice/partição em relação à base autorizada. |
| `search_run` | Percurso observável de uma investigação, sem raciocínio interno privado. |
| `search_result` | Resultado reutilizável condicionado à validade atual. |
| `search_recipe` | Estratégia versionada de investigação, sem herdar conclusões de execuções anteriores. |
| `work_item` | Entrada de fila ligada à execução responsável, sem segundo estado de execução concorrente. |
| `evaluation` | Plano e resultado de avaliação de uma candidata, separados de sua promoção. |

Um processo de pesquisa externa usa `execution`, fontes e `synthesis` de pesquisa. Uma análise do perfil usa execução e síntese pertinentes. Não criar uma família nova apenas porque a tarefa recebeu outro nome. O formato físico poderá agrupar logs e visões sem exigir um arquivo visível por chamada.

## 2. Definição e autoridade

**Processo.** O: `process_key`, finalidade, gatilhos, contrato de entrada/saída, pré-condições, efeitos permitidos, caminhos de chamada, parada, falhas, limites exigidos e critérios de verificação. C: dependências de ferramentas, versões compatíveis e avaliação quando candidato à adoção. `adoption_status`: `candidate`, `under_evaluation`, `adopted`, `retired`. Publicar uma descrição não instala capacidade executável.

**Política.** O: finalidade, alcance, versão, referência à autoridade que a estabeleceu e situação de adoção. C: política anterior, mudança autorizada e efeitos sobre acessos/execuções. A configuração de autoridade é validada fora do controle da candidata avaliada. Uma nota arbitrária não se torna permissão por declarar `adopted` ou apontar para si mesma.

A leitura de versões para uma execução não dispensa a verificação de revogações e exclusões atuais. Contrato estável e acesso vigente são verificações distintas.

## 3. Execução e fila

| Campo de `execution` | Regra |
|---|---|
| `process_ref` | O. Contrato/revisão adotados ou contexto de avaliação isolado explicitamente permitido. |
| `request_context` | O. Objetivo e origem autorizada; referências quando houver material persistido. |
| `root_execution_id`, `parent_execution_ref` | Raiz O; pai C para trabalho filho. A raiz pode identificar a própria execução. Encadeamento não renova orçamento. |
| `execution_status` | O. Os estados do capítulo 03, com a representação técnica mapeada abaixo. |
| `responsible_actor` | O. Responsável ativo ou regra explícita de transferência; não executar a mesma escrita por dois responsáveis sem coordenação. |
| `authorization_ref`, `input_refs` | O no alcance necessário; bases de cálculo e alteração apontam às revisões consultadas. |
| `budget_ref`, `budget_usage` | O para iniciar; envelope e consumo vinculados à raiz, incluindo trabalho descendente. |
| `dependency_refs`, `wait_condition` | C quando houver dependência ou espera. Identificar a condição de retorno. |
| `checkpoint_refs`, `operation_refs` | C quando houver progresso persistido ou efeitos a reconciliar. |
| `result_refs`, `completion_quality` | C ao concluir; resultado também pode ser limitação permitida pelo contrato. |
| `failure_details`, `cancellation_details` | C quando aplicáveis; registrar efeitos confirmados e incertos. |

Mapeamento de `execution_status`: registrada → `registered`; na fila → `queued`; em execução → `running`; aguardando → `waiting`; suspensa → `suspended`; cancelando → `cancelling`; concluída → `completed`; falhou → `failed`; cancelada → `cancelled`. Transições são as do capítulo 03. `lifecycle_status` continua descrevendo o registro armazenado, sem substituir esse estado.

`completion_quality`: `sufficient`, `limited`, `conflicting`, `inconclusive` ou `not_applicable`. Cumprir o contrato de uma busca com resultado inconclusivo não comprova uma hipótese nem atinge automaticamente o objetivo amplo.

O orçamento identifica tetos configurados de passos, duração, chamadas, profundidade, tentativas e custo/esforço pertinente. Não há valor universal ideal fixado por este catálogo. Limite obrigatório ausente impede iniciar a rotina autônoma dependente dele; não significa ilimitado.

**Fila (`work_item`).** O: `execution_ref`, motivo, prioridade, política de elegibilidade e origem. F/C: `not_before`, condição de retorno, chave de agrupamento, interessados e metadados de reserva/transferência. A situação operacional vem da execução, não de outro campo contraditório. Cancelar um interessado não cancela trabalho que ainda serve aos demais. Reservas, expiração e justiça de fila terão implementação própria, sem novas chamadas de IA para cada transição.

## 4. Operação e reconciliação de efeitos

| Campo de `operation` | Regra |
|---|---|
| `execution_ref`, `operation_key` | O. Identidade definida antes da primeira tentativa; repetição usa a mesma identidade para o mesmo pedido. |
| `intent`, `request_fingerprint` | O. Conteúdo pretendido e representação verificável do pedido; mesma chave com conteúdo diferente é conflito. |
| `target_refs`, `expected_revisions` | C para alteração de existentes. Criação exige condição de inexistência/identidade apropriada. |
| `authorization_ref` | O. Autorização aplicável e alcance efetivo. |
| `effect_status` | O. `proposed`, `sent`, `confirmed`, `partially_confirmed`, `unknown`, `rejected` ou `compensated`. |
| `attempts` | C ao enviar. Ferramenta/modo/versão pertinente, momento, pedido correlacionável e retorno observado. Sem credenciais. |
| `confirmed_effects` | C ao confirmar. Alvos, revisões/efeitos reconhecidos e evidência de confirmação adequada ao contrato. |
| `pending_effects`, `reconciliation_refs` | C para aplicação parcial, efeito incerto ou recuperação. |

Texto convincente não preenche `confirmed_effects`. Perda de resposta pode deixar efeito desconhecido; antes de repetir, conferir o que ocorreu. Trocar de ponte não autoriza repetir uma escrita incerta. Uma tentativa repetida não deve criar novamente entidade, aresta ou evento.

Mudanças em várias notas precisam de estratégia explícita de atomicidade, reconciliação ou compensação. Confirmar uma nota não autoriza confirmar o conjunto. Comparar revisão e escrever depois em chamadas independentes não garante proteção contra concorrência; isso precisa ser imposto pela autoridade real de escrita, considerando edições manuais.

Compensação tem fonte, responsável e limites; não significa apagar eventos nem restaurar dados excluídos contra a política vigente. O registro não presume entrega exatamente uma vez por qualquer servidor MCP.

## 5. Evento de alteração e cobertura de índices

**Evento (`change_event`).** O: operação confirmada/origem de alteração externa reconhecida, `event_scope`, tipo, alvos e revisões pertinentes, momento, abrangência de impacto e sinalização de derivados. `event_scope`: `knowledge`, `operational`, `catalogue` ou `access`. Tipos iniciais: criação, atualização, correção, mudança temporal, fusão, separação, exclusão e alteração de política/esquema quando pertinentes. Alteração de conhecimento deve avançar uma geração identificável do escopo; não presumir que mudar um log operacional seja nova biografia.

`impact_status`: `bounded`, `requires_broader_revalidation` ou `pending`. A falta de dependência anterior não prova irrelevância: nota nova ou aresta nova pode mudar buscas antigas, inclusive buscas vazias. Se não for possível delimitar impacto com cobertura verificável, invalidar/revalidar um escopo mais amplo antes de usar resultados como atuais.

Confirmar a alteração precisa deixar reconhecível a necessidade de revalidação. Reindexação pesada pode ser assíncrona, mas a sinalização não pode depender apenas de uma fila opcional. A implementação deve coordenar confirmação e sinalização ou oferecer mecanismo conservador de recuperação; não afirmar essa garantia apenas por escrever o evento no manual.

**Cobertura (`index_checkpoint`).** O: tipo de índice, versão/configuração relevante, escopo autorizado, geração da base coberta, momento, `coverage_status` e lacunas conhecidas. `coverage_status`: `complete_for_scope`, `partial`, `rebuilding`, `unavailable`. Para vetor, identificar modelo/configuração de embeddings e compatibilidade de espaço; para grafo, a versão de relações e o alcance reconstruído. Lacuna não é coberta só porque a maior geração observada é recente.

Um checkpoint é metadado de cobertura que precisa corresponder ao índice real, não evidência pessoal. O sistema identifica diferença entre base confirmada e índices; pode consultar fonte atual por outro caminho permitido, aguardar ou declarar limitação. Não usar resultado conhecido como superado enquanto a indexação está atrasada.

## 6. Busca realizada, resultado e receita

### 6.1 Percurso: `search_run`

O: execução responsável, objetivo/questão, contexto da tarefa, escopo e política aplicados, contratos/ferramentas usados, cobertura consultada, operações observadas, referências recuperadas e motivo de encerramento/pausa. C: relações percorridas, tentativas improdutivas, lacunas, conflitos e limites atingidos. F: medidas de tempo, chamadas e custo quando disponíveis.

O percurso registra consulta, filtros, ferramenta, referências e justificativas verificáveis de encaminhamento. Não pede raciocínio interno privado. Uma investigação pode conter várias rodadas no mesmo registro; não precisa criar um novo processo para cada consulta determinística.

Motivos previstos: evidência suficiente, falta de progresso, informação pessoal faltante, limite de recursos, indisponibilidade, acesso insuficiente ou cancelamento. “Não encontrei no escopo e cobertura disponíveis” não é “isso não existe”. Pedir resposta mantém a dependência de execução em espera quando essencial.

`question_refs` é obrigatório quando o avanço depender de esclarecimento pessoal. A questão referencia a busca/rodada que motivou a dúvida; suas `answer_refs` fornecem a nova entrada. Quando a resposta chegar, revalidar acesso, versões e limite e retomar a parte afetada, distinguindo pergunta respondida de lacuna efetivamente resolvida. Se a execução ainda estiver aguardando, registrar a nova rodada sem duplicar o percurso anterior. Se ela já tiver terminado, uma nova execução pode usar `continuation_of_ref` para referenciar a busca anterior, sem reabrir silenciosamente um estado terminal ou renovar orçamento por conta própria.

Uma rodada sem resultados deixa o registro operacional necessário no alcance autorizado e pode originar pergunta, busca adaptativa ou pesquisa externa conforme a lacuna. Falha de ferramenta não é falta de informação pessoal; informação restrita não é sugerida na pergunta para contornar acesso. Não perguntar automaticamente por todo retorno vazio quando a contribuição já permitir a operação ou quando outra recuperação disponível resolver o ponto.

### 6.2 Resultado reutilizável: `search_result`

O: busca de origem; representação do pedido/contexto atendido; fontes/revisões efetivamente usadas; escopo e política; versões relevantes e cobertura; conteúdo ou referências do resultado; limitações; `validation_status`; data e condições de revalidação. `validation_status`: `pending`, `valid`, `stale`, `invalid`. `stale` indica necessidade de nova verificação, não prova de falsidade de todo conteúdo.

Compatibilidade do pedido inclui finalidade, período e condições pertinentes, não apenas palavras próximas. Novas notas, relações, exclusões, correções e mudanças de acesso podem exigir revisão mesmo sem edição nas fontes antigas. O relógio também pode importar em pedidos sobre o estado atual; fontes externas exigem política de atualização, pois sua mudança pode não gerar evento local.

Prazo de validade e chave de cache não comprovam validade semântica. Antes de entregar, validar autorização atual e cobertura necessária. Se o impacto é delimitável, atualizar o trecho; caso contrário, ampliar a recuperação. Preservar acesso ao material completo necessário e às exceções. Trocar apenas o modelo que conversa não cria evidência independente; incompatibilidade técnica real de representação deve ser tratada explicitamente.

### 6.3 Receita: `search_recipe`

O: finalidade, situações compatíveis, entradas, sequência permitida, saídas, parada, dependências, limites compartilhados e estado de adoção. C: avaliações e versão anterior ao promover. A receita inclui saída para descoberta normal/adaptativa e para novidades fora do percurso antigo. Não contém uma conclusão pessoal fixa como resposta obrigatória.

Busca lexical/vetorial pode localizar uma receita candidata. Similaridade não aprova sua aplicação. Frequência de uso não basta para adotá-la: medir qualidade, tempo e custo líquido, incluindo localizar, validar, registrar e manter a memória. Uma otimização que perde correções não é aceita só por economizar tokens.

## 7. Pesquisa externa e avaliação de melhorias

Pesquisa externa é execução de P11. Registros necessários: questão, contexto mínimo autorizado, estratégia e período de busca, fontes consultadas, disponibilidade, desenho/população pertinente, resultados, limitações, divergências e aplicabilidade. Guardar como fontes e síntese de pesquisa; seleção e exclusão de estudos relevantes devem ser explicáveis, sem inventar revisão sistemática que não ocorreu. Artigo populacional não preenche um acontecimento pessoal ausente.

**Avaliação (`evaluation`).** O: candidata e revisão, versão de referência quando houver, finalidade, critérios definidos antes da avaliação, cenários/dados de avaliação, estado e evidências dos resultados. `evaluation_status`: `planned`, `running`, `completed`, `interrupted`. C ao concluir: resultados por critério, regressões, limites e `verdict` (`pass`, `fail`, `inconclusive`). Opinião de uma IA avaliadora não é a única prova de funcionamento. Dados usados para ajustar uma candidata não substituem os casos independentes de avaliação.

Um parecer favorável torna a candidata elegível, sem executar a promoção por si. Adoção segue autoridade vigente, correspondência com capacidades reais, publicação coerente de manual/contratos e recuperação compatível. Candidata não altera os próprios critérios nem amplia permissões. Nenhuma avaliação deste capítulo foi executada.

## 8. Regras transversais e casos de aceitação

Histórico e resultados respeitam acesso/retenção das consultas, caminhos, títulos e conteúdo que revelem. Não salvar segredos em parâmetros ou retornos. Exclusão e restauração tratam derivados controlados e preservam apenas o que a política permitir. Registrar um log não é gatilho suficiente para reexecutar a busca que o gerou.

| Caso planejado | Tratamento exigido |
|---|---|
| Chave de operação reaparece com outro conteúdo | Rejeitar conflito; não interpretar como repetição válida. |
| Ferramenta aplicou, mas a resposta se perdeu | Marcar incerteza e reconciliar antes de repetir. |
| Duas de três mudanças são confirmadas | Registrar parcial; recuperar o restante ou compensar conforme contrato. |
| Contrato da execução é estável e acesso é revogado | Impedir novas entregas/efeitos fora do acesso vigente. |
| Nota nova contraditória ainda sem arestas | Busca não depende só das revisões antigas; descoberta por texto/significado e cobertura. |
| Índice está atrás da correção confirmada | Revalidar por caminho atual, aguardar ou declarar limitação. |
| Cache foi gerado com acesso maior | Não vazar conteúdo, caminhos ou títulos por reutilização. |
| Receita popular deixa de recuperar exceções | Falhar na qualidade/reavaliar; popularidade não compensa a perda. |
| Filho cria outro filho para continuar pesquisa | Todos permanecem no limite da raiz; não há orçamento novo implícito. |
| Registro de busca gera evento operacional | Não tratar como experiência nova nem disparar ciclo de autorregistro. |

Os casos são requisitos futuros, não testes passados. Mecanismos de confirmação, concorrência, fila, indexação, orçamento e recuperação dependem da implementação escolhida e serão verificados no ambiente real.
