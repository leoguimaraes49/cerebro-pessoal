# Busca do cérebro pessoal — proposta técnica

Situação: arquitetura híbrida aceita pelo usuário em 28 de outubro de 2026. Nenhum mecanismo foi instalado, indexado ou testado no cofre. Os algoritmos, armazenamento e ferramentas abaixo são candidatos técnicos. A modelagem final de entidades e campos continua para depois da lógica dos processos.

Revisão com artigos e relatos: ver pesquisa-busca-e-comunicacao.md nesta pasta. A busca vetorial deve participar da avaliação desde o desenho; não foi estabelecida uma regra de adiar vetores até o surgimento de falhas. A contribuição da fusão e da expansão por grafo será comparada separadamente. A proposta permanece substituível e não representa escolha implementada de ferramenta.

## Recomendação

Combinar recuperação lexical, vetorial e expansão por relações. A busca vetorial é apropriada para comparar significado, mas não substitui a busca de nomes e termos precisos nem a verificação das fontes. O índice organiza candidatos; os registros autorizados do cofre continuam sendo a referência.

| Componente proposto | Função | Custo e cuidado |
|---|---|---|
| Busca lexical com índice invertido e BM25 | Encontrar palavras, nomes, expressões e termos do manual. | Pode operar localmente sem uma chamada a um modelo de linguagem para cada consulta; precisa de indexação e atualização. |
| Vetores e similaridade de cosseno | Encontrar relatos próximos em significado mesmo com vocabulário diferente. | Precisa gerar representações das fontes e da consulta; custo depende do modelo e de onde ele roda. Semelhança não comprova verdade ou causalidade. |
| Expansão do grafo por relações pertinentes | Encontrar experiências, fontes, exceções, correções e contextos ligados aos candidatos. | Usar relações tipadas e limites de expansão; não explorar todo o grafo indiscriminadamente. |
| Fusão dos resultados por RRF | Combinar listas de candidatos sem somar escores de escalas incompatíveis. | É uma opção inicial a avaliar; não transforma posição no ranking em probabilidade de verdade. |

## Algoritmos e mecanismos candidatos

- **BM25:** ranking lexical. SQLite FTS5 é um candidato local para essa capacidade; isso não obriga guardar a base canônica em SQLite.
- **Similaridade de cosseno com busca exata sobre os vetores:** referência para avaliar qualidade e custo com o volume real.
- **HNSW:** alternativa aproximada a comparar se volume e frequência de consulta justificarem o índice e a memória. Não é necessário escolhê-la sem medir. Exatidão da busca de vizinhos não equivale a correção semântica da resposta.
- **Expansão por vizinhança no grafo:** percorrer relações escolhidas em camadas, com controle de nós visitados, relevância, profundidade e orçamento. Trata-se do grafo de conhecimento; um eventual grafo interno de HNSW é um índice matemático diferente.
- **RRF:** combinar os rankings lexical e semântico. Após a fusão, recuperar as fontes e dependências pertinentes, incluindo as que contradigam uma hipótese inicial.

Não é uma escolha entre todos esses métodos como concorrentes equivalentes: eles resolvem partes diferentes do problema. A seleção do armazenamento, da biblioteca e do modelo de embeddings ficará para a validação técnica.

## Caminho de uma consulta

1. Entender o pedido e o contexto, aplicar o escopo de acesso e definir a cobertura necessária.
2. Recuperar correspondências diretas e semânticas de acordo com a pergunta, sem chamar um modelo grande para cada operação determinística.
3. Combinar candidatos e remover duplicações de origem.
4. Explorar relações relevantes para obter fontes, períodos, correções, dependências e exceções.
5. Ler os contratos e evidências completos necessários para a resposta. Trechos usados para localizar documentos não são a única base para a conclusão.
6. Verificar se o contexto cobre o pedido e se há divergências. Se faltar base, usar a busca adaptativa já planejada ou perguntar.
7. Responder distinguindo o que foi encontrado, o que foi inferido e o que segue desconhecido.

Uma pergunta específica pode ser atendida sem todas as etapas de recuperação. Uma investigação ampla pode exigir várias rodadas. A parada depende de suficiência e limites declarados, e não de simplesmente preencher uma lista de resultados. Nenhum ranking garante encontrar todos os fatos relevantes.

## Exemplo

Pergunta: como estudar programação de uma forma compatível com o usuário?

A busca lexical pode encontrar programação e métodos registrados. A vetorial pode encontrar um relato de aprender por tentativa e construção mesmo sem mencionar estudo. A expansão do grafo pode recuperar um projeto, o resultado observado, a disponibilidade atual e uma correção que limite aquela preferência ao início de um conteúdo. A resposta considera esse conjunto, sem converter uma experiência em regra universal.

## Atualização e evolução

Quando o conteúdo autorizado muda, atualizar o que foi afetado: índice lexical, vetores cujo conteúdo semântico mudou, relações e resultados dependentes. Não recalcular o cérebro inteiro por padrão. Mudança no modelo de embeddings exige migração ou reindexação coerente; não comparar vetores incompatíveis como se pertencessem ao mesmo espaço.

O cache de resultados depende das revisões das fontes. Correção ou exclusão invalida o que for pertinente. Dados apagados não podem continuar acessíveis por índice antigo.

Novas notas e relações podem mudar resultados sem editar as fontes antigas. Identificar impacto por dependências, escopo pesquisável e recuperação lexical/semântica; uma nota sem arestas também pode importar. Atualizar o trecho afetado quando seu alcance for delimitável; ampliar a recuperação quando não for. Atraso de índices não libera uso de cache conhecido como superado.

A memória de buscas integra esta arquitetura: histórico operacional de consultas/fontes, resultados condicionados à validade atual e receitas reutilizáveis de investigação. Vetores podem ajudar a localizar receitas por significado, sem transformar similaridade em equivalência de pergunta ou conclusão. O manual-cerebro-05-memoria-de-busca.md detalha o contrato e os testes futuros.

Essa manutenção não cria automaticamente subfluxos novos: a busca e a escrita existentes acionam os mecanismos necessários. Se surgir uma estratégia de pesquisa realmente nova, ela segue o ciclo de composição temporária, candidata, testes e eventual adoção já planejado.

## Custo-benefício e teste

Comparar lexical isolada, vetorial isolada e combinação com grafo usando as mesmas perguntas e fontes. Avaliar recuperação de evidências importantes, contradições e correções, além da qualidade final, duração, memória, custo de geração dos vetores, reindexação e chamadas de IA.

Um modelo local de embeddings pode evitar cobrança por chamada a um provedor, mas consome recursos do computador. Modelo remoto possui suas próprias condições de cobrança e acesso. A ponte MCP não fornece gratuitamente um modelo de embeddings por existir.

A preferência por conteúdo completo não significa enviar todo o cofre a cada consulta. Significa preservar a profundidade das evidências pertinentes, não decidir só por resumo rápido e não ocultar limitações de cobertura. Completude absoluta não é garantida por ler mais texto.

## Fontes primárias consultadas

- [SQLite FTS5](https://www.sqlite.org/fts5.html): indexação textual, atualizações e ranking BM25.
- [Faiss: escolha de índice](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index): diferenças entre busca exata, índices aproximados, memória e custo de construção.
- [Qdrant: busca híbrida e fusão de rankings](https://qdrant.tech/documentation/hybrid-queries/): recuperação lexical e semântica combinadas e RRF.
- [SQLite: consultas recursivas em grafos](https://www.sqlite.org/lang_with.html): exemplo de expansão em grafo sem impor um banco dedicado de grafos.
