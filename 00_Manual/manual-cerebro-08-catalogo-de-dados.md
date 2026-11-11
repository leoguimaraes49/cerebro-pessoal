# Manual do cérebro pessoal — 08: catálogo de dados e campos

Versão do documento: 0.2; esquema lógico proposto: 0.1. Situação: proposta concreta do modelo inicial; não há registros pessoais preenchidos, cofre criado ou validador implementado. Complementa os capítulos 06 e 07 e fixa o vocabulário inicial para representação e validação. Alterações posteriores seguem evolução de esquema e compatibilidade.

## 1. Convenções e campos comuns

Nesta versão, campos técnicos usam inglês em `snake_case`; títulos e conteúdo podem estar em português. A notação abaixo é lógica, não uma promessa de que objetos complexos sejam editáveis no painel de propriedades do Obsidian.

**O** significa obrigatório para publicar um registro ativo; **C** significa obrigatório quando a condição indicada existir; **F** significa facultativo. Omissão de um campo não significa zero, falso ou ausência da condição pessoal. Um rascunho incompleto pode ser retido no fluxo autorizado, mas não tratado como registro ativo validado.

| Campo comum | Tipo | Regra |
|---|---|---|
| `id` | Identificador | O. UUID v4 gerado pelo serviço; nunca derivado do nome, caminho ou diagnóstico. Imutável após criação. |
| `record_type` | Enumeração | O. Uma das famílias registradas neste capítulo ou no capítulo 09. |
| `schema_version` | Texto | O. Nesta proposta, `0.1`; a versão é do formato, não da pessoa. |
| `revision` | Inteiro positivo | O. Revisão controlada do registro; inicia em 1. Não é relógio clínico nem critério de verdade. |
| `title` | Texto | O. Nome de exibição, sem obrigação de revelar informação sensível no título. |
| `created_at`, `updated_at` | Instante | O. Datas técnicas com fuso explícito; a implementação normaliza para UTC. |
| `created_by` | Referência de ator | O. Identidade autorizada do autor técnico, resolvida na configuração ou no cadastro; pode ser diferente de quem relatou o conteúdo. |
| `access_policy_ref` | Referência de política | O. Política conhecida pelo executor. Escrever seu nome numa nota não concede acesso. |
| `lifecycle_status` | Enumeração | O. `draft`, `active`, `superseded` ou `archived`. São estados do registro, não da vida da pessoa nem da execução. |
| `superseded_by_refs` | Lista de referências | C. Quando a substituição tiver destinos conhecidos; a razão fica no evento de alteração. |
| `field_states` | Mapa de ausências | F/C. Para uma ausência material, usar `unknown`, `not_asked`, `not_applicable` ou `declined` com o campo correspondente. Não coexistir valor e ausência para o mesmo campo. |
| `payload_format` | Enumeração | C na representação Markdown do capítulo 11: `brain_json_v1`. Não é necessário em uma visão derivada que não seja registro canônico. |

Uma exclusão não é apenas trocar `lifecycle_status`: exige o procedimento de remoção e tratamento de derivados. Um marcador mínimo sem conteúdo poderá existir se a política permitir, sem preservar material que deveria ser excluído.

`field_states` representa lacunas de conteúdo, não substitui requisitos técnicos como identidade, versão, autorização ou confirmação de efeito. Quando um dado pessoal condicional é desconhecido, o registro pode explicitar a lacuna se o uso continuar válido; um cálculo que depende desse dado permanece inelegível ou limitado conforme sua regra.

### 1.1 Referências e tempo

`Ref` aponta à identidade atual: `record_id`, com localização opcional. `RevRef` aponta à base efetivamente utilizada: `record_id`, `revision` e, quando necessário, `fragment`. Toda derivação, cálculo, correção de conteúdo e operação dependente usa revisões identificáveis. Uma referência a uma versão indisponível é uma limitação, não autorização para fingir que a versão atual é a mesma fonte.

`TimeSpec` representa período ou ocorrência: precisão (`exact`, `approximate`, `interval`, `unknown`), limites conhecidos e descrição original quando útil. Informar apenas o ano não autoriza inventar dia e mês. O desconhecimento é representável; valores técnicos de gravação continuam separados das datas narradas.

Listas não exigem multiplicar registros: uma fonte pode servir a vários registros; uma entidade pode participar de várias experiências. Um identificador de operação reconhece tentativas repetidas e é distinto da identidade do conteúdo alterado.

## 2. Famílias canônicas

| `record_type` | Finalidade |
|---|---|
| `entity` | Algo identificável na vida ou no repertório: pessoa, experiência, decisão, conteúdo, projeto e demais subtipos. |
| `assertion` | Relato, observação, resultado ou inferência sobre sujeito, contexto e valor/alvo. Inclui relações semânticas. |
| `source` | Origem consultável ou referência a conteúdo recebido. |
| `synthesis` | Perfil, padrão sugerido ou síntese de pesquisa, com bases e limites. |
| `question` | Lacuna ou divergência que orienta esclarecimento. |
| `instrument` | Definição/versionamento de instrumento e condições de aplicação. |
| `assessment` | Uma aplicação individual, com estado e elegibilidade próprios. |
| `assessment_response` | Uma resposta atribuída a item e aplicação, com origem e revisão. |
| `assessment_score` | Resultado de cálculo identificado e reproduzível quando permitido. |

As famílias operacionais são definidas no capítulo 09. Um resultado de ação na vida real, um escore e um resultado de busca possuem sentidos diferentes; não compartilham um campo genérico que esconda a diferença.

## 3. Entidades e subtipos de domínio

Toda entidade possui `entity_kind` (O), `summary` (F), `origin_refs` (O, fontes ou bases da criação), `aliases` (F) e `identity_status` (O: `provisional`, `identified`, `ambiguous` ou `merged`). `identified` significa identidade resolvida para o uso da base, não comprovação externa de toda informação. Em `merged`, exigir destino e evento de fusão; preservar referências e acesso ao reconciliar. Casos incertos não são fundidos pela semelhança de nome.

Os campos abaixo se somam ao núcleo. Informações sobre pessoas, preferências e contextos, quando controversas ou derivadas, são afirmações referenciadas; não atributos soltos sem autoria.

| `entity_kind` | Campos específicos | Condições e fronteiras |
|---|---|---|
| `person` | `display_name` O; `identity_context` C quando houver ambiguidade. | Apelido pode ser o único nome conhecido. Não exigir documentos, endereço ou data de nascimento. Impressões ficam em afirmações. |
| `group`, `organization` | `display_name` O; `group_description` F. | Participantes e vínculo profissional/social são relações temporais atribuídas. |
| `place` | `display_name` O; `place_kind` F. | Precisão geográfica só quando relatada, necessária e autorizada. |
| `life_period` | `period_description` O; `time` O, admitindo desconhecido. | Um período como “época da faculdade” não precisa de datas exatas. |
| `experience` | `event_description`, `occurred_time` O; `context_refs`, `participant_refs`, `place_ref` F. | Componentes estruturais referenciam relações atribuídas; sentimentos e explicações são afirmações. |
| `decision` | `situation`, `perceived_options`, `decision_status` O; `chosen_option`, `decided_time` C quando decidida; objetivos, restrições e razões por referências F/C. | `decision_status`: `considering`, `decided`, `reconsidered` ou `withdrawn`. Escolha não é prova de execução. Não exigir que a pessoa lembre todas as opções. |
| `action` | `action_description`, `action_status` O; `decision_ref` F; `performed_time` C quando realizada. | `action_status`: `planned`, `in_progress`, `performed`, `abandoned`. Efeito real não é inferido de um plano. |
| `outcome` | `outcome_description`, `observation_kind`, `observed_time`, `source_refs` O; `action_ref`, `experience_ref`, `measurements` F. | `observation_kind`: `self_report`, `third_party_report` ou `documented_observation`. Medida exige unidade, método e origem. Não atribuir causalidade só pelo vínculo temporal. |
| `goal` | `desired_outcome`, `goal_status` O; `target_time`, `success_criteria`, `priority_context` F. | `goal_status`: `proposed`, `active`, `paused`, `achieved`, `abandoned`. “Alcançado” precisa de base identificada, não otimismo do modelo. |
| `project` | `purpose`, `project_status` O; objetivos, tarefas e entregas por referências F. | `project_status`: `planned`, `active`, `paused`, `completed`, `abandoned`. Conclusão referencia critérios e evidência. |
| `task` | `task_description`, `task_status` O; `project_ref`, `due_time`, `completion_criteria` F; `completion_refs` C quando concluída. | `task_status`: `planned`, `in_progress`, `blocked`, `completed`, `cancelled`. Não é o estado da execução técnica. |
| `habit` | `behavior_description`, `context_description`, `pattern_basis_refs` O; frequência relatada/observada e exceções F. | Hábito é padrão contextual. Uma ocorrência isolada não recebe frequência inventada. Pode permanecer hipótese. |
| `learning_topic` | `topic_description` O; objetivos, pré-requisitos e evidências por referências F. | “Sabe o assunto” precisa de afirmação e fonte; autoavaliação e desempenho demonstrado são distintos. |
| `study_method` | `method_description` O; `external_basis_refs`, `applicability_notes` F. | A popularidade do método não é evidência de eficácia individual. |
| `study_session` | `topic_refs`, `session_status` O; `method_refs`, `session_time`, `context_refs`, resultados por referências F/C. | `session_status`: `planned`, `held`, `interrupted`, `cancelled`; sessão realizada precisa de origem. |
| `idea`, `concept` | `content`, `idea_scope` O; `basis_refs` C quando derivada. | Valores, interesses e conceitos podem ser compartilhados; dizer que um valor é do usuário requer afirmação atribuída. Preferência simples pode ser apenas afirmação. |
| `recommendation` | `suggestion`, `purpose`, `personal_basis_refs`, `limitations`, `recommendation_status` O; `external_basis_refs` C se houver fundamentação externa alegada. | `recommendation_status`: `proposed`, `accepted`, `declined`, `superseded`. Propor não significa que a pessoa aceitou ou tentou. |
| `trial` | `recommendation_ref`, `trial_description`, `trial_status` O; condições, datas, ações e resultados por referências F/C. | `trial_status`: `planned`, `started`, `completed`, `stopped`. Ausência de retorno não é sucesso. |

Conteúdo de diário pode ser uma fonte ou uma visão de acontecimentos por dia. Se houver texto original do usuário, ele permanece fonte; agrupar referências na visão não cria observações adicionais. Pensamento ou emoção de um momento costuma ser afirmação contextual. Não é obrigatório criar uma entidade para cada frase.

Referências de participantes, lugar de um acontecimento, temas/métodos usados e demais vínculos semânticos da tabela são campos lógicos de consulta. Sua autoridade canônica está na afirmação relacional; a visão da entidade pode apresentá-los sem persistir uma segunda cópia editável no bloco canônico. Se uma projeção for materializada, ela identifica as afirmações de origem e é reconstruível. Referências que definem composição de registros — como aplicação/instrumento, resposta/item e tentativa/recomendação — são estruturais e têm a autoridade do próprio registro; não exigem uma cadeia infinita de afirmações sobre metadados.

Para dados clínicos relatados, usar fonte e afirmação com autoria e natureza adequadas. Não criar um subtipo de pessoa baseado num diagnóstico nem inferi-lo para completar uma entidade.

## 4. Afirmação e relação semântica

| Campo | Exigência |
|---|---|
| `subject_ref`, `predicate` | O. Sujeito existente e predicado registrado com tipos permitidos. |
| `object_ref` ou `value` | O. Exatamente um. `value` possui tipo explícito e unidade quando representa medida. |
| `nature` | O. `user_report`, `third_party_report`, `documented_observation`, `instrument_result` ou `inference`. |
| `asserted_by`, `recorded_time` | O. Quem afirmou e quando o relato/afirmação entrou; distinto da criação técnica. |
| `source_refs` | C. Fonte localizada para relato/observação/resultado. Pode coexistir com bases de interpretação. |
| `basis_refs` | C. Bases com revisões para uma inferência; não aceitar inferência sem base como fato pessoal. |
| `context_refs`, `context_description`, `valid_time` | O no que for material; o contexto ou tempo desconhecido é explícito, sem precisão fabricada. |
| `review_status` | O. `unreviewed`, `confirmed_by_user`, `disputed_by_user` ou `clarification_needed`. |
| `review_events` | C quando revisada. Responsável, momento, revisão examinada e alcance. |
| `opposing_refs`, `alternative_refs`, `dependency_refs` | F/C conforme forem conhecidas; uma contradição relevante não pode ser silenciosamente descartada. |
| `origin_group_refs`, `independence_status` | C ao sintetizar/contar evidências. `shared`, `distinct` ou `unknown`; distinguir repetição de origem, eventos e eventual corroboração por relatos diferentes. |

Confirmação do usuário não muda automaticamente a natureza, valida a pontuação ou produz diagnóstico. Uma relação sugerida por similaridade continua inferência e conserva a base. Relações estruturais derivadas para navegação são reconstruíveis a partir desses registros e não criam uma segunda fonte de verdade.

## 5. Fonte e síntese

**Fonte (`source`).** O: `source_kind`, `origin_description`, `received_at`, `availability_status` e `retention_conditions`. C: `author_refs` quando identificados, `parent_source_ref` para um turno, `content_locator` para conteúdo retido e `reference_locator` para referência externa. `source_kind`: `conversation`, `conversation_turn`, `document`, `publication`, `web_page`, `tool_output` ou `observation_record`. Citações identificam trecho/revisão. `availability_status`: `retained`, `reference_only`, `partially_available`, `unavailable`. Para publicação: `publication_title` e referência/localizador conhecido; `published_time`, `doi` e demais dados bibliográficos só se verificados. Capturar uma página hoje não inventa sua data de publicação. Conteúdo de terceiros só é preservado no alcance permitido.

**Síntese (`synthesis`).** O: `synthesis_kind`, `content`, `scope`, `basis_refs`, `limitations`, `coverage_status`, `as_of`; `exception_refs`, `opposing_refs`, `open_question_refs` são C quando conhecidos. `synthesis_kind`: `profile`, `behavior_pattern`, `research_summary` ou `knowledge_summary`. `coverage_status`: `provisional`, `supported_within_scope`, `limited`, `conflicting`, `needs_revalidation`. Esses rótulos descrevem suporte no escopo, não certeza objetiva ou diagnóstico. Perfil usa `assessed_dimensions` e `unassessed_areas`, distinguindo dimensões avaliadas de lacunas; não preenche uma personalidade completa por conveniência.

Síntese de pesquisa também referencia questão, período de busca, estudos, desenho, populações, resultados e limitações relevantes. Estudo populacional não se torna experiência pessoal. A mesma observação descrita por várias sínteses não aumenta o número de experiências.

## 6. Questão e aplicação de instrumento

**Questão (`question`).** O: `question_text`, `purpose`, `trigger_refs`, `information_needed`, `impact`, `question_status`, `resolution_status`. F: prioridade e contexto já conhecido. `question_status`: `open`, `awaiting_answer`, `answered`, `deferred`, `closed_without_answer`. `resolution_status`: `unresolved`, `partially_resolved`, `resolved`. Quando respondida, exigir `answer_refs`; resolução da lacuna é decisão distinta, com justificativa e base em `resolution_refs`. `awaited_by_refs` é C quando uma execução estiver aguardando esse dado. Gatilhos podem referenciar busca/rodada inconclusiva, e a resposta passa a integrar as entradas da retomada. O capítulo 07 continua definindo perguntas neutras, silêncio e dúvidas essenciais.

**Instrumento (`instrument`).** O antes de selecionar: `instrument_name`, `instrument_version`, `purpose`, `constructs`, `language`, `original_source_refs`, `target_population`, `age_scope`, `items_source_ref`, `instructions_source_ref`, `scoring_rule_ref`, `missing_response_rule`, `use_conditions`, `administration_modes` e `verification_status`. Autores e tradução usam `author_refs`/`translation_source_ref` quando identificados; evidências alegadas usam `validation_evidence_refs` e seus limites. `verification_status`: `pending_verification`, `verified_for_intended_scope` ou `not_suitable`. Um cadastro candidato pode estar incompleto em `draft`; isso não o seleciona. Itens não precisam ser copiados se a retenção não permitir. Tradução, autorização e evidências de validade possuem verificações separadas. Uma pendência não é preenchida com a frase genérica “validado cientificamente”.

**Aplicação (`assessment`).** O: `instrument_ref` com revisão, `subject_ref`, `purpose`, `application_status`, `conditions`, `scoring_eligibility` e `eligibility_reason`. Estados de aplicação: `not_started`, `in_progress`, `interrupted`, `completed`. Elegibilidade: `pending_verification`, `calculable`, `not_calculable`, segundo a regra referenciada. `conditions` registra idioma, modalidade, instruções efetivamente apresentadas e ajuda/adaptações relevantes; `started_at`, `ended_at`, pausas e desvios são C quando ocorridos/conhecidos. Concluir a aplicação não obriga produzir escore.

**Resposta (`assessment_response`).** O: `assessment_ref`, `item_ref`, `value` ou ausência explicitada, `source_refs` e revisão. `item_ref` identifica a revisão do instrumento e o localizador/chave do item, sem exigir uma entidade independente por pergunta. Não inferir resposta a partir da conversa geral nem alterar um item para combinar com o perfil. Retificação conserva procedência conforme retenção e exige reavaliar dependentes.

**Pontuação (`assessment_score`).** O: `assessment_ref`, `scoring_rule_ref`, `response_refs` com revisões, `dimension_scores`, `computed_at`, `limitations` e `score_validity_status` (`current`, `needs_revalidation`, `invalid`). `scoring_rule_ref` pode apontar à seção versionada da definição do instrumento. Normas/percentis usam `norms_ref` e comparação documentada quando adequadas; não inventar. Resultado não calculável pertence ao estado da aplicação e não é escore zero. A interpretação é uma síntese ou afirmação inferida, distinta do cálculo. Rastreamento não cria diagnóstico, mesmo quando há resultado elevado.

## 7. Regras de identidade, acesso e evolução

Uma menção nova primeiro é comparada com identidades conhecidas. Havendo ambiguidade, usar registro provisório ou questão; fusão/split são alterações explícitas com impacto em referências e derivados. A semelhança de embeddings não resolve identidade sozinha.

Dados que uma síntese, título, relação ou consulta revelem continuam sujeitos à política do conteúdo de origem. A validação de entrega considera a autorização atual, não apenas a que existia quando o resultado foi criado. Atribuir uma política mais ampla a um derivado exige base/transformação efetivamente permitida; o modelo não decide desclassificação por escrever um resumo curto.

Novos tipos/campos têm versão, finalidade, migração e critérios de compatibilidade. Campos desconhecidos não são promovidos ao catálogo por simples presença numa nota. O texto recebido pode ser preservado como fonte autorizada enquanto sua extração permanece rascunho ou pendente.

## 8. Alcance deste fechamento

Este catálogo fixa uma proposta inicial de famílias, campos e valores. O capítulo 09 especifica registros operacionais; o capítulo 10 fixa relações e validações; a representação física e os exemplos devem preservar este significado. Isso não equivale a um validador executado, ferramenta instalada ou instrumento selecionado.
