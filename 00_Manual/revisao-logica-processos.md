# Revisão cruzada dos processos

## Alcance

Conferência manual dos capítulos 01 a 04, realizada após sua leitura integral. Foram comparados responsabilidades, gatilhos, entregas, estados, dependências e os caminhos de primeiro contato, pergunta, correção, troca de IA, pesquisa e evolução. Trata-se de revisão da especificação. Nenhum teste de software ou integração foi executado.

A primeira revisão independente delegada terminou com erro de limite de uso antes de fornecer análise. Esse episódio não constitui parecer aprovado. Uma rodada posterior sobre memória de buscas entregou seis observações específicas, incorporadas no capítulo 05 e nos contratos relacionados. A revisão final de 28 de outubro de 2026 examinou os capítulos 01 a 05, a proposta de busca híbrida e a avaliação das integrações; não encontrou correção lógica bloqueante para esta versão inicial. Nenhuma dessas revisões é teste de software nem garantia de ausência de falhas.

## Ajustes incorporados

| Achado | Ajuste |
|---|---|
| Primeiro contato aparecia na sequência sem explicar como iniciar antes do perfil. | P01 aceita perfil ausente. P03 coordena preparação e instrumento; P02 recebe respostas; P06/P07/P08 registram o perfil provisório antes da entrevista ampla. |
| O texto de P08 podia sugerir que diferentes IAs tornavam as evidências independentes. | A regra passou a exigir preservação da linhagem e identificação de fontes compartilhadas. |
| Retomada após espera não explicitava o retorno à fila quando faltassem recursos. | As transições de espera e suspensão agora incluem revalidação e escolha entre fila e execução. |
| Cancelamento misturava impossibilidade de confirmar efeito externo com falha de controlar a execução. | Distinguidos encerramento local, efeitos confirmados, efeitos incertos e responsabilidade de reconciliação posterior. |
| Os encaminhamentos estavam descritos em exemplos, sem uma matriz geral. | Acrescentada tabela de solicitações entre P01 e P14, sujeita ao coordenador, contratos, permissões e orçamento. |
| Capítulos antigos ainda listavam como ausentes regras já escritas nos capítulos posteriores. | Atualizadas as referências e separadas especificação lógica, configuração de implantação e testes ainda não executados. |

## Cobertura conferida

- Origem, contexto e revisão das afirmações: capítulos 01 e 02.
- Separação de conhecimento e execução: capítulos 01 e 04.
- Extração, busca e investigação adaptativa: P02 a P06.
- Escrita, conflito, repetição e confirmação: P07 e capítulo 03.
- Perfil, mudanças temporais e correção de derivados: P08, capítulos 01 e 04.
- Sugestões e resultados reais: P09/P10.
- Pesquisa externa e rotina de fundo: P11/P14.
- Continuidade entre IAs: P01 e registros confirmados de origem.
- Evolução de processos, protocolo e manual: P12/P13.
- Condições de parada, orçamento compartilhado e prevenção de ciclos: capítulos 03 e 04.
- Verificação de entregas incompletas e casos de aceitação: capítulo 04.

Essa cobertura registra onde as regras foram especificadas; não comprova que uma implementação as satisfaz nem que o desenho não possa ter outras falhas.

## Pendências concretas

1. Modelar entidades, campos, relações e representação no cofre, depois da revisão lógica conforme a ordem do usuário.
2. Definir contratos técnicos de ferramentas e verificar leitura, escrita e disponibilidade no cliente MCP e no modo de voz efetivamente usados.
3. Configurar valores de recursos, fila e execução compatíveis com o ambiente. As regras já exigem limites finitos; os valores ainda não foram medidos ou adotados.
4. Escolher o instrumento de autoconhecimento e seu roteiro de aplicação, antes da avaliação inicial e da entrevista ampla.
5. Detalhar os critérios operacionais para avaliação de fontes externas e o acesso a pesquisas.
6. Construir e executar testes de contratos e integração, além da comparação de busca lexical, semântica e em grafo.
7. Manter revisões futuras quando o esquema, as ferramentas ou os processos mudarem; a rodada atual de revisão independente da lógica foi concluída, sem equipará-la à validação do software.

## Rodada de consolidação da memória de buscas

O usuário aceitou a busca híbrida e pediu preservar os percursos úteis para reduzir trabalho futuro. Também esclareceu que a informação nova pode exigir reavaliação a partir do vértice ou da relação afetada e que a versão inicial deve continuar evolutiva. Não existem buscas reais desse sistema para servir de histórico nesta fase; os percursos de aceitação são cenários planejados.

Foram incorporados: distinção entre histórico, resultado e receita; revalidação por novidades além das revisões das fontes antigas; descoberta de notas ainda sem ligações; persistência operacional pelo executor sob garantias aplicáveis de P07; proteção do histórico conforme acesso e exclusão; atraso de índices; custo líquido; prevenção de repetição como evidência ou autorreativação.

Capítulos 01 a 04 e proposta de busca foram alinhados ao novo capítulo 05. A avaliação documental das integrações passou a distinguir confiabilidade por operação, modo e versão. A preferência atual é avaliar primeiro o MCP Connector como ponte mais completa, mantendo MCPVault como candidata de acesso direto. Não houve seleção final, instalação ou teste no ambiente do usuário.

### Resultado da revisão final desta versão

Foram conferidos: entrega e roteamento do registro operacional; distinção entre contrato estável e resultado que precisa de revalidação; atualização incremental com ampliação conservadora; fontes novas sem arestas; confirmação, repetição e recuperação; acesso ao histórico; promoção de melhorias; e diferença entre documentação examinada e teste real. O parecer não apontou correção bloqueante nesse alcance. As referências dos capítulos de fundamentos, processos e interações foram atualizadas para incluir o capítulo 05 e distinguir a revisão antiga interrompida da rodada concluída.

A versão inicial dos processos pode orientar a modelagem de entidades e campos. Mecanismos físicos de consistência, invalidação, acesso e retenção, escolha de versões, parâmetros, instrumento inicial e testes executados continuam nas etapas correspondentes. Concluir esta versão não congela o sistema; mudanças seguem P12/P13 e mantêm documentação e funcionamento coerentes.

## Próximo ponto de retomada

Os processos têm uma base lógica escrita e conferida manualmente. O usuário poderá revisar os capítulos completos e os ajustes acima antes da modelagem final dos dados. O cofre escolhido será novo, mas ainda não foi criado. Não iniciar a entrevista como se a estrutura ou a integração já estivessem prontas.
