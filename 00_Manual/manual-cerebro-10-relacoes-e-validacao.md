# Manual do cérebro pessoal — 10: relações, cardinalidades e validação

Versão da especificação: 0.1. Situação: regras declarativas para implementar e verificar; nenhum validador ou teste executável foi construído. Este capítulo torna verificáveis os catálogos dos capítulos 08 e 09, sem alterar os limites e a autoridade dos processos anteriores.

## 1. Três classes de ligações

1. **Semânticas:** o que se afirma sobre pessoas, experiências e conceitos. São registros `assertion`, com origem, natureza, contexto, tempo e revisão.
2. **De avaliação de evidência:** uma base apoia, contraria ou limita uma hipótese em determinado alcance. Também são afirmações atribuídas quando contêm interpretação.
3. **Técnicas e de proveniência:** referências de sujeito, fonte, derivação, cálculo, execução e substituição. São geradas dos campos canônicos; não precisam de uma nova afirmação para cada referência, evitando uma regressão de registros sobre registros.

O grafo visual pode projetar as três classes, mas precisa identificá-las. Um link de navegação não ganha automaticamente nenhum desses sentidos nem autoriza chamar um processo. A eventual aresta direta entre duas entidades é uma projeção da afirmação relacional, com referência a ela, e não outra verdade canônica.

## 2. Predicados semânticos iniciais

Cada afirmação tem exatamente um sujeito e exatamente um alvo referenciado ou valor. Quando uma relação envolve várias pessoas, usar o acontecimento/contexto comum e afirmações pertinentes; não duplicar a experiência para formar pares. `0..*` significa que um registro pode participar de nenhuma ou várias afirmações desse predicado; não é uma obrigação de completar dados ausentes.

| `predicate` | Sujeito permitido | Objeto permitido | Multiplicidade/contexto |
|---|---|---|---|
| `participates_in` | Pessoa, grupo ou organização | Experiência, projeto, sessão de estudo ou tentativa | `0..*`; papel e período quando relevantes. |
| `member_of` | Pessoa ou grupo | Grupo ou organização | `0..*`; vínculo em períodos diferentes pode coexistir. |
| `has_relationship_with` | Pessoa ou grupo | Pessoa ou grupo | `0..*`; natureza e perspectiva do vínculo no contexto. Não inferir reciprocidade. |
| `occurs_at` | Experiência, ação ou sessão | Lugar | `0..*`; local relatado, não endereço presumido. |
| `occurs_during` | Experiência, ação ou sessão | Período de vida | `0..*`; complementa o `TimeSpec`, não inventa datas. |
| `concerns_topic` | Experiência, ideia, projeto, decisão ou sessão | Conteúdo de estudo, conceito ou ideia | `0..*`; ligação temática não é causalidade. |
| `pursues_goal` | Pessoa, projeto, decisão ou ação | Objetivo | `0..*`; referência à perspectiva e ao período. |
| `uses_method` | Sessão de estudo, ação ou tentativa | Método de estudo ou conceito de método | `0..*`; intenção e uso realizado permanecem distinguíveis na base. |
| `implements_decision` | Ação | Decisão | `0..*`; não concluir realização só porque a decisão existe. |
| `relates_outcome_to` | Resultado da vida real | Ação, tentativa ou experiência | `0..*`; vínculo de acompanhamento, não prova de efeito causal. |
| `prerequisite_for` | Conteúdo de estudo | Conteúdo de estudo | `0..*`; requer fundamento/escopo. Dúvida vira hipótese. |
| `reports_preference` | Pessoa | Entidade pertinente ou valor descritivo | `0..*`; obrigatório contexto/período ou desconhecimento explícito. |
| `reports_value` | Pessoa | Conceito/ideia ou valor descritivo | `0..*`; não inferir valor permanente de uma escolha isolada. |
| `reports_feeling` | Pessoa | Valor descritivo | `0..*`; relato atribuído e contexto; inferência não se apresenta como declaração. |
| `reports_difficulty` | Pessoa | Conteúdo, atividade/conceito ou descrição | `0..*`; contexto e origem. Não estabelece diagnóstico. |
| `hypothesized_pattern` | Pessoa, hábito ou experiência | Conceito/ideia ou descrição contextual | `0..*`; natureza `inference`, bases e limites explícitos. Não atribuir uma declaração nem estabelecer diagnóstico. |
| `reports_diagnosis` | Pessoa | Descrição ou referência autorizada do diagnóstico relatado | `0..*`; apenas relato atribuído ou documento com origem identificada, nunca escore ou opinião da IA convertidos em diagnóstico. |
| `supports` | Afirmação, fonte ou resultado documentado | Afirmação ou síntese específica | `0..*`; avaliação atribuída, bases e alcance. A origem compartilhada continua reconhecível. |
| `contradicts` | Afirmação, fonte ou resultado documentado | Afirmação ou síntese específica | `0..*`; preservar versões e contextos; diferença não prova erro por si só. |
| `limits_scope_of` | Afirmação, fonte ou resultado documentado | Afirmação ou síntese específica | `0..*`; explicitar em que situação/período a generalização não se sustenta. |

Um nome da tabela não confirma o conteúdo da relação. Predicados de relato precisam identificar quem relatou; uma inferência sobre sentimento pode existir como hipótese, mas não usar `reports_feeling` para atribuir ao usuário palavras que ele não disse. Quando a frase é hipótese analítica e não cabe num predicado existente, manter conteúdo inferido e sua base em síntese/questão ou propor predicado específico pelo procedimento de evolução; não falsear uma declaração.

Qualificadores opcionais de afirmação, quando necessários: `role`, `perspective`, `conditions` e `scope_note`. Eles não alteram os tipos de origem/destino nem substituem fonte e tempo. Não permitir qualificadores arbitrários que escondam instruções executáveis ou mudem o significado do esquema.

Duplicatas exatas de sujeito, predicado, alvo/valor, fonte, período e contexto podem ser reconciliadas. Relatos diferentes sobre o mesmo vínculo não são automaticamente duplicatas. Não criar uma aresta inversa canônica só para facilitar a visualização; inversões de navegação preservam referência à origem.

## 3. Referências técnicas e cardinalidades

| Ligação projetada | Campo canônico | Cardinalidade e condição |
|---|---|---|
| Afirmação → sujeito | `subject_ref` | Exatamente 1. |
| Afirmação → alvo ou valor | `object_ref` / `value` | Exatamente uma alternativa; valor tipado. |
| Relato/observação → origem | `source_refs` | Pelo menos 1 fonte localizada para uma afirmação ativa dessas naturezas. |
| Inferência/síntese → bases | `basis_refs` | Pelo menos 1 base com revisão; conclusões sem base permanecem questão/limitação. |
| Resposta → aplicação e item | `assessment_ref`, `item_ref` | Exatamente 1 aplicação e 1 item da versão correspondente. |
| Pontuação → respostas/regra | `response_refs`, `scoring_rule_ref` | Uma regra identificada e todas as respostas/revisões necessárias ao cálculo permitido. |
| Aplicação → instrumento/pessoa | `instrument_ref`, `subject_ref` | Exatamente 1 instrumento versionado e 1 pessoa no escopo autorizado. |
| Questão respondida → resposta | `answer_refs` | Pelo menos 1 referência; resolução da lacuna é decisão adicional. |
| Execução aguardando → questão | `question_refs` / `awaited_by_refs` | Referências coerentes ao esclarecer dado pessoal essencial; resposta integra a retomada, sem duplicar trabalho confirmado. |
| Registro substituído → substituto | `superseded_by_refs` | Pelo menos 1 destino quando conhecido; motivo no evento. Uma exclusão segue outra política. |
| Execução filha → raiz/pai | `root_execution_id`, `parent_execution_ref` | Uma raiz; um pai para cada filha. Raiz não possui pai e identifica a si mesma como raiz. |
| Execução → contrato | `process_ref` | Exatamente 1 revisão do contrato para a execução. |
| Operação → execução e alvos | `execution_ref`, `target_refs` | Uma execução e os alvos necessários. Mutações exigem precondições/revisões ou condição de criação. |
| Busca → execução | `execution_ref` | Exatamente 1 responsável, sem execução nova obrigatória para cada consulta interna. |
| Resultado reutilizável → busca | `search_run_ref` | Exatamente 1 busca de origem e suas bases, contexto e validade. |
| Fila → execução | `execution_ref` | Exatamente 1 referência canônica; interessados podem ser vários. |
| Tentativa → recomendação | `recommendation_ref` | Exatamente 1 nesta versão. Tentativas independentes recebem identidade própria. |

Campos lógicos de participantes, lugares e métodos são visões extraídas de afirmações quando representam vínculos semânticos. Quando materializados para leitura eficiente, indicar a afirmação de origem e reconstruir após correção; não manter duas cópias editáveis independentes. Esta regra se aplica também a `decision_ref`, `action_ref`, `experience_ref`, `topic_refs` e `method_refs` nesse uso, preservando o grau de suporte original. Referências de composição — aplicação/instrumento, resposta/item, pontuação/regra e tentativa/recomendação — são canônicas no próprio registro e projetam ligações técnicas; não exigem duplicação como afirmações semânticas. A ligação tentativa/recomendação indica o plano associado, não prova que ele foi executado.

## 4. Ciclos e dependências

O grafo de conhecimento pode ter ciclos legítimos, como pessoas e projetos mutuamente relacionados. A expansão controla nós visitados e orçamento. Relação semântica não impõe execução.

A linhagem de derivação não aceita uma hipótese como sua própria nova evidência nem um ciclo de sínteses que finja produzir suporte independente. Referências históricas/correções podem apontar ao passado; a validação distingue esse vínculo da base de evidência ativa.

Dependências obrigatórias de uma execução precisam de ordenação realizável. Detectar ciclo sem ponto inicial e rejeitar/replanejar antes de esperar indefinidamente. Encadeamento de processos pode voltar à busca somente com mudança material, motivo e limites, conforme capítulos 03 e 04. A exceção de raiz identificar a si própria não é dependência de trabalho.

## 5. Catálogo de validações

Os identificadores abaixo servem para rastrear requisitos, não para afirmar que já existe código executando-os.

| Regra | Verificação exigida | Falha ou pendência |
|---|---|---|
| V01 — Identidade | ID único, família/subtipo registrados, revisão positiva, versão conhecida. | Rejeitar colisão/formato incompatível; não fundir por nome. |
| V02 — Núcleo e tipo | Campos obrigatórios e tipos corretos; campo desconhecido não muda esquema silenciosamente. | Rascunho/quarentena compatível ou reparo; nunca publicação válida falsa. |
| V03 — Ausência | Valor e `field_states` não se contradizem; zero/falso não substituem desconhecimento. | Rejeitar ambiguidade ou pedir esclarecimento quando necessário. |
| V04 — Referência | Identidade, revisão e trecho recuperáveis ou limitação explicitada. | Fonte indisponível não vira conteúdo inventado. |
| V05 — Relação | Predicado, tipos de sujeito/alvo, exclusividade alvo/valor e cardinalidade válidos. | Rejeitar relação malformada; associação incerta conserva natureza inferida. |
| V06 — Origem | Relatos/observações com fonte; inferências e cálculos com bases/revisões. | Não promover conteúdo sem suporte a conclusão pessoal. |
| V07 — Tempo/contexto | Não confundir ocorrência e registro; precisão respeita o relato. | Marcar desconhecido/aproximado ou esclarecer. |
| V08 — Revisão | Confirmação identifica responsável, momento, revisão e alcance. | Mudança técnica não se transforma em confirmação pessoal/clínica. |
| V09 — Identidade semântica | Ambiguidade, fusão ou separação possui base e evento, com impacto em referências. | Preservar alternativas; não sobrescrever por similaridade. |
| V10 — Linhagem | Origens compartilhadas e exceções conhecidas preservadas. | Repetição, resumo ou troca de IA não aumentam evidência independente. |
| V11 — Instrumento | Versão, finalidade, população, idioma, condições e modalidade verificados no alcance alegado. | Seleção/aplicação dependente permanece pendente; não declarar validação inexistente. |
| V12 — Resposta/cálculo | Item pertence à versão; ausências e regra respeitadas; cálculo fixa revisões. | Não calcular quando inelegível nem imputar silenciosamente. |
| V13 — Interpretação | Resultado descritivo/rastreamento separado de diagnóstico e de causalidade numa decisão. | Impedir conversão automática; organizar contexto e avaliação apropriada quando necessário. |
| V14 — Decisão/ação/resultado | Planejado, escolhido, executado e observado permanecem distinguíveis. | Não registrar sucesso por silêncio ou intenção. |
| V15 — Acesso | Autorização atual abrange conteúdo, títulos, relações, histórico e derivados. | Não entregar/alterar fora do escopo; cache não contorna a política. |
| V16 — Alteração | Precondição de revisão/criação é garantida pela autoridade de escrita, com repetição reconhecível. | Conflito ou efeito incerto exige reconciliação, não reenvio cego. |
| V17 — Efeitos | Confirmação corresponde ao efeito; parcial não é sucesso completo. | Manter pendências/estado específico e responsável. |
| V18 — Novidade/cobertura | Verificar geração, escopo, índices e alterações além das fontes antigas. | Revalidar trecho delimitado ou ampliar recuperação. |
| V19 — Estado/retomada | Estados do capítulo 03 e versões/acesso atuais respeitados. | Não reabrir terminal silenciosamente nem confundir inconclusão com falha técnica. |
| V20 — Limites/ciclos | Raiz e tetos finitos configurados; dependências realizáveis; retorno com progresso. | Não iniciar rotina sem limite obrigatório nem renovar orçamento por filhos. |
| V21 — Evolução | Candidata tem critérios prévios, avaliação e autoridade de adoção. | Texto não instala ferramenta; candidata não altera sua própria aprovação. |
| V22 — Exclusão/restauração | Escopo de remoção e derivados controlados respeitados; restauração reconhece exclusões vigentes. | Não reintroduzir conteúdo eliminado nem prometer apagar serviços externos sem capacidade. |

Validação estrutural automatizável não decide, sozinha, se uma interpretação psicológica é correta, se um estudo se aplica à pessoa ou se um relato é verdadeiro. Avaliações de significado usam fontes, contexto e limitações e podem permanecer inconclusivas. Opinião de outro modelo não substitui evidência de execução.

## 6. Resultado da validação e tratamento

O consumidor distingue: **estruturalmente válido**, **inválido**, **pendente de evidência/esclarecimento**, **conflito**, **incompatível com a versão** e **fora da autorização**. O resultado é da validação, não um rótulo da pessoa. Um registro pode ser estruturalmente válido e insuficiente para a conclusão pretendida.

Erros claros de formato podem receber reparo limitado que não mude o sentido. Mudar conteúdo pessoal, resolver identidade incerta ou alterar a resposta de um instrumento exige o caminho de esclarecimento/correção pertinente. Registrar as alterações confirmadas e não apenas a intenção de corrigi-las.

Parte de uma contribuição pode estar pronta para registro enquanto outra fica em esclarecimento, desde que as dependências permitam essa separação. A publicação de um conjunto que exige consistência conjunta respeita o contrato da operação; não esconder falha parcial.

## 7. Aceita, rejeita e mantém pendente

| Exemplo fictício | Decisão de desenho |
|---|---|
| Pessoa relata preferência contextual e indica a experiência de origem | Aceitar como relato atribuído; não como verdade universal. |
| Duas pessoas com o mesmo apelido e contexto insuficiente | Manter identidades provisórias/questão; não fundir. |
| Aplicação completa, mas instruções essenciais foram alteradas | Registrar aplicação e limites; pontuação comparável depende da regra, sem fingir equivalência. |
| Uma resposta retificada tem escore antigo ainda marcado atual | Rejeitar uso atual até revalidação de cálculo/interpretação. |
| Nova fonte contraditória não aparece no caminho cacheado | Revalidar cobertura e descoberta; não aceitar cache só pela idade ou fonte antiga inalterada. |
| Fonte excluída permanece copiada na receita/histórico | Corrigir a propagação conforme política; não servir a cópia indevida. |
| Relação de participação vira chamada para executar outro processo | Rejeitar a transformação: conhecimento não concede autoridade. |
| Livro, síntese e três IAs repetem o mesmo relato | Preservar linhagem; não chamar isso de cinco experiências independentes. |
| Gravação parcial é conhecida após queda | Confirmar apenas os efeitos identificados e reconciliar pendências. |

Estes exemplos não foram executados como testes. A etapa técnica deverá implementar validações, conferir cenários reais e comparar o comportamento com estes contratos.
