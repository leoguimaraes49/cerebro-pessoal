# Manual do cérebro pessoal — 02: processos e contratos

Versão: rascunho 0.6. Situação: desenho lógico, sem execução ou implementação. O capítulo 03 detalha estados, transições, interrupção e retomada; o capítulo 04 detalha entregas, decisões, autonomia, prioridades e critérios de aceitação; o capítulo 05 detalha memória de buscas, reaproveitamento e atualização dos caminhos. Os contratos deste capítulo devem ser interpretados junto a essas regras.

## 1. Escopo e ordem de trabalho

Este capítulo especifica o funcionamento antes de definir as entidades, os campos ou as pastas do Obsidian. As entradas e saídas abaixo descrevem necessidades de informação; não são esquemas de arquivos, parâmetros finais de ferramentas ou escolhas de banco de dados.

O objetivo é cobrir a arquitetura inteira e suas interações, sem transformar cada regra auxiliar em um subfluxo independente. O capítulo de fundamentos continua válido. Ao detalhar esta lógica, revisar o conjunto e registrar correções; a autorrevisão não substitui a avaliação integrada que será implementada depois.

## 2. O que um contrato precisa garantir

Cada processo precisa explicar:

1. Qual necessidade resolve e em que situação pode ser acionado.
2. Qual componente o inicia e quem tem autoridade para permitir suas ações.
3. Quais informações precisa receber e o que faz se elas não estiverem disponíveis.
4. Quais pré-condições verifica e quais ações pode executar.
5. O que entrega, para quem entrega e o que caracteriza uma conclusão válida.
6. Quais processos pode chamar, em que condições e com que limite.
7. Quais alterações pode persistir e como tratar conflito, repetição ou interrupção.
8. Como encerra com sucesso, dúvida, falha, cancelamento ou espera.
9. Que evidência permite conferir o resultado e quais testes verificam o contrato.

Um processo não declara sucesso porque produziu texto convincente. Uma ferramenta precisa confirmar uma gravação; uma busca precisa distinguir informação encontrada de informação inferida; uma pergunta sem evidência suficiente pode terminar com uma limitação explícita.

## 3. Contextos de operação

| Contexto | Funcionamento esperado |
|---|---|
| Preparação | Verificar ambiente, ferramentas e regras antes de usar o cérebro. |
| Primeiro contato | Avaliação inicial escolhida, perfil provisório e entrevista ampla, nessa ordem. |
| Conversa diária | Interpretar cada turno, consultar o contexto pertinente e responder com continuidade. |
| Manutenção | Pesquisar, testar, reconciliar e otimizar em segundo plano sob limites definidos. |
| Troca de IA | Retomar pelo estado compartilhado autorizado, com fontes, divergências e pendências. |
| Recuperação | Identificar o que foi concluído ou ficou pendente após falha, conflito ou cancelamento. |

Esses contextos reutilizam os mesmos processos. Uma investigação em segundo plano não recebe permissão adicional por ter sido iniciada automaticamente.

## 4. Processos centrais

### P01 — Abrir ou retomar uma sessão

**Gatilho:** iniciar conversa, retomar após interrupção ou trocar de IA.

**Recebe:** solicitação atual, regras vigentes e recursos autorizados disponíveis.

**Executa:** verifica acesso; identifica versões do manual e dos processos; recupera o estado atual autorizado, pendências e contexto pertinente, com acesso aos contratos e evidências completos necessários. Por decisão do usuário, uma leitura rápida não substitui esse material. Consulta fontes adicionais conforme a tarefa exigir, sem pressupor que todo o histórico deva ser carregado em cada turno.

**Entrega:** contexto de trabalho e limites reais conhecidos para interpretação e planejamento.

**Condições:** se a base estiver indisponível ou desatualizada, informa a limitação e não apresenta uma continuidade que não conseguiu recuperar. Instruções essenciais vêm da configuração autorizada, não de uma página ou nota arbitrária encontrada na busca.

**Verificação:** uma IA nova consegue distinguir o perfil atual de hipóteses antigas e reconhecer as pendências; indisponibilidade não vira alegação de leitura completa.

**Primeiro contato:** perfil ausente é uma condição inicial válida. P03 organiza a preparação e a escolha do instrumento; P02 recebe as respostas. A aplicação respeita o instrumento escolhido, e P06/P07/P08 registram resultados e perfil provisório. A entrevista ampla começa depois dessa etapa, conforme a ordem definida pelo usuário. Se o instrumento ainda não estiver escolhido ou sua aplicação não for possível, registrar a pendência; não inventar resultados para liberar a entrevista. Escolher o conteúdo do instrumento continua sendo tarefa posterior, não um requisito de possuir perfil antes de iniciar P01.

### P02 — Receber e interpretar uma contribuição

**Gatilho:** fala, texto, resultado de ferramenta ou documento autorizado.

**Recebe:** contribuição e contexto da sessão ou tarefa que a originou.

**Executa:** identifica pedido, relatos, experiências, emoções declaradas, decisões, correções e dúvidas. Uma mesma contribuição pode alimentar várias áreas. Distingue o que a pessoa disse do que o modelo inferiu. Conserva a origem no alcance permitido pela política de retenção.

**Entrega:** entendimento de trabalho e itens candidatos para busca, resposta ou atualização.

**Condições:** ambiguidade na transcrição pode exigir esclarecimento. Sentimento não declarado pode aparecer como hipótese, não como leitura mental. Retificar uma palavra mal transcrita não é uma mudança de personalidade.

**Verificação:** uma resposta com vários assuntos é aproveitada sem criar automaticamente duplicatas ou conclusões pessoais não sustentadas.

**Construção durante a conversa:** contribuições suficientemente claras alimentam o ciclo P04/P06/P07 ao longo da sessão, sem esperar o encerramento para criar ou atualizar o grafo. Cada pessoa, experiência, pensamento ou relação relevante é comparada com os registros existentes antes de ser proposta. Escritas permitidas podem ocorrer automaticamente; ambiguidades permanecem propostas ou geram esclarecimento conforme o impacto. Trechos de voz ainda instáveis ou incompletos não recebem o mesmo tratamento de um relato compreendido; uma retificação deve ser conciliada antes de consolidar efeitos dependentes. O sistema só informa uma gravação como realizada após confirmação da ferramenta. Esse é um requisito de funcionamento futuro, não uma integração já implementada.

### P03 — Planejar e coordenar uma demanda

**Gatilho:** pedido interpretado ou evento de manutenção válido.

**Recebe:** objetivo, contexto disponível, permissões, versão vigente e limites de execução.

**Executa:** escolhe os processos necessários, define dependências e separa o que precisa ocorrer para responder do que pode entrar na fila de fundo. Reutiliza capacidades existentes antes de propor outra.

**Entrega:** plano executável com resultado esperado e condições de parada.

**Condições:** precisa reconhecer quando ferramentas necessárias não existem ou não estão disponíveis. Um plano não altera permissões. Pergunta simples não deve disparar revisão global ou pesquisa indefinida.

**Verificação:** cada etapa tem finalidade, consumidor do resultado e limite; nenhuma ligação de conhecimento é interpretada automaticamente como chamada operacional.

### P04 — Buscar e compor o contexto

**Gatilho:** necessidade concreta de informação para resposta, revisão ou outro processo.

**Recebe:** questão de busca, informações já conhecidas e escopo autorizado.

**Executa:** combina métodos de recuperação disponíveis e explora relações pertinentes; compara fonte, tempo, contexto, exceções e divergências. O resultado pode incluir informação de áreas aparentemente distintas. Selecionar relevância faz parte da busca, sem criar um segundo processo redundante.

**Entrega:** contexto recuperado, referências, lacunas e distinção entre evidência direta e associação candidata.

**Condições:** para quando há base suficiente para a tarefa, quando os limites são atingidos ou quando faltam dados que só outra fonte pode fornecer. Não garante ter encontrado tudo nem transforma similaridade em causalidade.

**Verificação:** encontra contexto indireto útil e evita incluir conexões sem justificativa; resultados antigos são checados antes de uso como informação atual.

**Memória de buscas:** consulta resultados e percursos anteriores quando pertinentes. Um resultado requer validação atual; uma receita de percurso pode orientar uma investigação nova sem herdar a conclusão. O executor registra operações observáveis e fontes sob autorização, retenção e garantias aplicáveis de P07, sem converter todo log em conhecimento pessoal. Verifica novidades no conjunto pesquisável, inclusive notas sem ligações que sejam relevantes por texto ou significado. O capítulo 05 define quando reutilizar, atualizar parcialmente ou refazer; não é criado um P15 redundante.

### P05 — Adaptar uma investigação e compor estratégias

**Gatilho:** P04 identifica uma lacuna relevante, conflito não resolvido ou estratégia improdutiva.

**Recebe:** questão, tentativas anteriores, lacuna e operações disponíveis.

**Executa:** reformula a questão ou compõe outra sequência de buscas e processos. Pergunta ao usuário quando o dado depende dele; pode encaminhar pesquisa externa quando adequada. Registra o que mudou em relação à tentativa anterior para detectar repetição sem progresso.

**Entrega:** novo contexto, hipótese explicitamente provisória, pergunta de esclarecimento ou encerramento com lacuna. Estratégia reutilizável pode gerar uma candidata para P12.

**Condições:** composição temporária usa operações permitidas; criar sua descrição não implementa uma ferramenta nova. Respeita limites de passos, custo e profundidade compartilhados com a demanda de origem.

**Verificação:** admite ausência de informação, não inventa biografia e não repete indefinidamente as mesmas buscas com outra redação.

### P06 — Propor alterações no conhecimento

**Gatilho:** informação nova, resultado de busca ou revisão que justifique mudança.

**Recebe:** conteúdo, fontes pertinentes, registros existentes e regras de alteração.

**Executa:** decide entre criar, associar, atualizar, manter dúvida ou não alterar; verifica identidade e duplicação; distingue registro relatado de interpretação. Calcula impacto e condições de adoção segundo a política vigente.

**Entrega:** proposta de alterações com base, alcance, dependências e tratamento de incerteza.

**Condições:** uma busca sem resultados não obriga criar algo. Nova menção pode se referir a algo existente. Relação indireta incerta não recebe o mesmo tratamento de uma correção explícita do usuário.

**Verificação:** reaproveita o que já existe e permite que a mesma experiência se conecte a várias áreas sem replicar sua evidência.

### P07 — Validar e aplicar uma alteração

**Gatilho:** proposta de P06 ou de um processo de revisão.

**Recebe:** alteração proposta, versões consultadas, origem e autorização aplicável.

**Executa:** valida o contrato, o alcance de acesso e as versões. Detecta repetição e conflito. Aplica mudanças de maneira consistente ou devolve uma pendência ou falha verificável. Produz os eventos necessários para reavaliar derivados.

**Entrega:** confirmação do que foi aplicado e do que ficou pendente; ou motivo específico de falha.

**Condições:** não sobrescreve silenciosamente atualização concorrente. Retentativa não duplica efeitos. Uma falha parcial precisa ser reconhecida e recuperável, sem resposta de sucesso completo.

**Verificação:** gravações concorrentes, repetidas e interrompidas preservam consistência; estado proposto não é confundido com adotado.

**Derivados e registro operacional:** uma alteração confirmada precisa deixar reconhecível a necessidade de revalidação dos resultados pertinentes, mesmo quando reindexação e revisão pesada ocorrerem depois. Reconhecer eventual diferença entre a versão da base e a cobertura dos índices. O registro operacional pelo executor segue as garantias aplicáveis deste contrato, sem exigir nova interpretação de IA em cada linha e sem reativar buscas por ter registrado a si mesmo. A decisão sobre conhecimento pessoal continua passando por P06/P08; receitas persistentes seguem P12/P13.

### P08 — Revisar perfil, tempo e dependências

**Gatilho:** correção, resultado novo, contraste temporal ou evidência pertinente ao perfil.

**Recebe:** diferença encontrada, fontes, contexto e derivados afetados.

**Executa:** usa os subfluxos de mudança temporal e correção em cadeia. Distingue erro, evolução, diferença de situação e incerteza. Procura evidências favoráveis e contrárias e propõe ajustes. Pode ser executado por IAs diferentes, preservando a linhagem das fontes e identificando origens compartilhadas; trocar o modelo não torna a evidência independente.

**Entrega:** revisão do perfil ou de suas dependências, ou divergência aberta; encaminha escritas por P07.

**Condições:** não exige consenso entre modelos. Uma emoção passageira não redefine automaticamente um traço. Uma correção clara invalida o uso atual da informação antiga enquanto derivados pertinentes são reavaliados.

**Verificação:** corrige derivados sem apagar acontecimentos verdadeiros e não usa repetição de análises como nova evidência independente.

### P09 — Responder e personalizar sugestões

**Gatilho:** contexto suficiente ou necessidade de explicar uma limitação.

**Recebe:** pedido, contexto selecionado, perfil pertinente e estado confirmado das operações.

**Executa:** responde ao objetivo; diferencia fatos recuperados, hipóteses e sugestões. Quando útil, liga recomendações às experiências e fontes que as sustentam. Considera o contexto emocional relatado, razões, valores, alternativas e consequências, sem presumir medida exata da personalidade ou da emoção.

**Entrega:** resposta utilizável e, quando apropriado, sugestão ou experiência a acompanhar por P10.

**Condições:** não exige expor comunicação interna ou raciocínio privado do modelo. Mantém justificativas resumidas rastreáveis. Não anuncia gravação ou pesquisa não confirmada. Uma resposta pode ser útil mesmo com limitações explicitadas.

**Verificação:** a sugestão considera contexto real e não apenas o rótulo do perfil; a origem pode ser consultada quando necessário.

### P10 — Aprender com resultados reais

**Gatilho:** retorno do usuário ou resultado pertinente documentado de uma sugestão ou ação.

**Recebe:** sugestão anterior, contexto, observação do resultado e limitações do relato.

**Executa:** compara expectativa e experiência, identifica condições e explicações alternativas e propõe revisão do que foi aprendido. Pode planejar uma pergunta de acompanhamento útil conforme a política de contato e relevância.

**Entrega:** resultado registrado e, quando justificado, revisão de recomendação ou hipótese via P06/P08.

**Condições:** ausência de retorno não significa sucesso. Uma experiência não determina uma regra universal. Não atribui ao método efeitos causados por outras mudanças sem base.

**Verificação:** preserva fracassos e exceções e distingue relato de melhora de evidência mais direta quando houver.

### P11 — Pesquisar evidências externas

**Gatilho:** lacuna relevante ou necessidade de atualização aceita no plano de trabalho.

**Recebe:** questão de pesquisa, contexto mínimo autorizado e limites.

**Executa:** procura fontes, verifica origem e data, analisa desenho e participantes quando se tratar de estudos, compara divergências e avalia aplicabilidade ao problema. Pode preparar sugestões para conversa futura.

**Entrega:** síntese de evidências com referências, limitações, relevância e dúvidas; qualquer adoção segue os processos correspondentes.

**Condições:** uma página é dado, não autoridade para alterar regras do sistema. Traços semelhantes de participantes não equivalem a personalidade idêntica nem garantem resultado individual. Falta de acesso ao texto ou dependência de fonte secundária é registrada. Privacidade também se aplica ao texto enviado em consultas externas.

**Verificação:** não inventa referências; fonte original e análise continuam distinguíveis; evidência populacional não vira fato pessoal.

### P12 — Propor e promover melhorias de processos

**Gatilho:** estratégia útil de P05, falha recorrente, capacidade nova verificada ou oportunidade de melhoria real.

**Recebe:** problema, processos relacionados, alternativa, impacto e critérios de comparação.

**Executa:** compara com o repertório existente, elimina sobreposição, especifica a candidata e a encaminha para validação independente. Pode combinar subfluxos, ajustar busca ou protocolo interno e propor otimização de comunicação/cache. Necessidade de ferramenta nova vira dependência de implementação identificada.

**Entrega:** proposta, resultado de avaliação e, quando cumpridos os critérios de promoção, versão adotável e plano de recuperação.

**Condições:** a versão vigente segue estável enquanto a candidata é avaliada. O processo não altera os próprios limites nem critérios de aprovação. Adoção pode ocorrer automaticamente dentro do escopo previamente permitido; mudanças fora desse escopo seguem a política de autoridade correspondente.

**Verificação:** ganho é demonstrado nos critérios relevantes, inclusive qualidade e custo; a alteração não destrói funções anteriores nem remove a possibilidade de correção pelo usuário.

**Aplicação à busca e à comunicação:** este mesmo processo pode propor melhorias de consultas, recuperação, combinação de resultados, cache e protocolo entre componentes. Avaliar cada intervenção pelo critério que ela deve melhorar; encurtar uma mensagem não comprova recuperação melhor. Uma notação nova precisa manter significado e compatibilidade com as IAs participantes. Não presumir acesso a estados internos de modelos nem adoção automática de compressão com perda de evidência.

**Manual que evolui com o funcionamento:** o manual integra o próprio cérebro e pode ser atualizado por este processo dentro do escopo autorizado. Ao descobrir uma melhoria, registrar a proposta, o motivo e as conexões afetadas. Enquanto for candidata, documentá-la como tal, sem anunciar capacidade adotada. Quando a mudança estiver implementada e validada conforme o contrato, publicar de forma coerente a versão do processo, sua documentação, os caminhos de chamada e as dependências. As IAs posteriores devem conseguir identificar qual versão está vigente. Manter histórico e plano de reversão compatível entre documentação e execução; uma nota descrevendo uma função não equivale à função instalada. Testar também a correspondência entre o manual vigente e as ferramentas efetivamente disponíveis.

### P13 — Verificar o funcionamento integrado

**Gatilho:** candidata, mudança significativa ou rotina de verificação definida.

**Recebe:** versão atual, alternativa, cenários e critérios previamente estabelecidos.

**Executa:** valida contratos e cenários independentes, compara resultados, verifica escrita, busca, perfil, correções, continuidade, ciclos e custos. Executa os testes em ambiente separado dos registros reais ou com exemplos autorizados.

**Entrega:** resultado por critério, falhas reproduzíveis, regressões, limitações e decisão elegível para promoção ou correção.

**Condições:** o mesmo modelo pode ajudar a examinar a saída, mas sua opinião não basta como prova. Casos de avaliação não são apenas os exemplos usados para ajustar a candidata. A rigidez dos contratos não transforma uma inferência subjetiva em fato.

**Verificação:** uma candidata eficiente, mas pior em recuperar correções ou admitir lacunas, não é promovida só pela economia.

### P14 — Coordenar manutenção, retomada e recursos

**Gatilho:** evento relevante, agendamento autorizado, pendência ou retorno após falha.

**Recebe:** tarefas pendentes, prioridades, orçamento e disponibilidade do ambiente.

**Executa:** organiza fila, agrupa tarefas equivalentes, evita sobreposição, retoma de pontos confirmados e respeita cancelamento. Pesquisa e otimização não competem indefinidamente com a conversa. O executor pode parar quando o computador, a conexão ou o recurso de modelo estiver indisponível.

**Entrega:** trabalhos concluídos ou pendentes com estado verificável; achados úteis ficam disponíveis para futuras conversas.

**Condições:** cada tarefa tem limite de esforço e motivo rastreável. O término de um agendamento ou cancelamento não é confundido com término de toda tarefa em execução; o alcance da interrupção precisa ser explícito.

**Verificação:** reiniciar não perde correções confirmadas nem duplica gravações; não há promessa de atividade autônoma sem executor disponível.

## 5. Regras transversais

**Controle de acesso e dados:** aplica-se em toda leitura, consulta externa, escrita, exportação e exclusão. Não é uma nova busca paralela. Dados pessoais e instruções autorizadas são distinguidos.

**Cache e eficiência:** integram recuperação e execução. Resultados só são reutilizados quando origem, contexto, acesso, revisões e mudanças no escopo pesquisável continuam compatíveis. Novas notas ou relações podem afetar buscas sem alterar suas fontes anteriores. Memória operacional, resultado e receita são distintos, conforme o capítulo 05. A representação interna pode evoluir por P12/P13, sem presumir que binário reduza tokens ou que mais uso reduza automaticamente o custo.

**Rastreabilidade e recuperação:** todo processo distingue informação recebida, interpretação, proposta e efeito confirmado. Exclusão e restauração devem considerar índices e derivados sob controle do sistema, conforme a política a especificar.

**Atualização incremental:** a continuidade deve depender de registros confirmados ao longo da atividade, não de uma última mensagem que talvez nunca ocorra.

## 6. Caminhos completos que a lógica deve cobrir

| Situação | Caminho principal |
|---|---|
| Primeiro contato e primeira entrevista | P01 aceita perfil ausente → P03 coordena preparação e avaliação inicial, com respostas por P02 e registros por P06/P07/P08 → perfil provisório → entrevista ampla pelo ciclo P02/P03/P04/P06/P07/P08/P09. |
| Pergunta sobre estudo | P01/P02 → P03 → P04 → P05 se necessário → P09 → P10 após retorno. |
| Pessoa ou experiência nova | P02 → P04 para contexto e duplicação → P06 → P07 → P08 quando pertinente. |
| Correção do usuário | P02 → P03 → P08 → P06/P07 → revisão de derivados e invalidação de resultados pertinentes → P09. |
| Troca de IA | P01 com estado compartilhado → P04 conforme a tarefa → continuidade sem supor memória interna transferida. |
| Pesquisa sem conversa | P14 → P03 → P11 → P06/P07 quando adequado → material disponível para P09 ou revisão. |
| Estratégia nova | P05 → candidata em P12 → P13 → promoção conforme a política → próxima execução usa a versão adotada. |
| Busca anterior pertinente | P04 verifica contexto, acesso, revisões e novidades → reutiliza resultado validado, atualiza parte delimitada ou executa receita/recuperação mais ampla → P05 quando faltar base. Registro operacional confirmado não é evidência pessoal nova. |
| Falha durante gravação | P07 identifica o ponto confirmado → P14 coordena retomada → repetir não duplica efeitos. |

A indicação de um caminho não obriga executar todas as etapas em toda conversa. Os gatilhos e a necessidade determinam quais são pertinentes. Rotinas reativadas por seus próprios resultados precisam reconhecer a origem e verificar se há informação nova antes de continuar.

## 7. Autorrevisão obrigatória desta especificação

Antes de adotar ou ampliar um contrato:

1. Conferir se a capacidade já existe e se é melhor ajustar um processo atual.
2. Conferir se cada entrada tem uma origem possível e se cada saída tem um consumidor.
3. Verificar permissões, efeitos persistentes, versões e tratamento de informações incertas.
4. Percorrer um caso normal, um caso sem informação e um caso de falha ou interrupção.
5. Verificar ciclos, efeitos repetidos, concorrência e condições de parada.
6. Conferir impacto nos outros processos e nos critérios de qualidade, custo e continuidade.
7. Atualizar contratos e caminhos afetados e registrar pendências reais.

Esta lista deve orientar a revisão do documento, mas sua conclusão não comprova que o software passou em testes. Os testes executáveis serão definidos e rodados na implementação.

## 8. Situação dos detalhamentos

Os estados e a retomada estão descritos no capítulo 03. Entregas, suficiência da busca, autoridade, promoção de versões, prioridades, limites e percursos de aceitação estão detalhados logicamente no capítulo 04; a memória dos caminhos está no capítulo 05. Foi realizada conferência manual cruzada e foram corrigidos os pontos registrados em revisao-logica-processos.md. Uma primeira revisão independente não entregou resultado por limite de uso e não foi considerada aprovada. A revisão posterior de 28 de outubro de 2026 examinou os capítulos 01 a 05, a proposta de busca e o comparativo de integrações; não encontrou correção lógica bloqueante, e as referências editoriais indicadas foram ajustadas. Isso não equivale a validação de software.

Permanecem para as etapas correspondentes: escolher instrumento e roteiro específicos do primeiro contato; definir valores operacionais compatíveis com o ambiente; detalhar a avaliação de fontes e as ferramentas reais; construir e executar testes. Uma regra lógica definida não significa que sua implementação ou sua validação empírica já ocorreu.

Depois da consolidação lógica, suas necessidades orientam o catálogo de entidades, campos, relações e ferramentas concretas do Obsidian. Os capítulos 06 a 11 detalham núcleo, avaliação, experiências, tipos/campos, operação, relações/validações e representação/templates. São propostas de modelagem e formato; mecanismos e validadores executáveis continuam exigindo implementação e testes.
