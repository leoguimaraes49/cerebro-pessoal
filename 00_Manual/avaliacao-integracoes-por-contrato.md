# Integrações Obsidian — confiabilidade por contrato

Data: 28 de outubro de 2026. Escopo: MCP Connector for Obsidian e MCPVault. Método: documentação dos mantenedores e leitura dirigida de interfaces e código; nenhuma instalação, conexão com cofre, medição ou teste de execução foi realizada. As fontes em branches móveis precisam ser fixadas em uma versão antes da implementação.

## 1. O que significa confiabilidade neste projeto

Confiabilidade é a capacidade demonstrada de cumprir um contrato nas condições de operação previstas, reconhecer limites e recuperar falhas sem esconder perda ou duplicação. Deve ser avaliada por operação, versão e modo de execução. A confiança declarada pela IA não substitui essa avaliação.

Separar três níveis: comportamento descrito pelo mantenedor, comportamento encontrado no código examinado e comportamento confirmado em teste no ambiente real. Esta avaliação alcança os dois primeiros, em trechos específicos. Não atribui uma nota global arbitrária nem comprova a aplicação inteira.

| Área | Exigência verificável |
|---|---|
| Leitura | Recuperar o material necessário e reconhecer truncamento, ausência e revisão consultada. |
| Busca | Recuperar fontes relevantes, correções e contexto; distinguir resultado vazio de informação inexistente. |
| Escrita | Detectar proposta obsoleta, preservar correção concorrente e confirmar o que ocorreu. |
| Repetição | Reconciliar efeito após perda de resposta, sem duplicar o que já foi aplicado. |
| Mudança em várias notas | Reconhecer partes confirmadas e pendentes; recuperar sem alegar sucesso total inexistente. |
| Acesso | Aplicar a política também em leituras diretas, links, índices e histórico de buscas. |
| Continuidade | Retomar dados confirmados e contratos compatíveis, reconhecendo indisponibilidade. |
| Atualização | Impedir uso atual de derivado conhecido como inválido enquanto índice/cache é atualizado. |

Ausência de uma garantia não é compensada por uma resposta convincente do modelo. A operação pode ficar restrita a leitura, proposta ou revisão até existir uma implementação que cumpra o contrato. Dúvida sobre significado pessoal é tratada pela pergunta pertinente; defeito de consistência da ferramenta precisa de correção técnica.

## 2. Comparação das capacidades observadas

| Critério | MCP Connector for Obsidian | MCPVault | Implicação |
|---|---|---|---|
| Modo de acesso | Plugin no Obsidian; também oferece modo headless com capacidades próprias. | Acesso direto à pasta, sem plugin nem Obsidian aberto. | Avaliar cada modo separadamente. |
| Recuperação | Documenta texto, semântica local e navegação por relações. | Documenta busca textual com BM25 e resolução de links. | Connector oferece mais componentes prontos para o desenho híbrido; isso não comprova qualidade em português. |
| Leitura extensa | Documenta limites e continuação de conteúdo truncado. | Oferece leitura integral, em lote e por linhas. | Verificar completude de ambos, sem confundir trecho com nota inteira. |
| Alteração de notas | Proteção declarada entre escritas MCP no mesmo arquivo; precondição de conteúdo opcional em determinadas operações. | Interface examinada de escrita não recebe revisão esperada nem identificador de repetição. | Nenhuma das evidências comprova todo P07. |
| Autorização | Plugin documenta teto de ferramentas por token e exclusões globais de pastas. | Modo somente leitura; exclusões de busca/listagem permitem acesso direto aos caminhos excluídos. | Escopo visível e autorização efetiva precisam ser distinguidos. |
| Falhas e retomada | Contrato documentado de erros. | Operações de arquivo e resultados próprios. | Erro identificado não equivale a idempotência durável ou recuperação de várias notas. |
| Trabalho de fundo | Headless pode operar sem a interface. | Pode operar sem a interface. | Nenhum desses modos constitui, por si só, agendador e recurso autônomo de modelo. |

As descrições de recuperação e leitura vêm dos catálogos dos mantenedores: [MCP Connector](https://github.com/istefox/obsidian-mcp-connector#what-it-can-do) e [MCPVault](https://github.com/bitbonsai/mcpvault). São capacidades candidatas; não resultados de comparação experimental.

## 3. Pontos decisivos encontrados

### 3.1 Concorrência precisa de uma garantia concreta

O Connector declara o uso de `Vault.process()` e mutex para impedir perda entre duas escritas MCP no mesmo arquivo. Isso não comprova precondição obrigatória em toda mutação, coordenação entre todos os modos e editores ou consistência de várias notas. Determinadas operações aceitam `expectedContent` opcional. [Declaração do mantenedor](https://github.com/istefox/obsidian-mcp-connector#security).

Na interface `NoteWriteParams` examinada do MCPVault existem caminho, conteúdo, frontmatter e modo de escrita. Não há revisão esperada nem identidade durável de operação; o caminho de `writeNote` examinado monta o conteúdo e usa escrita de arquivo. Isso deixa em aberto a preservação de uma edição posterior à leitura e a repetição de append após resposta perdida. [Interface](https://github.com/bitbonsai/mcpvault/blob/main/src/types.ts), [implementação examinada](https://github.com/bitbonsai/mcpvault/blob/main/src/filesystem.ts).

Uma camada nossa pode organizar validações, mas comparar uma revisão e depois chamar uma escrita comum não torna as duas etapas atômicas. A autoridade que efetiva a escrita deve garantir a precondição ou a coordenação apropriada. Edições manuais e outros escritores que contornem esse caminho precisam entrar no modelo de conflito.

### 3.2 Um filtro de descoberta não é uma regra de acesso

No Connector, a lista permitida de ferramentas por token é diferente do perfil inicial de descoberta; exclusões de pastas são globais ao cofre. Isso não oferece automaticamente uma política de pastas diferente para cada IA. As garantias do plugin não devem ser transferidas ao headless sem conferência. [Decisão de perfis por cliente](https://github.com/istefox/obsidian-mcp-connector/blob/main/docs/architecture/ADR-0014-per-client-tool-profiles.md), [política de conteúdo](https://github.com/istefox/obsidian-mcp-connector/blob/main/SECURITY.md#content-folder-exclusion-omc-040).

O MCPVault documenta que o modo somente leitura rejeita mutações também quando chamadas diretamente. Em contrapartida, suas exclusões de busca/listagem mantêm leitura e escrita direta disponíveis. Logo, esses filtros não atendem sozinhos a uma política de conteúdo privado por IA. [Opções documentadas](https://github.com/bitbonsai/mcpvault#readme).

### 3.3 Identificar uma falha não resolve todos os seus efeitos

O Connector documenta códigos estáveis e indicação de erro; não foi comprovado um contrato completo de deduplicação durável de chamadas ou atualização conjunta de notas. Um bloqueio de arquivo não é uma transação do grafo. [Contrato de erros](https://github.com/istefox/obsidian-mcp-connector/blob/main/docs/error-codes.md).

Nos dois casos, exigir recuperação verificável de efeitos parciais. Se houver troca de ponte após uma falha, reconciliar primeiro a operação anterior; mudar de ferramenta e repetir a escrita pode duplicar o efeito. A escolha de duas candidatas para avaliação não autoriza dois caminhos de escrita concorrentes sem coordenação.

### 3.4 Memória de buscas é responsabilidade adicional

Índices, observação de arquivos e notificações disponíveis não comprovam o histórico de percursos, a validade semântica de caches ou a propagação de correções de que precisamos. O capítulo 05 especifica o comportamento a construir sobre as primitivas escolhidas. Manter sua aplicação independente do fornecedor evita perder o repertório operacional ao trocar de IA ou de ponte.

## 4. Cobertura dos processos do cérebro

| Processo | O que as pontes podem fornecer | O que continua sendo responsabilidade do nosso sistema |
|---|---|---|
| P01 — Sessão | Leitura de manual, notas e estado persistido. | Contexto autorizado, versões e continuidade, inclusive perfil inicialmente ausente. |
| P02 — Contribuição | Persistência e consulta como ferramentas. | Interpretar voz/texto, aproveitar várias áreas e distinguir relato de inferência. |
| P03 — Coordenação | Operações disponíveis para o plano. | Dependências, autoridade, limites e decisão do que executar. |
| P04 — Busca | Recuperação e leitura, com diferenças entre candidatas. | Suficiência, contradições, contexto, memória de caminhos e validade atual. |
| P05 — Adaptação | Consultas que podem ser recombinadas. | Reformulação, receita temporária, pergunta e condição de parada. |
| P06 — Proposta | Notas e metadados consultáveis. | Identidade, deduplicação semântica, alcance e impacto. |
| P07 — Aplicação | Primitivas de mutação; proteção parcial conforme operação. | Garantias adicionais de revisão, repetição, efeitos parciais e eventos de derivados. |
| P08 — Perfil e correções | Acesso às fontes e alterações permitidas. | Tempo, linhagem, interpretação revisável e correção em cadeia. |
| P09 — Resposta | Fontes e confirmações de ferramentas. | Personalização fundamentada e comunicação do que foi confirmado. |
| P10 — Resultados | Armazenar relatos e observações. | Comparar resultado e expectativa sem inferir sucesso pelo silêncio. |
| P11 — Pesquisa | Guardar referências e materiais autorizados. | Pesquisa externa, avaliação de fontes e aplicabilidade individual. |
| P12 — Evolução | Publicar descrições quando a operação permitir. | Proposta, promoção, compatibilidade e coerência entre execução e manual. |
| P13 — Verificação | Ambiente e chamadas sob teste. | Cenários independentes, comparação e decisão por critérios prévios. |
| P14 — Manutenção | Acesso local quando o servidor estiver disponível. | Fila, agendamento autorizado, recursos de modelo e recuperação. |

## 5. Avaliação proposta antes de escolher

Preparar casos artificiais ou autorizados num cofre de teste; fixar versão do cliente, servidor, modo e ferramentas. As mesmas exigências centrais valem para todas as candidatas.

1. Ler manual e fontes extensas, conferir continuação, nomes e acentos em português.
2. Recuperar nome exato, paráfrase, relação indireta, correção e experiência contraditória nova.
3. Alterar a mesma nota por dois clientes e pelo editor; exigir detecção de proposta obsoleta.
4. Perder a resposta de uma escrita e repetir após reinício; confirmar ausência de duplicação ou recuperação explícita.
5. Interromper uma alteração de três notas; identificar exatamente o que ocorreu e restaurar consistência conforme o contrato.
6. Testar o escopo permitido por acesso direto, busca, links e histórico, inclusive após revogação.
7. Corrigir, excluir ou acrescentar uma nota durante atraso de índice; impedir resposta baseada em cache conhecido como antigo.
8. Retomar sessão noutra IA com acesso diferente, sem depender de memória interna ou de funcionalidades não comprovadas do cliente.
9. Comparar latência, manutenção, recursos locais e chamadas ao modelo preservando a qualidade exigida.

Falhar numa garantia central restringe a operação afetada; não é compensado pela média de desempenho. Resultados ficam registrados por cenário e configuração. As adaptações necessárias devem passar pelos mesmos testes.

## 6. Recomendação atual

Priorizar o MCP Connector para avaliação da ponte híbrida mais completa; manter MCPVault como candidata de acesso direto mais simples, especialmente para avaliar operação sem interface. A preferência é de avaliação, não aprovação de instalação ou garantia de confiabilidade final.

As duas opções são avaliáveis. A escolha definitiva depende da capacidade de cumprir os contratos com adaptação e manutenção razoáveis. Um servidor de acesso às notas não substitui a arquitetura de memória, o executor ou a avaliação do perfil.

O trabalho atual continua sendo especificação e revisão. Depois vêm entidades e campos, preparação do cofre novo, integração e testes, avaliação inicial e entrevista. Nada foi instalado por esta análise.
