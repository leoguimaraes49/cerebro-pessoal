# Integrações entre Codex e Obsidian

Data da pesquisa: 28 de outubro de 2026. Situação: análise de documentação e repositórios; nenhuma instalação, alteração de configuração ou conexão com cofre foi realizada.

## Resultado

Há opções comunitárias documentadas para conectar Codex a um cofre. A busca de Obsidian no catálogo de plugins disponibilizado nesta sessão não retornou resultados; esse catálogo não é uma lista exaustiva de todos os projetos existentes.

A [documentação oficial de MCP no Codex](https://learn.chatgpt.com/docs/extend/mcp) descreve suporte a servidores locais e HTTP. Isso fundamenta o caminho de integração, mas não comprova o funcionamento de um plugin comunitário específico, de suas configurações ou da combinação com voz na conta do usuário.

## Candidatas

### MCP Connector for Obsidian

[Repositório e documentação do mantenedor](https://github.com/istefox/obsidian-mcp-connector).

O projeto documenta operações de notas, propriedades e ligações, pesquisa textual e semântica local e configuração para Codex, inclusive considerações de Windows. Possui modo de plugin dentro do Obsidian e um modo headless separado. O README registra uma correção de travamento em determinadas versões do Obsidian e recomenda versão corrigida do plugin. A compatibilidade precisa ser testada nas versões que forem usadas.

**Uso candidato:** avaliar uma ponte com mais recursos prontos, inclusive recuperação semântica e relações entre notas. O modelo de busca deve ser avaliado com relatos em português. Não assumir que toda operação de grafo ou de perfil planejada já está implementada por essa ferramenta.

### MCPVault

[Repositório e documentação do mantenedor](https://github.com/bitbonsai/mcpvault).

Servidor MCP local com exemplos para Codex, leitura, escrita e pesquisa textual com BM25. Trabalha diretamente nos arquivos, sem exigir plugin nem Obsidian aberto; usa runtime Node.js. A documentação diferencia exclusões de pesquisa de permissões: esconder uma pasta dos resultados não impede necessariamente sua leitura direta pelas ferramentas.

**Uso candidato:** acesso aos arquivos desacoplado da interface do Obsidian, útil para avaliar o trabalho de fundo. Isso não equivale a um agendador, não fornece por si só perfil comportamental ou busca vetorial e não substitui nossa política de acesso. Instruções do repositório sobre planos do ChatGPT precisam ser conferidas na documentação oficial atual, sem presumir que estejam atualizadas.

### Cortex MCP

[Repositório e documentação do mantenedor](https://github.com/DoktorDaveJoos/cortex-mcp).

Plugin que serve MCP HTTP dentro do Obsidian, com exemplo para Codex e operações de leitura, criação, edição, pesquisa textual, organização e metadados. O uso documentado depende de o Obsidian estar aberto com o servidor ativo.

**Uso candidato:** ponte de operações básicas de notas. Busca semântica, tratamento de versões temporais e os contratos completos do cérebro não ficam comprovados por esse conjunto de ferramentas. Configuração e autenticação devem ser verificadas antes de escolher a solução.

## O que muda e o que permanece no projeto

Uma integração existente pode reduzir o trabalho para acessar o cofre. Ainda precisamos mapear cada ferramenta disponível aos contratos de escrita, busca, correção e revisão. Não confundir uma API de notas com toda a arquitetura do assistente.

As seguintes propriedades não foram comprovadas por esta pesquisa: atualização consistente de vários registros, preservação de correções concorrentes, invalidação completa do cache, bloqueio de todos os caminhos de acesso, validade de hipóteses pessoais e execução autônoma sem recurso de modelo ou serviço disponível.

Servidor e embeddings locais não significam que todo o processamento permaneça no computador: conteúdo devolvido a uma IA remota pode entrar no contexto enviado ao fornecedor. O fluxo real de dados precisa ser identificado na configuração escolhida.

## Recomendação de avaliação

A avaliação aprofundada de confiabilidade por operação e de cobertura dos processos está em [Avaliação das integrações por contrato](avaliacao-integracoes-por-contrato.md). Ela complementa esta lista de candidatas com leitura dirigida de código e documentação, sem instalação ou testes de execução.

Manter MCP Connector e MCPVault como as candidatas principais, por abordagens complementares: integração com recursos do Obsidian e acesso aos arquivos sem dependência da interface. Cortex permanece uma alternativa mais básica a comparar. Essa é uma recomendação de avaliação, não seleção de produto nem aprovação de instalação.

Quando chegarmos à implementação, usar um cofre de teste separado para verificar leitura de notas completas, criação, alteração, links, nomes e acentos em português, duplicação, conflito de revisão, exclusões e retomada após falha. Conferir quais contratos podem usar a ponte diretamente e quais precisam de um serviço adicional. Escolher a alternativa pela adequação, manutenção, custo e resultados reais dos testes, e não pela quantidade de ferramentas anunciadas.

O cofre do usuário continua planejado como novo. A pesquisa não altera a ordem de concluir a lógica dos processos antes de definir entidades e campos e preparar o cofre.
