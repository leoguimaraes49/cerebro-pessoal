# Manual do cérebro pessoal — 04: interações e políticas de decisão

Versão: rascunho 0.4. Situação: especificação lógica; os casos abaixo ainda não foram executados em software. O capítulo 05 complementa as regras de recuperação com memória de buscas e evolução de caminhos.

## 1. Direção e escopo

O usuário escolheu um cofre novo, do zero, mas determinou que os processos sejam fechados antes da criação desse cofre e da definição final das entidades e campos. Este capítulo trata os quatro blocos restantes do funcionamento: entregas, critérios de decisão, limites e aceitação.

As informações mencionadas são requisitos lógicos. Não são nomes definitivos de propriedades ou pastas do Obsidian. Os processos P01 a P14 e os estados do capítulo 03 continuam sendo as referências.

## 2. Entrega entre processos

Toda entrega precisa permitir que o consumidor reconheça: qual pedido está sendo atendido; de onde veio o resultado; qual contrato e quais versões foram usados; o que foi encontrado ou realizado; quais fontes sustentam a conclusão; quais limitações ou conflitos permanecem; e quais efeitos foram confirmados. Não é necessário expor raciocínio interno privado do modelo.

Antes de continuar, o consumidor verifica compatibilidade com sua necessidade, acesso, vigência e suficiência. Um processo concluído pode entregar evidência insuficiente para uma conclusão específica; nesse caso, o consumidor não trata a lacuna como resolvida.

| Entrega recebida | Tratamento |
|---|---|
| Válida e suficiente | Continuar com base nas fontes e limites informados. |
| Válida, porém incompleta | Complementar somente o que falta, adaptar a investigação ou apresentar limitação conforme a tarefa. |
| Contém divergência | Preservar as alternativas e encaminhar a revisão pertinente; não decidir pela quantidade de IAs concordantes. |
| Usa revisão superada | Conferir o que mudou e recalcular o trecho afetado antes de usar como atual. |
| Incompatível com o contrato | Rejeitar a entrega, registrar o motivo e solicitar reparo limitado quando houver perspectiva de recuperação. |
| Efeito ainda não confirmado | Verificar a ferramenta ou o estado de aplicação; não executar novamente às cegas. |
| Fora da autorização | Não consumir nem propagar a informação ou ação naquele escopo; tratar conforme a política de acesso. |

O executor valida a estrutura e os efeitos observáveis. A IA avalia relevância e significado dentro das fontes disponíveis. Ambas as verificações podem ser necessárias; nenhuma substitui a outra.

Na primeira utilização, ausência de perfil é um estado inicial válido, não falha de continuidade. P01 recupera as regras e o que já existir; o caminho de primeiro contato conduz à preparação e à avaliação inicial antes da entrevista ampla, sem inventar um perfil para conseguir iniciar.

## 3. Encadeamento e retorno

P03 coordena dependências. Processos podem executar em paralelo quando não dependem da saída um do outro e não produzem efeitos conflitantes. Etapas que exigem informação anterior aguardam sua confirmação.

Para cada conjunto de tarefas, distinguir saídas obrigatórias de complementares. Falha em uma saída obrigatória impede declarar o objetivo atendido. Falha em uma complementar pode permitir resposta com a limitação explicitada, conforme o contrato. Essa distinção é feita no plano e não inventada depois para esconder falha.

Uma combinação reutiliza contratos existentes. Seu consumidor pode ser outro processo, a resposta ao usuário ou uma fila de manutenção. Uma saída sem consumidor ou propósito identificável é sinal de redundância a revisar.

Se uma etapa voltar à busca ou à revisão, deve identificar o que mudou: evidência nova, pergunta reformulada, versão diferente ou falha recuperável. Retorno sem mudança e sem progresso não autoriza um ciclo indefinido.

### 3.1 Encaminhamentos permitidos

A tabela descreve solicitações lógicas, não chamadas irrestritas. P03 e o executor conferem necessidade, escopo, versões e orçamento antes de iniciar etapas. Leituras e verificações determinísticas internas não exigem uma nova chamada de IA para cada linha.

| Processo de origem | Próximos trabalhos que pode solicitar, quando necessários |
|---|---|
| P01 — Sessão | P02/P03 para a demanda ou primeiro contato; P04 para recuperar o estado pertinente. |
| P02 — Interpretação | P03 para planejar a demanda e encaminhar contribuições ou correções. |
| P03 — Coordenação | P04 a P14 conforme o objetivo. Atribui dependências e limites; não se replica para renovar orçamento. |
| P04 — Busca | P05 para lacuna; entrega ao consumidor original. O executor pode registrar o percurso operacional sob as garantias aplicáveis de P07, sem nova chamada de IA por evento. Uma hipótese encontrada não se grava automaticamente. |
| P05 — Adaptação | P04 para busca diferente, P11 para fonte externa, P09 para esclarecimento ou limitação, P12 para candidata reutilizável. |
| P06 — Alteração proposta | P04 para resolver identidade ou contexto faltante; P07 para aplicar a proposta validada. |
| P07 — Aplicação | P08 para derivados afetados; P03 para conflito ou P14 para recuperação necessária. Repetição sem mudança não gera novos efeitos. |
| P08 — Revisão | P04 para fontes, P06/P07 para ajustes e P09 para esclarecer ponto dependente do usuário. Não reabre a própria revisão sem mudança material. |
| P09 — Resposta | P06/P07 quando houver informação autorizada a registrar; P10 somente quando existir retorno ou resultado pertinente. |
| P10 — Resultado real | P06/P08 para registrar resultado e revisar o que for justificado. |
| P11 — Pesquisa externa | P06/P07 para evidências autorizadas e P08/P09 quando houver revisão ou sugestão pertinente. |
| P12 — Evolução | P04 para repertório existente, P13 para avaliar candidata e P07 para publicar descrições adotadas. Uma capacidade de software ausente permanece dependência de implementação. |
| P13 — Verificação | Executor isolado para os cenários e retorno ao solicitante. Avaliar uma candidata não dispara automaticamente outra avaliação de si mesma. |
| P14 — Manutenção | P03 para executar uma demanda válida da fila; não recria a mesma demanda indefinidamente por eventos que ela própria produziu. |

Novos encaminhamentos persistentes alteram contratos e seguem o ciclo de evolução. A tabela não substitui as condições particulares de cada processo. Trabalhos de implementação de novas ferramentas precisam de capacidades e autorização efetivas; uma publicação textual em P07 não instala código.

## 4. Quando buscar mais e quando perguntar

Uma busca é suficiente para uma resposta na medida em que reúne evidências pertinentes às partes do pedido, trata referências e períodos relevantes, procura correções e contradições conhecidas e permite rastrear as conclusões. A seleção de candidatos por similaridade é apenas parte desse trabalho.

A investigação pode continuar quando houver uma lacuna importante e um caminho plausível para reduzi-la. Não precisa procurar todo o cofre antes de responder. Também não deve encerrar apenas porque encontrou um número fixo de notas.

Perguntar ao usuário quando a diferença de interpretação pode alterar materialmente a resposta ou uma mudança persistente e a informação necessária depende da pessoa. Evitar perguntas de permissão repetidas para operações já autorizadas. Perguntar não substitui uma busca disponível que pode resolver o ponto.

Se a informação não estiver acessível e a resposta ainda puder ajudar, explicar o que é desconhecido e seu efeito. Na ausência de base, não inventar fatos pessoais nem transmitir certeza por exigência de tom assertivo. O resultado pode permanecer inconclusivo.

### 4.1 Perguntar para completar uma conclusão

Quando faltar um detalhe essencial para a conclusão e esse detalhe depender do usuário, o sistema deve formular uma pergunta pertinente. Primeiro verifica se o dado já está disponível nas fontes autorizadas, para evitar pedir novamente o que já foi contado. A pergunta deve indicar o ponto a esclarecer sem sugerir que uma hipótese da IA já é verdadeira.

Registrar a dúvida como pendência e aguardar a resposta quando ela for indispensável. Trabalhos independentes podem continuar; a conclusão dependente não é publicada como resolvida. Ao receber a resposta, retomar a parte afetada, revalidar contexto e versões e aplicar correção em cadeia se a nova informação retificar uma premissa anterior. Respeitar os limites da demanda, sem reiniciar o orçamento por ter perguntado.

Se o usuário não souber, não quiser responder ou adiar, manter a lacuna ou entregar uma conclusão limitada quando isso ainda for útil. Não interpretar ausência de resposta como confirmação. Uma resposta adicional pode reduzir a dúvida, mas não garante que qualquer questão subjetiva se torne conclusiva.

Em rotina sem conversa ativa, guardar a pergunta para contato permitido ou para a próxima conversa pertinente; a necessidade de esclarecimento não cria automaticamente um canal ou autorização de notificação.

### 4.2 Novos pensamentos e conclusão da busca

Uma combinação pode produzir uma hipótese nova com ligações às fontes de origem. O sistema avalia se a hipótese acrescenta conteúdo útil ou se basta registrar uma relação, sem criar uma entidade para toda combinação possível. A nova hipótese não é evidência independente dos relatos que a originaram.

A busca da pergunta atual pode encerrar com evidência suficiente, com incerteza declarada ou por limite explícito. A existência de novas combinações possíveis não exige prolongá-la indefinidamente. Uma investigação futura pode retomar quando houver informação materialmente nova ou um objetivo diferente, sob o contrato correspondente.

### 4.3 Reutilização e impacto de novidades

A busca híbrida é a arquitetura escolhida; mecanismos concretos e medição ficam para implementação. Resultado reaproveitável, histórico de execução e receita de investigação permanecem distintos. Similaridade seleciona percursos candidatos, mas não comprova que a pergunta atual tenha a mesma resposta.

Conferir contexto, acesso, revisões, contratos e mudanças no conjunto pesquisável antes de reutilizar. Uma nota nova pode alterar o resultado sem tocar nas fontes anteriores, inclusive antes de ter ligações no grafo. Reavaliar a partir da mudança quando o alcance puder ser delimitado; ampliar a recuperação quando a identificação de impacto não for suficiente. Um caminho antigo precisa manter saída para descoberta e para a busca adaptativa.

Correções e exclusões impedem uso atual de resultados reconhecidamente inválidos, mesmo durante atraso da indexação. Memória operacional também respeita acesso, retenção e reconhecimento de repetição. O capítulo 05 detalha as condições; não acrescenta estados de execução nem exige novas entidades nesta fase.

## 5. Decisões sobre conhecimento e perfil

| Situação | Decisão lógica |
|---|---|
| Relato novo com origem clara | Registrar como relato, com contexto e busca de duplicação; não apresentar como comprovação independente. |
| Correção explícita sobre registro pessoal | Corrigir o alcance indicado, confirmar aplicação e sinalizar derivados afetados. |
| Diferença entre períodos ou situações | Preservar as versões pertinentes e revisar o contexto; não aplicar a regra de que o último relato sempre vence. |
| Hipótese inferida pela IA | Registrar como hipótese e associar sua base; não marcar como confirmação do usuário. |
| Divergência entre IAs | Comparar fontes e pressupostos; manter divergência se não houver base para resolvê-la. |
| Afirmação pública ou científica em conflito com opinião pessoal | Separar o relato da pessoa da avaliação da fonte externa; não sobrescrever um pelo outro como se fossem o mesmo tipo de evidência. |
| Recomendação que foi experimentada | Registrar o resultado e suas condições, sem inferir sucesso pelo silêncio nem generalizar um único caso. |

A revisão pode atualizar hipóteses automaticamente dentro do contrato e do escopo autorizado, preservando incertezas e histórico. Não deve interromper toda conversa para confirmar cada interpretação. Quando a decisão depende de esclarecer o significado do relato ou seu alcance, faz a pergunta necessária.

Enquanto uma correção relevante é aplicada e seus derivados são reavaliados, resultados reconhecidamente inválidos ficam impedidos de uso como informação atual. A revisão completa de todas as dependências pode ser feita em fila, mas a resposta corrente precisa respeitar o que já se sabe estar superado.

## 6. Autonomia e evolução do manual

O manual integra o cérebro, mas uma alteração no manual precisa ser distinguida de uma mudança de capacidade executável.

| Classe de ação | Tratamento |
|---|---|
| Leitura, busca e interpretação dentro do acesso vigente | Executar conforme o contrato; não requer aprovação nova por padrão. |
| Registro, conexão, correção e revisão permitidos | Aplicar por P07, com validação, origem, versões e tratamento de incerteza. |
| Plano temporário que combina ferramentas existentes | Executar dentro dos limites compartilhados; não altera o catálogo de ferramentas. |
| Mudança persistente em processo ou protocolo | Criar candidata, validar, testar e promover segundo os critérios vigentes. A promoção pode ser automática no escopo previamente autorizado. |
| Dependência nova de código, ferramenta, fornecedor ou recurso | Identificar necessidade e viabilidade; realizar implementação e verificação antes de documentar como disponível. |
| Ampliação de permissões ou alteração dos critérios essenciais de autoridade | Seguir autoridade própria definida pelo usuário; uma candidata não pode conceder isso a si mesma. |

Na promoção, verificar que a documentação, as ferramentas, os contratos e as dependências descrevem a mesma versão. Preservar recuperação compatível. Modelos posteriores devem conseguir identificar a versão vigente e as candidatas ainda não adotadas.

Não obrigar uma revisão por várias IAs em todo turno: esse recurso é acionado quando tem uma finalidade concreta, como conflito relevante ou avaliação de uma candidata. Concordância continua sendo análise, não evidência pessoal adicional.

## 7. Política de prioridades e fila

Ordem recomendada de atenção: revogação de acesso, exclusão e interrupção aplicável; correção que invalide dados em uso; demandas da conversa; manutenção necessária à integridade; pesquisa complementar e otimização. A posição não dispensa dependências nem garante interrupção instantânea de uma ferramenta externa.

A fila precisa evitar que a manutenção nunca avance, mas não sacrifica a correção de uma resposta atual para executar otimizações opcionais. Seu mecanismo de justiça e distribuição será ajustado ao ambiente de execução.

Tarefas equivalentes podem ser agrupadas se preservarem o propósito, o acesso e a origem de cada demanda. Uma execução em andamento pode atender a mais de um interessado sem duplicar efeitos; cancelar um interessado não cancela automaticamente uma tarefa que ainda seja necessária aos demais.

Interrupção, espera e retomada seguem o capítulo 03. A rotina de fundo precisa de agendamento ou evento válido e de recursos realmente disponíveis. Eventos gerados pela própria tarefa não a reativam indefinidamente: verificar se existe diferença material antes de iniciar outra investigação.

## 8. Política de limites

Limites são parâmetros de operação, aplicados pelo executor. O manual define a mecânica; a configuração de implantação fornece valores compatíveis com hardware, conta e classe de tarefa. Não há orçamento infinito implícito. A ausência de valor obrigatório impede iniciar uma rotina autônoma dependente dele e gera uma pendência de configuração, não um pedido recorrente ao usuário durante cada conversa.

O escopo completo desejado pelo usuário e a preferência por respostas completas são preservados. Os limites controlam repetição e uso de recursos; não autorizam omitir uma lacuna ou alegar que uma investigação truncada foi exaustiva.

Antes de executar, definir teto de passos, profundidade de chamadas, duração, tentativas, contexto por chamada e custo ou esforço disponível. Os valores iniciais não devem ser apresentados como cientificamente ideais. Devem ser mensurados e ajustados por classe de trabalho.

Processos filhos compartilham o limite da demanda de origem. O coordenador escolhe reduzir escopo opcional, colocar continuidade em fila, retornar a informação obtida com sua limitação ou encerrar, segundo o contrato. Aumento de orçamento depende da política vigente, sem autoampliação ilimitada.

O custo deve incluir planejamento, indexação, geração de vetores, comunicação, testes e tentativas improdutivas, além da resposta final. Economia não é avaliada apenas pelo tamanho da mensagem.

## 9. Critério de aceitação de uma mudança

Definir a capacidade que a mudança pretende melhorar e o patamar de qualidade a preservar antes de testá-la. Medir recuperação de fontes e uso correto delas separadamente; considerar tempo, memória, custo e atualização. Uma melhora em velocidade não compensa, por padrão, perder correções ou transformar hipóteses em fatos.

Comparar com a versão vigente nas mesmas condições. Manter casos de referência, dados de ajuste separados dos de avaliação e registro de limites conhecidos. Para critérios subjetivos, usar retorno do usuário e comparação fundamentada; não apresentar opinião de um avaliador de IA como prova definitiva.

Uma candidata pode ser rejeitada, continuar em avaliação ou ser adotada. A revisão deve alcançar também o manual e a compatibilidade com IAs e ferramentas participantes.

## 10. Percursos de aceitação

| Cenário | Resultado esperado |
|---|---|
| Resposta por voz contém história, emoção e decisão | P02 identifica os componentes, P04 procura contexto e duplicatas, P06/P07 registram apenas efeitos permitidos, P09 não declara inferências como relatos. |
| Pergunta de estudo usa palavras diferentes das notas | P04 pode usar recuperação lexical e semântica, explorar relações e recuperar as fontes; P05 adapta a estratégia quando necessário. |
| Pergunta depende de informação pessoal ausente | Busca limitada por acesso, pergunta quando necessário ou resposta com lacuna explícita. Artigo externo não preenche a biografia. |
| Correção chega enquanto outra IA escreve | P07 identifica versão conflitante; informação antiga não sobrescreve a correção; derivados reconhecidamente inválidos não são usados como atuais. |
| Duas interpretações conflitantes usam o mesmo relato | P08 trata a origem como uma evidência e preserva a divergência se não houver dado para decidir. |
| Pesquisa externa encontra recomendação diferente | P11 registra fonte e limitações; P08/P09 avaliam a pertinência; não muda automaticamente a história nem estabelece personalidade por semelhança de grupo. |
| Subfluxos conectados sugerem combinação nova | P12 verifica utilidade e sobreposição, P13 avalia; uma proposta em nota não ganha execução por si só. |
| Protocolo compacto reduz texto, mas perde exceção | A candidata falha no requisito de preservação; economia isolada não a aprova. |
| IA é trocada no meio da continuidade | P01 recupera estado confirmado e fontes pertinentes; não depende do raciocínio interno privado da IA anterior. |
| Conexão cai depois de uma gravação | P14/P07 conferem confirmação antes da retentativa, sem duplicar o efeito. |
| Falha de uma tarefa complementar | O consumidor decide conforme o contrato e declara a limitação; não esconde falta de uma dependência obrigatória. |
| Exclusão atinge conteúdo usado por cache | Invalidação impede uso indevido de derivados controlados; recuperação de versão antiga respeita a exclusão vigente. |
| Nota nova contraditória não altera nenhuma fonte antiga | Revalidar mudanças no conjunto pesquisável e recuperar a novidade; não presumir validade só pelas revisões antigas. |
| Pergunta semelhante tem objetivo ou contexto diferente | Receita pode orientar a investigação; conclusão antiga não é aplicada automaticamente. |
| Índice atrasa após correção confirmada | Usar fonte atual por caminho permitido, aguardar ou declarar limitação; cache conhecido como superado não é publicado como atual. |
| Cache foi criado com acesso mais amplo | A nova IA não recebe conteúdo, títulos ou caminhos fora de sua autorização. |

Esses cenários foram formulados, não executados. A implementação precisa transformá-los em verificações adequadas ao mecanismo real.

## 11. Checagem de cobertura e situação

| Capacidade planejada | Cobertura lógica |
|---|---|
| Primeiro contato e entrevista | Preparação e ordem em P01/P02; instrumento e roteiro específicos permanecem decisões de conteúdo a verificar antes do uso. |
| Extração para todas as áreas | P02/P06/P07. |
| Busca completa para a questão, incluindo conexões | P04/P05 e critérios de suficiência deste capítulo; não promessa de leitura integral do cofre em todo turno. |
| Perfil, mudanças e correções | P08 com políticas de contexto, origem, tempo e dependências. |
| Sugestões e resultados reais | P09/P10. |
| Pesquisa externa autônoma | P11/P14, com fontes, limites e executor disponível. |
| Continuidade entre IAs | P01, confirmações incrementais e contratos de entrega. |
| Crescimento e evolução dos subfluxos e do manual | P12/P13, incluindo candidatura, promoção e compatibilidade. |
| Eficiência e comunicação | Busca, cache e evolução avaliados sem substituir a evidência completa por leitura rápida; capítulo 05 detalha memória de percursos e custo líquido. |
| Autorrevisão e validação | Checagem dos capítulos, percursos de aceitação e testes futuros. |

O desenho lógico possui uma proposta integrada de regras de interação e decisão. A conferência manual cruzada corrigiu o primeiro contato sem perfil, retomada e cancelamento, linhagem das evidências e indicação de pendências. Os encaminhamentos foram explicitados acima. O registro revisao-logica-processos.md distingue a primeira revisão independente interrompida por limite de uso da revisão posterior de 28 de outubro de 2026, que examinou os capítulos 01 a 05, a proposta de busca e o comparativo de integrações sem encontrar correção lógica bloqueante. Isso não equivale a uma implantação pronta. Valores operacionais, integração efetiva, instrumento inicial, modelo de dados e testes executados permanecem etapas concretas posteriores.
