# Manual do cérebro pessoal — 05: memória de buscas e evolução dos caminhos

Versão: rascunho 0.1. Data: 28 de outubro de 2026. Situação: especificação lógica; nenhuma rotina foi implementada ou testada em execução. Este capítulo estende P04/P05 e P07/P12/P13/P14, sem acrescentar um processo central redundante. Entidades, campos, pastas e banco concreto continuam para a fase posterior.

## 1. Decisão de arquitetura

A busca híbrida está escolhida como arquitetura: recuperação por texto, por significado e por relações do grafo. O roteamento combina os métodos pertinentes ao pedido; não exige executar três buscas completas em toda pergunta. Os algoritmos e produtos concretos serão comparados na implementação.

As notas e fontes completas autorizadas permanecem a referência. Índices lexicais, vetoriais e de relações são derivados reconstruíveis. A memória dos caminhos ajuda a localizar e investigar; não substitui a leitura do material necessário nem introduz uma leitura rápida no lugar do manual completo.

O sistema evolui uma versão de processos por vez. Concluir esta especificação inicial não congela a arquitetura: P12/P13 continuam permitindo melhorias verificadas e publicação coerente do manual e do funcionamento.

## 2. Três coisas que precisam permanecer distintas

| Material | Finalidade | Condição de uso |
|---|---|---|
| Registro de uma busca realizada | Mostrar objetivo, operações realizadas, fontes consultadas, relações percorridas, lacunas e desfecho observável. | É histórico operacional, não prova de que a conclusão continua válida. |
| Resultado reaproveitável | Evitar repetir trabalho quando o pedido e as condições continuam compatíveis. | Exige conferir acesso, contexto, versões, novidades pertinentes e suficiência para o pedido atual. |
| Receita de investigação | Reutilizar uma sequência útil de consultas e verificações em tarefas compatíveis. | Orienta uma nova execução; não transporta automaticamente a conclusão anterior. |

O registro pode incluir o motivo verificável de um encaminhamento, como uma fonte encontrada, uma correção ou uma lacuna. Não depende de obter o raciocínio interno privado do modelo. O percurso deve distinguir relações já existentes, associações propostas e alterações realmente confirmadas.

## 3. Quando guardar um caminho

O executor mantém continuidade operacional suficiente para retomar uma busca e reconhecer tentativas repetidas, conforme a retenção autorizada. Ao concluir ou interromper uma investigação relevante, registra o que foi efetivamente consultado e confirmado. Falhas úteis e buscas inconclusivas também podem ser preservadas para evitar repetir tentativas improdutivas.

Uma receita persistente se justifica quando há uma sequência reutilizável, problema recorrente ou benefício demonstrável. Não criar uma nova entidade biográfica ou um novo subfluxo para cada execução. Percursos equivalentes podem compartilhar uma receita e manter referências separadas aos resultados de cada execução.

O conteúdo necessário ao contrato inclui objetivo e contexto, operações e filtros, fontes e revisões consultadas, relações percorridas, limitações, motivo de encerramento e compatibilidade conhecida. São necessidades lógicas; este capítulo não define campos físicos. Credenciais e conteúdo fora da retenção permitida não entram no histórico.

## 4. Persistência e responsabilidade

P03 autoriza e delimita a coleta operacional. P04/P05 entregam os eventos observáveis ao mecanismo de registro do executor. Esse mecanismo segue as garantias aplicáveis de P07: autorização, reconhecimento de repetição, confirmação de efeito e recuperação. Registrar uma linha operacional não exige chamar outra IA nem criar uma proposta semântica sobre a pessoa.

O registro não concede permissão para alterar o conhecimento. Uma hipótese pessoal encontrada segue P06/P07/P08. Uma receita nova adotável segue P12/P13; sua publicação usa P07. A escrita de histórico não é, por si só, um evento de nova experiência pessoal nem gatilho para repetir a própria busca.

Se a persistência obrigatória para recuperação falhar, a execução não declara esse requisito atendido. Quando for uma parte complementar do pedido, a resposta pode continuar com a limitação registrada. Essa distinção é definida no contrato antes da execução.

## 5. Como reutilizar

1. Interpretar o objetivo atual e o escopo autorizado antes de procurar no histórico.
2. Localizar resultados ou receitas compatíveis. Similaridade textual ou vetorial seleciona candidatos; não comprova equivalência de tarefa, identidade, período ou intenção.
3. Conferir permissões atuais, contexto, versões de fontes, contratos, ferramentas e índices relevantes, além de mudanças no conjunto pesquisável.
4. Escolher entre reutilizar o resultado validado, atualizar o trecho afetado, executar a receita como investigação nova ou refazer a recuperação mais ampla.
5. Recuperar evidências completas pertinentes e procurar exceções, correções e contradições. Se faltar detalhe essencial dependente do usuário, perguntar e aguardar conforme o capítulo 04.
6. Entregar o resultado com as limitações reais e registrar somente os efeitos confirmados. Repetição após falha não duplica histórico ou conhecimento.

Uma nova IA pode usar a mesma memória operacional autorizada, mas precisa conferir compatibilidade. A troca não transfere automaticamente os estados internos do modelo nem torna uma interpretação anterior mais confiável.

## 6. Quando entra informação nova: revisão a partir do ponto afetado

Uma fonte nova pode reforçar, contradizer ou ampliar uma resposta anterior. Um novo vértice ou uma nova aresta pode alcançar uma pergunta por conexões indiretas; uma nota ainda sem ligações pode ser relevante por texto ou significado. Por isso, verificar apenas se as fontes antigas foram editadas é insuficiente.

Após uma mudança confirmada, o sistema identifica os resultados e as receitas possivelmente afetados usando dependências conhecidas, alterações de relações e mudanças no escopo recuperável. Quando o alcance puder ser delimitado com confiança operacional suficiente, reavalia a parte afetada e suas consequências necessárias. Se o mecanismo não conseguir delimitar o alcance, marca os resultados candidatos como pendentes de revalidação e amplia a recuperação antes de usá-los como atuais.

Não se deve restringir a revalidação às notas do caminho anterior: isso perderia uma experiência relevante registrada em outra área. A investigação inclui uma saída para descoberta por texto, significado e novas relações. Uma busca antiga sem resultados também perde validade quando material pertinente é acrescentado.

O mecanismo de impacto depende da implementação. É permitido começar com invalidação conservadora de um escopo maior e só adotar seleção mais precisa após testes. Não prometer que toda novidade será reconhecida por uma heurística sem erros.

## 7. Atualização, concorrência e índices atrasados

Ao confirmar uma correção, exclusão ou outra mudança material, P07 deve tornar reconhecível que os derivados pertinentes precisam de revalidação. Esse sinal não pode depender apenas de uma tarefa de baixa prioridade que talvez execute depois.

A atualização pesada dos índices e das conclusões pode ocorrer em fila. Enquanto houver atraso, a busca deve reconhecer a diferença entre a versão do conhecimento e a cobertura disponível dos índices; consultar uma fonte atual por outro caminho permitido, aguardar a atualização ou declarar a limitação. Não publicar um cache conhecido como superado só porque a reindexação ainda não terminou.

Antes de publicar uma resposta ou aplicar uma proposta dependente, conferir mudanças materiais ocorridas durante a investigação. A consistência exigida e o modo de conferir serão definidos no contrato técnico; este capítulo não presume que simples leitura seguida de escrita seja uma operação atômica.

Prazo de validade auxilia manutenção, mas não substitui controle de revisões, acesso e novidades. Alterações de modelo de embeddings exigem compatibilidade ou reconstrução coerente das representações; receitas textuais podem continuar úteis se seus contratos permanecerem válidos.

## 8. Permissões, exclusão e retenção

O próprio histórico pode conter perguntas íntimas, títulos, caminhos e trechos de notas. Seu acesso precisa ser filtrado no uso atual, inclusive quando outra IA tem permissões menores. Um resultado gerado com acesso amplo não pode revelar conteúdo restrito por meio do cache.

Correção, exclusão e revogação alcançam cópias e derivados sob controle do sistema. Manter um registro de que houve uma operação não autoriza conservar conteúdo excluído. Restaurações respeitam a política de exclusão vigente, e a retenção deve ser compatível com a capacidade concreta do armazenamento e das cópias de segurança.

Consolidar receitas equivalentes, limitar detalhes dispensáveis e remover resultados obsoletos conforme a política. Não guardar indefinidamente todos os conteúdos de toda consulta por padrão. Preservar fontes completas necessárias e histórico autorizado é distinto de manter cópias integrais em cada registro operacional.

## 9. Aprimoramento dos caminhos

As execuções fornecem observações de utilidade, falhas, custo e contexto. P12 pode propor ajuste de consulta, sequência, índice, expansão do grafo ou formato de comunicação. P13 compara a candidata com a versão vigente em tarefas repetidas e novas, incluindo correções e exceções.

Uma receita popular não ganha promoção apenas por ser muito usada. Ela pode repetir um viés ou deixar de descobrir novidades. Repetir a mesma conclusão tampouco adiciona evidência pessoal independente. O sistema mantém saídas para investigação normal/adaptativa e reavalia estratégias que perderam utilidade.

Melhorias adotadas atualizam processo, documentação e dependências de forma coerente, com possibilidade de recuperação. A candidata não altera seus critérios de aprovação nem amplia suas permissões. Dados pessoais e páginas externas continuam sendo fontes, sem autoridade para mudar essas regras.

## 10. Economia e critérios de qualidade

A hipótese é reduzir trabalho repetido em tarefas compatíveis. Medir o custo de localizar, validar, ler, registrar, atualizar e testar, além das chamadas de modelo e buscas evitadas. Considerar também indexação, armazenamento e manutenção. O custo por tarefa recorrente pode cair sem que o custo total de uma base crescente diminua.

Treinar este sistema, nesta fase, significa alimentar memória, corrigir perfil e melhorar estratégias. Não significa treinar os pesos dos modelos usados. A escolha de um banco vetorial ou a existência de cache não comprova economia por si só.

Uma otimização precisa preservar recuperação das fontes, correções, exceções, tratamento de lacunas e acesso às evidências completas necessárias. Se consumir mais do que economiza ou degradar esses critérios, deve ser ajustada, mantida como candidata ou desativada.

## 11. Cenários de aceitação a implementar

| Cenário | Resultado exigido |
|---|---|
| Mesmo pedido, contexto e base compatíveis | Reaproveitar o trabalho validado e medir se houve economia líquida. |
| Perguntas parecidas com objetivos distintos | Usar a receita se pertinente, sem herdar a recomendação anterior. |
| Nova nota contradiz resposta sem editar as fontes antigas | Recuperar a novidade ou reconhecer a cobertura incompleta antes de reutilizar. |
| Nota nova relevante ainda não tem arestas | A recuperação por texto/significado permite encontrá-la; grafo antigo não encerra a busca sozinho. |
| Mudança afeta somente parte de uma investigação | Atualizar o trecho delimitado e reavaliar suas consequências; ampliar se o alcance não for confiável. |
| Correção ocorre antes de terminar a indexação | Resultado conhecido como antigo fica impedido de uso atual; atraso é reconhecido. |
| Permissão menor ou exclusão após gerar cache | Histórico não expõe títulos, caminhos ou conteúdo proibidos. |
| Falha após salvar o percurso | Retomar sem duplicar o registro nem reforçar uma hipótese pela repetição. |
| Receita retorna sempre às mesmas notas | Descoberta de exceções e caminhos novos continua possível. |
| Mudança de ferramenta, contrato ou embeddings | Revalidar compatibilidade e reconstruir o necessário. |
| Pergunta exige informação pessoal ausente | Perguntar ao usuário e manter pendência; receita não inventa a resposta. |
| Registro de histórico gera evento de manutenção | Agrupar e encerrar sem ciclo de autorregistro e novas buscas. |

Os cenários foram especificados, não executados. Os testes concretos e a representação física serão definidos com a integração e o modelo de dados.
