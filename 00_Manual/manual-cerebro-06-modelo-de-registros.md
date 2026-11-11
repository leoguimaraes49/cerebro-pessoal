# Manual do cérebro pessoal — 06: modelo inicial de registros e avaliação

Versão: rascunho 0.2. Data: 28 de outubro de 2026. Situação: modelagem inicial, sem cofre criado, formulários aplicados, resultados pessoais ou integração implementada. Este capítulo começa a fase de dados a partir dos processos consolidados. Os nomes técnicos são propostas de esquema; ainda não há um validador executável.

## 1. Prioridade e ordem

O usuário reafirmou a avaliação inicial antes da entrevista ampla. A modelagem começa pelo núcleo que registra instrumentos, respostas, resultados, interpretações e perguntas de acompanhamento. A avaliação pretende orientar a personalização e a entrevista; a conversa posterior acrescenta experiências, contextos e exceções.

A escolha de instrumento deve considerar sua versão, finalidade, condições de uso e adequação ao contexto.

Preparar os registros necessários não equivale a já aplicar instrumentos. Quando a avaliação acontecer, suas respostas devem ter um destino verificável. Se for conduzida antes da integração, o local autorizado de registro e a migração posterior precisam ser explícitos; não alegar gravação automática no Obsidian.

## 2. Famílias de registros

| Família | O que representa | Regra central |
|---|---|---|
| Entidade de domínio | Pessoa, lugar, experiência, decisão, projeto ou conteúdo identificável. | Identidade não depende do título do arquivo. |
| Afirmação | O que foi relatado, observado ou inferido sobre algo. | Conteúdo, origem, contexto, tempo e natureza são rastreáveis. |
| Fonte | Conversa/trecho, documento, observação registrada ou publicação. | Permite localizar a evidência e a revisão efetivamente consultada. |
| Síntese | Perfil provisório, padrão sugerido ou síntese de evidências. | É derivada, com bases e exceções; não cria observação independente. |
| Questão | Informação faltante ou divergência a esclarecer. | Tem finalidade, dependências e condição de resolução. |
| Instrumento e aplicação | Definição de um instrumento e uma realização individual. | Versão do instrumento não se confunde com resposta, pontuação ou interpretação. |
| Registro operacional | Processo, execução, operação, mudança, busca, resultado ou receita. | Descreve funcionamento, sem se converter automaticamente em biografia. |

Uma relação semântica será uma afirmação relacional referenciável. Um link de navegação pode apontar para ela ou para suas entidades, mas não comprova sozinho o vínculo. Um mesmo acontecimento pode aparecer nas visões de diário, estudos e decisões sem se tornar três evidências.

## 3. Núcleo comum de campos

| Campo proposto | Necessidade e regra |
|---|---|
| `id` | Identidade estável e única do registro, independente de nome/pasta. |
| `record_type` | Família do registro; subtipo explícito quando houver. |
| `schema_version` | Versão das regras usadas para interpretar o registro. |
| `revision` | Revisão do registro, distinta da versão de esquema. |
| `title` | Nome exibido; pode mudar sem alterar identidade. |
| `created_at`, `updated_at` | Datas técnicas de criação e alteração; não representam a data do acontecimento. |
| `created_by` | Responsável pela criação; não equivale necessariamente ao autor da informação. |
| `access_policy_ref` | Política que determina quem pode receber ou alterar o conteúdo. |
| `lifecycle_status` | Situação do registro: ativo, arquivado ou substituído, conforme sua família. Exclusão segue política própria. |

Referências utilizadas como base de uma derivação identificam registro e revisão, com localização de trecho quando aplicável. Uma referência ao registro atual não reproduz automaticamente sua versão antiga. Se a fonte ou o trecho já não estiver disponível, representar essa limitação.

O identificador de uma operação repetível é distinto do identificador da entidade alterada. Duas tentativas da mesma gravação não criam duas pessoas ou experiências. Edição externa precisa ser detectável pelo mecanismo técnico posterior, inclusive quando alguém não atualiza manualmente a revisão no cabeçalho.

Campos desconhecidos não recebem valores inventados. A representação distinguirá desconhecido, não perguntado, não aplicável e resposta recusada quando essa diferença influenciar o uso. Isso não se reduz a colocar zero em toda ausência.

## 4. Afirmações, relações e tempo

Campos específicos necessários: sujeito; predicado; alvo referenciado ou valor; natureza; autor da afirmação; fontes ou bases da inferência; contexto; período de ocorrência ou vigência; situação de revisão; afirmações contrárias ou alternativas; dependências e restrições.

Natureza distingue relato, observação documentada, resultado de instrumento e inferência/hipótese. Revisão distingue ainda não revisado, confirmado pelo usuário, contestado ou pendente de esclarecimento. Vigência distingue o período/contexto a que se aplica. Essas dimensões não são um único rótulo de confiança.

Confirmado pelo usuário significa que ele confirmou a fidelidade daquele registro ou relato. Isso não valida o instrumento, o cálculo ou uma conclusão clínica. Uma revisão de conteúdo identifica responsável, momento e revisão examinada; uma alteração técnica de arquivo não equivale a essa revisão.

Datas podem ser precisas, aproximadas, intervalares ou desconhecidas. Guardar quando algo aconteceu e quando foi contado. Correção de uma palavra transcrita aponta à fonte e às extrações afetadas; mudança de preferência aponta aos períodos e situações pertinentes. Não transformar uma retificação em mudança de personalidade.

Relações iniciais precisam separar: participação e contexto; apoio ou contradição entre afirmações; derivação de uma síntese; substituição por correção; dependência de execução; e navegação. O vocabulário tipado e as restrições de sujeito/alvo serão detalhados junto aos subtipos. Uma associação candidata não ganha o estatuto de relação confirmada porque apareceu num gráfico.

## 5. Catálogo de domínio a detalhar

| Área | Registros centrais | Informações que devem permanecer atribuídas/contextuais |
|---|---|---|
| Pessoas e relações | Pessoas, grupos, organizações e afirmações relacionais. | Impressões sobre uma pessoa pertencem ao relato de quem as expressou. |
| História de vida | Experiências, lugares e períodos. | Data aproximada, participantes e perspectivas sobre o acontecimento. |
| Diário | Entradas ou visões diárias que referenciam fontes e experiências. | Pensamentos e emoções daquele contexto não definem automaticamente traços estáveis. |
| Identidade e preferências | Valores, objetivos, interesses e afirmações de preferência. | Autodescrição, prioridade atual e hipótese de padrão permanecem distintas. |
| Decisões e ações | Decisão, alternativas, ação realizada e resultado documentado. | Razões relatadas, emoção declarada e explicação inferida não se confundem. |
| Hábitos e rotina | Padrão proposto e ocorrências observadas/relatadas. | Frequência e exceções precisam de base; ausência de relato não é ausência de comportamento. |
| Estudos | Conteúdo, objetivo, sessão, método e evidência de aprendizagem. | Autoavaliação de domínio é distinta de desempenho demonstrado. |
| Projetos | Projeto, tarefa e entregas/resultados. | Estado planejado não equivale a ação concluída. |
| Recomendações e experiências práticas | Sugestão, tentativa e retorno. | Resultado inclui condições e alternativas explicativas. |
| Autoconhecimento e saúde relatada | Aplicações, respostas, resultados, relatos e documentos autorizados. | Rastreamento, hipótese, diagnóstico relatado e documento profissional permanecem separados. |

Nem toda emoção ou frase exige uma entidade independente. Uma afirmação contextual pode bastar; uma ideia persistente e reutilizável pode justificar entidade própria. Tipos novos passam por evolução de esquema e compatibilidade, sem classificação improvisada e silenciosa.

## 6. Modelo do instrumento

A definição do instrumento precisa identificar: nome e finalidade; construtos; autores e fonte original; versão; idioma e responsável pela adaptação; população/faixa etária; evidências e limites de validade; condições de uso; instruções; respostas permitidas; chave e regras de pontuação; tratamento de ausências; e modalidade de aplicação estudada.

Disponibilidade na internet, autorização de reprodução e adequação científica são verificações diferentes. Uma tradução existente não comprova equivalência para a população ou aplicação por voz. Não assumir que licença de um artigo se estenda a um instrumento de terceiros.

A seleção pode terminar como disponível para o uso pretendido, dependente de verificação ou inadequada a esse uso. Essa é uma decisão sobre o instrumento, não sobre a pessoa. Questionário de autorreflexão próprio, se utilizado, é identificado como tal e não recebe o nome ou a validade de um instrumento padronizado.

## 7. Modelo de uma aplicação individual

| Conjunto de campos | Conteúdo necessário |
|---|---|
| Identificação | Instrumento e versão, pessoa avaliada no escopo autorizado, finalidade e aplicação individual. |
| Condições | Data, idioma, modalidade, instruções apresentadas, pausas, ajuda e adaptações ocorridas. |
| Respostas | Identidade do item, resposta recebida, fonte/trecho, revisão e eventual retificação. |
| Estado e completude | Aplicação não iniciada, em curso, interrompida ou concluída; respostas faltantes explícitas. |
| Elegibilidade para pontuação | Calculável, não calculável ou pendente de verificação segundo a regra identificada, com motivo. Aplicação concluída pode não permitir pontuação válida. |
| Pontuação | Regra e versão de cálculo, referências às revisões exatas das respostas utilizadas, dimensões calculadas e limitações. Não preencher resultado quando a regra não permitir. |
| Interpretação | Leitura descritiva do resultado, contexto, limites e hipóteses; separada do cálculo. |
| Acompanhamento | Perguntas abertas pertinentes, prioridade e o que cada resposta pode esclarecer. |

Os estados de aplicação são específicos desse registro; não substituem os estados de execução do capítulo 03. Uma execução pode concluir registrando uma aplicação interrompida e um resultado não calculável.

Uma retificação relevante das respostas marca pontuação e interpretação dependentes para revalidação; o perfil não continua usando como atual um resultado conhecido como superado. Conservar a ligação à base anterior conforme a retenção autorizada. Resultado não calculável não significa escore zero, ausência de sintomas ou diagnóstico.

Preservar os itens e opções da versão escolhida quando a aplicação depender de padronização. Explicação, paráfrase ou resposta inferida pela IA não deve ser incorporada como se tivesse sido produzida pelo participante na modalidade original. Retificações de transcrição exigem confirmação quando alterarem o sentido. Não ajustar a resposta para fazê-la combinar com o perfil anterior.

## 8. Perfil inicial, rastreamento e informação clínica

O perfil inicial é uma síntese provisória. Contém as dimensões efetivamente observadas, referências às aplicações e relatos, contextos, exceções e perguntas abertas. Dimensões não avaliadas permanecem assim identificadas. O perfil não é um retrato completo do funcionamento cerebral.

Um resultado de rastreamento pode indicar sinais a investigar. Não cria uma afirmação de diagnóstico. Um diagnóstico que o usuário relate é registrado como relato atribuído; um documento profissional autorizado tem origem própria. A IA não preenche a ausência de avaliação clínica com sua opinião acumulada.

Relatos posteriores contextualizam e podem contrariar interpretações. Um escore não prova a causa de uma decisão específica. Essa ligação, se levantada, permanece hipótese ligada às situações e às alternativas explicativas.

Se o objetivo for esclarecer uma possível condição clínica, o sistema pode organizar informações úteis para avaliação por profissional qualificado. Sugestões cotidianas podem ser personalizadas pelas dificuldades e preferências relatadas, sem exigir atribuir primeiro um diagnóstico à pessoa.


## 9. Entrevista e sugestões orientadas por contexto

Depois da etapa inicial escolhida, a entrevista procura exemplos, períodos, impacto cotidiano, estratégias já tentadas, objetivos e exceções. Perguntas não devem pressupor que o resultado do rastreamento seja um diagnóstico ou que uma interpretação anterior esteja correta.

Cada resposta pode produzir fontes, experiências, afirmações, relações ou questões segundo P02/P06/P07. A mesma fonte pode informar várias áreas, mas continua uma origem de evidência. P08 revisa o perfil, e P10 aprende com resultados de sugestões efetivamente experimentadas.

Para uma situação cotidiana, P04 recupera contexto pessoal e fontes externas já armazenadas; P11 pesquisa quando existir lacuna ou necessidade de atualização. A síntese externa registra o que os estudos permitem concluir e sua aplicabilidade. A recomendação liga contexto e evidência sem presumir que uma pesquisa populacional descreva o indivíduo. O retorno real pode justificar revisão futura.

## 10. Registros operacionais e busca

Os registros de processo, execução, operação confirmada, evento de alteração, pesquisa realizada, resultado reutilizável e receita de investigação precisam de identidades e versões próprias. Não pertencem à mesma categoria de experiências da pessoa.

Uma busca registra objetivo, escopo, cobertura dos índices, revisões e operações observadas, resultados, lacunas e motivo de encerramento. Um resultado reutilizável representa sua condição de validade atual; uma receita representa um modo de investigar, com compatibilidade e situação de adoção. Informação nova pode exigir revalidação sem dependência anterior conhecida.

A representação precisa permitir localizar derivados atingidos por correção/exclusão e reconhecer diferenças entre a versão da base e a versão coberta pelos índices. Esses campos serão detalhados no submodelo operacional a partir dos capítulos 03 e 05; não são garantias já implementadas.

## 11. Acesso e representação no Obsidian

Respostas a instrumentos e resultados podem revelar informação pessoal sensível. Títulos, ligações, consultas, hipóteses e perfil derivado recebem políticas compatíveis com o conteúdo que expõem. Um resumo não ganha acesso mais amplo só por ser mais curto. Exclusão considera cópias e derivados controlados, sem reintrodução pela restauração de versão antiga.

A proposta física é usar registros canônicos portáveis, com identidade independente do caminho; índices e visões são derivados. O detalhamento posterior definirá como cada família vira arquivo, bloco ou registro operacional, evitando impor um arquivo visível por evento de ferramenta.

O Obsidian documenta propriedades em YAML e links internos; seu editor de propriedades tem limitações para estruturas aninhadas. Por isso, o modelo lógico não deve presumir que toda referência complexa caberá como objeto editável na interface de propriedades. [Propriedades do Obsidian](https://obsidian.md/help/properties), [links internos](https://obsidian.md/help/links). Nomes alternativos podem auxiliar navegação, sem substituir identidade: [aliases](https://obsidian.md/help/aliases).

## 12. Conferência e próximos detalhamentos

A revisão de requisitos conferiu identidade/revisão, reutilização de uma experiência em várias áreas, distinção de fonte e instrumento, contexto temporal, acesso dos derivados e memória operacional. A revisão do capítulo acrescentou separação entre completude e elegibilidade para pontuação, referências às revisões das respostas e alcance preciso da confirmação do usuário. Este primeiro capítulo incorpora essas necessidades; ainda não é um esquema executável ou um catálogo fechado de todas as propriedades.

Os campos por subtipo, valores, submodelo operacional, relações/validações e representação com templates foram detalhados nos capítulos 08 a 11. Eles constituem especificação declarativa, não software executado. Permanecem a seleção documentada dos instrumentos, implementação dos esquemas e mecanismos reais, configuração de implantação e testes com exemplos fictícios/autorizados. A criação do cofre, a integração e a primeira aplicação ainda não ocorreram.
