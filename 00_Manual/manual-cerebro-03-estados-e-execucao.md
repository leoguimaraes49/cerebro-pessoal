# Manual do cérebro pessoal — 03: estados e execução

Versão: rascunho 0.3. Situação: especificação lógica. Nenhum executor foi implementado por este documento. O catálogo de entidades e campos do Obsidian continua reservado para depois da lógica dos processos.

## 1. Finalidade

Definir o que acontece com cada trabalho desde sua criação até o encerramento, inclusive espera, conflito, cancelamento e falha. Os estados pertencem à execução de um processo, não ao usuário ou ao perfil comportamental.

Uma descrição de subfluxo pode ter várias execuções. Revisar a descrição não altera retroativamente a versão usada por uma execução em curso. Uma execução precisa ser identificável para retomar trabalho e reconhecer tentativas repetidas; a representação física será definida posteriormente.

## 2. Estados permitidos

| Estado | Significado | Próximo passo permitido |
|---|---|---|
| Registrada | Demanda reconhecida, ainda sem contrato operacional validado. | Validar contrato, alcance e recursos; encaminhar para fila ou encerrar como falha de preparação. |
| Na fila | Trabalho válido aguardando disponibilidade e prioridade. | Iniciar, suspender conforme comando autorizado ou cancelar. |
| Em execução | Trabalho possui um responsável ativo e realiza etapas permitidas. | Continuar, aguardar condição, suspender, encerrar com resultado, falhar ou iniciar cancelamento. |
| Aguardando | Falta algo específico: resposta, dependência, recurso ou retorno de ferramenta. | Quando a condição ocorrer, revalidar e retornar à fila ou à execução conforme os recursos; encerrar por prazo/falha aplicável ou cancelar. |
| Suspensa | Trabalho deliberadamente parado por comando autorizado ou política explícita. | Revalidar, retornar à fila ou à execução conforme os recursos, ou cancelar. |
| Cancelando | Solicitação de parada recebida; novas etapas estão impedidas e efeitos em andamento estão sendo conferidos. | Encerrar como cancelada após confirmar a parada local e o que ocorreu ou continua incerto. Se o próprio controle da execução falhar, registrar essa falha e a reconciliação necessária. |
| Concluída | O processo entregou o resultado exigido pelo contrato e confirmou os efeitos necessários. | Nenhuma retomada silenciosa. Uma nova demanda origina outra execução. |
| Falhou | O contrato não pôde ser cumprido, incluindo falha de preparação. | Sem continuação automática indefinida; uma tentativa de recuperação deve ser rastreável e limitada. |
| Cancelada | Trabalho local foi encerrado por cancelamento; efeitos já realizados ou chamadas externas ainda incertas estão explicitamente registrados. | Nova demanda para retomar o trabalho. Eventual reconciliação tem responsável próprio; não ressuscitar silenciosamente a execução nem afirmar reversão que não ocorreu. |

Não confundir espera com falha. Falta de acesso a um recurso pode levar a aguardar ou a falhar conforme a tarefa, os prazos e a possibilidade real de recuperação. Espera possui motivo e condição de retorno; não deve ser uma atividade que fica chamando a IA repetidamente.

## 3. Transições e evidência

O executor verifica a transição antes de adotá-la. Uma resposta textual de uma IA não basta para declarar uma gravação concluída. Quando houver efeito externo ou persistente, é necessária a confirmação definida no contrato da ferramenta.

Uma execução pode continuar passando por trechos determinísticos, sem chamar uma IA em todas as transições. O validador básico e a mudança de estado são funções do executor; não geram uma cadeia infinita de novos subfluxos para validar uns aos outros.

Regras centrais:

- Iniciar exige contrato válido, autorização atual, dependências atendidas e limites disponíveis.
- Aguardar exige condição específica de retorno e política para prazo ou perda de relevância.
- Retomar exige verificar de novo acesso, contexto e versões relevantes; não apenas continuar com a memória antiga.
- Concluir exige resultado compatível com o contrato e confirmação dos efeitos declarados.
- Falhar exige registrar o que não foi possível e o que já ocorreu.
- Cancelar exige distinguir a parada de trabalho futuro dos efeitos já confirmados.

Estados terminais não são sobrescritos como se o trabalho nunca tivesse acontecido. Uma nova execução pode referenciar a anterior, respeitando a política de retenção e exclusão.

## 4. Estado operacional e qualidade do resultado

Concluir uma busca não significa comprovar uma hipótese. O resultado da busca pode ser suficiente, limitado, contraditório ou inconclusivo.

Um processo pode cumprir seu contrato entregando uma limitação fundamentada. Isso não equivale a dizer que o objetivo amplo do usuário foi alcançado. A resposta deve preservar essa diferença.

Se uma informação essencial só pode vir do usuário, a tarefa pode aguardar uma resposta. Se não for essencial ou se o contrato permitir encerrar com incerteza, pode apresentar a limitação e concluir. Não insistir infinitamente na mesma pergunta nem usar silêncio como confirmação.

## 5. Responsabilidade, dependências e orçamento

Cada execução tem um responsável ativo. Outro trabalhador não assume a mesma escrita sem um procedimento de transferência ou recuperação. Os mecanismos concretos de coordenação serão definidos no projeto técnico.

Um processo filho recebe um escopo e uma parcela dos limites da demanda que o originou. Criar outro subfluxo não reinicia o orçamento total. Uma dependência só é satisfeita por uma saída válida para o contrato consumidor; estar em estado concluído, isoladamente, não torna qualquer saída adequada.

Antes de executar, devem existir limites definidos para duração, chamadas, passos, profundidade, repetição e custo ou esforço disponível. Os valores serão escolhidos por classe de tarefa na etapa de política operacional. Um limite não configurado não deve ser interpretado como infinito na execução autônoma.

Uma repetição precisa ter finalidade: falha transitória recuperável, informação nova ou estratégia diferente com perspectiva verificável de progresso. Repetir os mesmos dados e a mesma operação sem progresso leva a encerrar ou redirecionar dentro do limite.

## 6. Aplicação, repetição e conflito

Uma gravação tem duas verificações diferentes: se está permitida e se ainda corresponde ao estado sobre o qual foi proposta.

Se outra IA corrigiu a base durante a execução, a versão antiga não pode sobrescrever a nova. O responsável relê o necessário e recalcula a proposta ou deixa o conflito para tratamento específico. A retentativa continua sujeita ao orçamento original.

Se a ferramenta confirmou uma operação e a resposta ao chamador se perdeu, a retomada deve verificar o resultado anterior antes de gravar novamente. O objetivo é evitar efeitos duplicados; não presumir execução exatamente uma vez em qualquer ambiente distribuído.

Quando uma alteração envolve várias partes, deve ser possível reconhecer quais foram confirmadas e quais não foram. A estratégia de atomicidade, reconciliação ou compensação será definida na implementação. O contrato deve impedir uma confirmação de sucesso completo quando só parte foi aplicada.

## 7. Cancelamento, interrupção e retomada

Ao cancelar uma demanda, o executor deixa de iniciar novas etapas e verifica chamadas em andamento. Quando possível, solicita parada aos trabalhadores e ferramentas subordinados. Se algum efeito já foi confirmado, informa-o no registro de encerramento; cancelar não apaga o passado.

Se a chamada externa não puder ser interrompida, o processo acompanha sua confirmação ou registra que o efeito ainda é incerto. A mudança para estado terminal não deve esconder essa incerteza. Trabalho de reconciliação posterior possui responsabilidade explícita.

Após queda de conexão ou reinício:

1. Recuperar o último estado confirmado.
2. Verificar quais efeitos ocorreram de fato.
3. Revalidar permissões e contexto atual.
4. Retomar somente as partes ainda necessárias ou encerrar com motivo.

Retomar uma tarefa não significa reexecutar toda a conversa nem repetir todas as gravações.

## 8. Versões durante a conversa

A execução usa versões conhecidas dos contratos. Uma melhoria adotada normalmente vale para novas execuções, evitando alterar uma sequência no meio sem análise de compatibilidade.

Permissões, exclusões e correções relevantes continuam sendo verificadas: estabilidade de contrato não autoriza continuar usando um dado excluído ou acesso revogado. Quando uma mudança afeta a resposta ou a escrita em preparação, o processo verifica a necessidade de atualizar o contexto antes de publicar o resultado.

Eventos de correção não devem se perder atrás de pesquisas e otimizações de baixa prioridade. A política concreta da fila será detalhada separadamente, mas ela deve impedir uso de um resultado reconhecidamente inválido enquanto a revisão é feita.

A cobertura de um índice ou cache é distinta do estado da execução. Uma execução concluída pode deixar um resultado que depois precisa de revalidação. Acrescentar informação pode exigir uma nova investigação ou reavaliação do trecho afetado, sem reabrir silenciosamente a execução antiga. O capítulo 05 define essa reutilização e o tratamento do atraso entre conhecimento confirmado e derivados atualizados.

## 9. Casos de conferência

| Caso | Comportamento exigido |
|---|---|
| Falta informação pessoal para responder | Perguntar e aguardar, ou encerrar com limitação quando isso atender ao contrato. Não pesquisar na web para inventar a biografia ausente. |
| Uma busca não encontra evidência | Pode concluir operacionalmente com lacuna; não declarar hipótese comprovada. |
| Duas IAs propõem mudanças sobre a mesma versão | Detectar conflito antes de sobrescrever; reconciliar sem perder a correção mais recente. |
| Gravação confirmada, mas a conexão cai | Consultar a confirmação anterior antes de repetir a operação. |
| Cancelamento após parte das gravações | Parar o restante e registrar o que foi confirmado; não anunciar reversão automática inexistente. |
| Processo filho termina com resultado inválido para o pai | Não tratar a dependência como resolvida só pelo estado terminal. |
| Nova estratégia repete as mesmas tentativas | Detectar falta de progresso e encerrar ou redirecionar sob o orçamento compartilhado. |
| Nova versão do subfluxo é adotada durante uma resposta | Preservar a versão da execução, salvo procedimento explícito; revalidar dados e permissões atuais. |
| Recurso de modelo fica indisponível | Aguardar sob condição real de retorno ou falhar com clareza; não prometer trabalho contínuo inexistente. |

## 10. Autorrevisão realizada e limites do capítulo

O desenho foi confrontado com os caminhos de pergunta, correção, troca de IA, pesquisa e evolução do capítulo anterior. Foram explicitadas quatro distinções que evitam contradições: conclusão operacional versus suficiência da evidência; espera versus atividade contínua; cancelamento versus reversão; contrato estável versus permissão e dado atuais.

Essa conferência é uma revisão da especificação, não um teste do software. As regras lógicas de interação e decisão estão detalhadas no capítulo 04. Valores operacionais de implantação, mecanismos físicos de coordenação e cenários executáveis ainda precisam ser definidos e verificados antes do uso autônomo; não são apresentados como já testados. A modelagem final das entidades e campos continua sendo a próxima fase após a consolidação lógica.
