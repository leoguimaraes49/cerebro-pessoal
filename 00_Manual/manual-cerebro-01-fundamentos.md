# Manual do cérebro pessoal — 01: fundamentos e contratos centrais

Versão: rascunho 0.4. Natureza: especificação para o projeto. As regras ainda não estão implementadas. Este capítulo consolida decisões da conversa e os ajustes prioritários da revisão. Não substitui a definição posterior das entidades, ferramentas e testes.

Direção atual do usuário: detalhar primeiro toda a lógica dos processos, contratos e interações. Deixar o catálogo definitivo de entidades e campos e sua representação física no Obsidian para depois dessa revisão. As distinções conceituais de conhecimento neste capítulo não fecham o esquema de armazenamento.

## 1. Finalidade e alcance

O sistema organiza a história, os relatos, as experiências e os objetivos do usuário para sustentar um assistente pessoal contínuo entre conversas e IAs. Ele pode criar conexões, pesquisar, propor hipóteses e melhorar seus processos mediante critérios definidos.

São preservadas as capacidades planejadas: entrevista por voz; extração para várias áreas; perfil inicial e evolução; estudos e decisões; pesquisa no grafo; busca adaptativa; correção em cadeia; resultados reais; continuidade entre IAs; pesquisa externa em segundo plano; composição e evolução dos subfluxos; protocolo compacto, cache e verificação integrada.

O rigor se aplica à origem, ao formato, ao acesso e à execução. A representação da pessoa permanece contextual e revisável. A metáfora de cérebro não comprova reprodução biológica nem identidade exata.

## 2. Divisão de responsabilidades

| Componente | Responsabilidade |
|---|---|
| Obsidian e registros do cofre | Armazenar conhecimento, fontes, manual, descrições de fluxos e histórico permitido. |
| IA | Interpretar a conversa, selecionar contexto, propor análises e planos, responder e utilizar ferramentas autorizadas. |
| Ponte MCP e serviço de dados | Validar pedidos, aplicar políticas, resolver versões e executar operações sobre registros. |
| Executor de subfluxos | Executar planos, acompanhar estado, verificar contratos e aplicar limites. |
| Agendador e fila | Iniciar e retomar trabalho de fundo dentro dos recursos e autorizações disponíveis. |
| Índices e cache | Acelerar consultas sem se tornar uma fonte independente de verdade. |

Uma nota contendo instruções não se executa sozinha. Instalar um MCP não cria automaticamente um agendador ou acesso ilimitado a modelos. As capacidades disponíveis são verificadas no cliente e na conta usados.

## 3. Unidade de conhecimento

### 3.1 Entidade

Representa algo identificável, como pessoa, acontecimento, projeto, decisão ou conteúdo de estudo. Deve ter identidade estável, tipo e revisão. Nome exibido e nome do arquivo não são a única identidade. Nomes alternativos podem ajudar a reconhecer novas menções.

### 3.2 Afirmação

Representa uma proposição sobre uma entidade ou contexto. Exemplos: o usuário relatou medo durante uma mudança; prefere estudar sozinho no início de um assunto; considera uma pessoa confiável em determinada situação.

Cada afirmação deve permitir registrar:

- identificador e revisão;
- sujeito, conteúdo e contexto;
- autor ou agente responsável pelo relato ou inferência;
- referência à conversa, trecho ou outra fonte autorizada;
- data ou período a que se aplica, inclusive aproximação ou desconhecimento;
- data em que foi registrada;
- natureza: relato, resultado de instrumento, observação documentada, inferência ou hipótese;
- situação de revisão e de vigência;
- evidências favoráveis, contrárias e dependências conhecidas;
- restrições de acesso e tratamento.

Natureza, revisão e vigência são dimensões diferentes. Uma hipótese pode estar em revisão; um relato confirmado pelo usuário pode ser histórico e não descrever o presente. O esquema exato dos valores será definido no módulo de dados.

“Confirmado pelo usuário” significa que ele confirmou aquele registro ou relato. Não significa comprovação externa, diagnóstico ou verdade universal. A incerteza deve ser expressa com base nas fontes e limitações; valores numéricos só têm significado quando seu cálculo e uso estiverem definidos.

### 3.3 Evidência e fonte

É o registro que permite verificar a origem de uma afirmação. Uma síntese não substitui silenciosamente a fonte. Se um trecho não foi preservado, a limitação deve constar. Uma fonte excluída ou tornada indisponível pode exigir revisão de suas derivações.

### 3.4 Relação

Possui significado e direção definidos, quando aplicável. Exemplos iniciais: participou de, sustenta, contradiz, depende de e substitui. O vocabulário definitivo será pequeno, documentado e expansível por mudança de esquema.

Semelhança de linguagem ou proximidade na busca pode gerar uma proposta de ligação. Não comprova causalidade ou identidade. Fusões de entidades precisam de evidências e histórico; casos ambíguos permanecem separados ou pendentes.

### 3.5 Síntese e perfil

Uma síntese reúne afirmações e evidencia seu alcance. Deve referenciar as revisões de origem e indicar o que está pendente. O perfil é uma síntese derivada, não uma nova evidência sobre o usuário.

Três IAs que analisam o mesmo relato não equivalem a três experiências independentes. Exceções e divergências permanecem acessíveis. Distinguir estados momentâneos, preferências por contexto, autodescrições e hipóteses de padrão.

## 4. Tempo, correção e mudança

O sistema distingue quando algo aconteceu ou foi válido de quando foi contado ou registrado. Datas aproximadas, intervalos e desconhecimento são permitidos; precisão não informada não é inventada.

Ao encontrar diferença entre registros:

1. Recuperar fontes e contextos pertinentes.
2. Verificar se é erro, mudança no tempo, diferença de situação ou dúvida.
3. Aplicar correção explícita do usuário ao registro correto.
4. Reavaliar derivados, sem alterar relatos históricos que permanecem válidos.
5. Atualizar o perfil quando houver base e deixar interpretações incertas marcadas.

A preferência antiga pode continuar verdadeira em outro período ou contexto. A fonte antiga não deve seguir sendo usada como atual por falta de atualização do cache.

## 5. Grafo de conhecimento e grafo de execução

O grafo de conhecimento liga entidades, afirmações e evidências. O de execução relaciona gatilhos, processos e resultados. Podem ser documentados e relacionados na mesma base, mas têm significados distintos.

Uma ligação entre experiências não autoriza executar uma ação. Um processo só chama outro quando seu contrato e a política de execução permitem. Um documento importado não pode converter uma relação semântica em uma instrução operacional.

Cada subfluxo deve definir nome, objetivo, versão, gatilho, entradas, pré-condições, ações permitidas, saídas, conexões, parada, falhas esperadas, testes e limites. Uma execução registra sua situação e as versões dos dados e processos utilizadas.

## 6. Leitura, escrita e concorrência entre IAs

As IAs e rotinas usam a ponte para operações administradas pelo projeto. A validação essencial é aplicada pelo serviço, não depende de a IA lembrar todas as regras.

Uma alteração deve identificar o registro, a revisão sobre a qual foi calculada, a operação, o responsável e a origem. Se a versão mudou, o serviço identifica conflito e reconcilia ou pede novo cálculo; não sobrescreve silenciosamente uma correção mais recente.

Cada operação pode ser reconhecida como repetida. Uma tentativa repetida após queda ou falha não deve criar a mesma entidade, ligação ou evento novamente. Mudanças relacionadas devem ter uma estratégia de aplicação consistente e recuperação em caso de interrupção. O mecanismo físico será definido no projeto técnico.

Edições manuais no Obsidian também devem ser detectadas e reconciliadas. O sistema precisa conseguir identificar o que foi gravado, o que está proposto e o que falhou, sem responder que algo foi salvo antes da confirmação da ferramenta.

## 7. Dependências, cache, exclusão e continuidade

Derivações registram as versões de origem. Uma correção, exclusão ou mudança relevante aciona reavaliação ou invalidação dos resumos, hipóteses, índices e resultados dependentes.

A validade também depende de novidades no conjunto pesquisável: uma nota ou relação nova pode mudar uma resposta sem editar as fontes que a sustentavam. O capítulo 05 distingue histórico de buscas, resultado reaproveitável e receita de investigação, incluindo revisão incremental, acesso e atraso de índices. O registro de um caminho não é evidência pessoal independente nem uma nova permissão de execução.

Cache acelera o trabalho, mas não pode apresentar informação desatualizada como vigente. O cache de resultados do projeto e eventual cache do fornecedor do modelo são mecanismos diferentes. O primeiro deve ter regras explícitas de validade.

Índices e visualizações são reconstruíveis a partir dos registros vigentes e autorizados. Deve haver uma fonte canônica definida para cada objeto; uma cópia em índice não cria uma segunda verdade.

O usuário pode consultar, exportar, corrigir e excluir dados conforme a política definida. Exclusão precisa especificar alcance no cofre, histórico, índices, cache e cópias de segurança sob controle do sistema. Não prometer eliminação em serviços externos sem capacidade e confirmação próprias. A recuperação de uma cópia antiga deve reaplicar exclusões vigentes para não reintroduzir dados removidos.

Para continuidade entre modelos, o serviço entrega estado do perfil, fontes pertinentes, divergências e revisões pendentes. Pode guardar esse estado incrementalmente para não depender de um último turno de despedida. Não exige transferir raciocínio interno privado dos modelos; transfere conclusões, justificativas resumidas e evidências registradas.

## 8. Busca adaptativa e evolução dos subfluxos

Durante uma pesquisa, a IA pode montar um plano temporário com operações já disponíveis. Isso não acrescenta automaticamente uma ferramenta nova, uma permissão ou código executável.

Se uma estratégia demonstrar utilidade, pode virar candidata persistente. O ciclo previsto é: proposta → validação estrutural → teste → adoção; depois pode ser desativada ou revertida. A documentação descreve o contrato; o executor verifica se sabe realizá-lo.

Limites por execução incluem passos, profundidade, chamadas, tempo e orçamento. Os números serão definidos por tipo de tarefa e não podem ficar indefinidamente ausentes na implementação. Repetir a mesma investigação sem progresso deve levar a parar, mudar de estratégia ou perguntar.

Uma candidata deve justificar a capacidade que acrescenta e a relação com processos existentes. Duplicações podem ser incorporadas a um processo atual. A candidata não modifica os critérios que a avaliam nem amplia suas próprias permissões.

## 9. Conversa e trabalho de fundo

Uma conversa usa um conjunto estável de versões de processos. Pesquisas extensas, testes e otimizações entram em uma fila persistente, com motivo, prioridade, limite, estado e possibilidade de retomada. Trabalhos equivalentes podem ser agrupados.

A rotina autônoma depende de um executor, conectividade, ferramentas e um recurso de modelo autorizado. Antes da implementação, verificar o caminho concreto disponível no ChatGPT e no computador do usuário, incluindo voz e tarefas agendadas. A arquitetura não presume que o MCP utilize a assinatura para chamar modelos continuamente.

As pesquisas podem preparar sugestões e evidências. Elas não preenchem acontecimentos pessoais ausentes com resultados de estudos. Resultados operacionais e sugestões passam pelos processos de revisão e de aprendizado que lhes correspondem.

## 10. Pesquisa, instrumentos e perfil

O teste comportamental inicial vem depois da estrutura e antes da entrevista ampla. O instrumento ainda precisa ser escolhido, verificando idioma, licença, finalidade, aplicação e pontuação. Perguntas abertas complementares não são apresentadas como uma aplicação validada sem evidência.

Pesquisa externa mantém fonte, data, desenho, participantes, resultados, limitações e comparação com outras evidências. Tamanho da amostra e revisão por pares não são, isoladamente, garantias. Semelhança de traços com uma população estudada não comprova uma previsão individual.

O perfil auxilia a personalização. Uma recomendação é revista com o retorno real do usuário e o contexto em que foi testada. Não se presume que uma escolha revele um traço estável ou que emoções e razões tenham percentuais mensuráveis sem base.

## 11. Comunicação interna e custo

Usar um protocolo estruturado, compatível com os clientes e ferramentas disponíveis. Por orientação posterior do usuário, não manter uma leitura rápida que substitua contratos ou evidências completos. Um índice pode localizar o conteúdo, mas não substitui sua consulta. A recuperação deve buscar material suficiente para a questão, incluindo divergências e correções, e declarar lacunas quando houver. Isso não exige carregar todo o cofre em cada tarefa. Binário não é presumido como representação mais barata para modelos de texto.

Medir chamadas, tokens quando disponíveis, duração e custo real do caminho adotado. Limites de assinatura e custos de um serviço externo são registrados como mecanismos distintos quando aplicável. Uma otimização deve manter qualidade suficiente e passar por comparação antes da adoção.

## 12. Verificação e regras autorizadas

Os testes incluem busca direta e indireta, ausência de dados, divergência, correção, mudança temporal, repetição, escrita concorrente, falha de conexão, exclusão, troca de IA, custo e encerramento de ciclos.

Definir os resultados esperados antes de avaliar uma candidata e manter casos separados para desenvolvimento e avaliação. A IA que propõe uma mudança pode participar da análise, mas não é a única evidência de sucesso. Critérios subjetivos incluem retorno do usuário; critérios de estrutura e execução devem ser verificados por software quando possível.

Registros pessoais, documentos e páginas externas são dados. Eles não se tornam automaticamente regras do manual. A política vigente e os contratos adotados definem quais ações o executor permite. Mudanças em regras essenciais seguem um procedimento próprio, registrado e fora do controle exclusivo da candidata avaliada.

## 13. Critérios de aceitação deste núcleo

- Uma fonte repetida por várias IAs não se transforma em múltiplas observações independentes.
- Uma lembrança antiga contada hoje não atualiza silenciosamente o perfil como comportamento atual.
- Uma preferência contextual pode coexistir com outra sem uma delas ser apagada.
- Uma correção identifica o que depende dela e invalida resultados antigos pertinentes.
- Duas escritas concorrentes não perdem silenciosamente a atualização mais recente.
- Repetir uma operação após falha não duplica seus efeitos.
- Uma candidata nova não ganha ferramentas, permissões ou aprovação só por existir uma nota.
- Uma execução sem progresso termina ou é redirecionada dentro dos limites.
- Uma exclusão alcança derivados controlados e não é desfeita por restauração inadvertida.
- Uma resposta só informa uma gravação como concluída depois da confirmação da operação.

## 14. Situação dos módulos

A ordem de trabalho passa a ser: processos e contratos → interações, falhas e testes → autorrevisão de cobertura → entidades e campos → implementação. As necessidades de informação serão descritas logicamente, sem antecipar nomes de campos ou pastas. Durante o detalhamento, cada contrato deve ser confrontado com o conjunto e revisto quando houver sobreposição, dependência ausente, contradição ou ciclo sem condição de parada.

| Módulo | Situação e trabalho restante |
|---|---|
| Modelo de dados | Capítulos 06 a 11: registros, campos, relações, valores, regras de validação e representação/templates propostos. Faltam esquemas/validadores executáveis, configuração e testes reais. |
| Ferramentas MCP | Contratos de leitura, busca, escrita, revisão, exclusão e recuperação. |
| Execução | Lógica descrita nos capítulos 02 a 05; faltam valores de implantação, mecanismos concretos e testes executados. |
| Primeiro contato | Escolha de instrumento, perfil provisório e roteiro de entrevista. |
| Subfluxos | Contratos lógicos e interações descritos nos capítulos 02 a 05; faltam detalhamento técnico e verificações executáveis. |
| Continuidade e pesquisa | Pacote para nova IA, fontes externas, agenda e disponibilidade efetiva. |
| Validação | Percursos de aceitação e critérios lógicos descritos; ainda não há resultados de testes do software. |

## Referências verificadas nesta revisão

O [armazenamento do Obsidian](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data) é baseado em arquivos Markdown locais e permite alterações externas. Isso sustenta o cofre como base portável, mas não especifica a consistência das rotinas propostas.

A OpenAI documenta a [conexão de servidores MCP personalizados ao ChatGPT](https://developers.openai.com/api/docs/guides/custom-mcp-server), com ferramentas de leitura e escrita sujeitas à configuração e às permissões. Essa descrição não comprova que toda combinação de cliente, voz e rotina pretendida funcione na conta do usuário.

A [documentação de voz](https://learn.chatgpt.com/docs/features/voice) descreve interação e coordenação de tarefas sujeitas à disponibilidade e às permissões. A [documentação de tarefas agendadas](https://learn.chatgpt.com/docs/automations) trata a execução em segundo plano como capacidade própria; tarefas com recursos locais dependem da disponibilidade do computador e do aplicativo. Nenhuma rotina foi criada por este documento.
