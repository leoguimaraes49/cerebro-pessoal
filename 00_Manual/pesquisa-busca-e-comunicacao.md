# Pesquisa: busca de memória e comunicação entre IAs

Data da consulta: 28 de outubro de 2026. Escopo: artigos primários, documentação técnica e relatos de primeira mão, para orientar o desenho do cérebro pessoal. Não houve execução de benchmarks, instalação de motores ou acesso a um cofre do usuário.

## Conclusão para este projeto

Uma arquitetura que permita busca lexical, semântica e expansão por relações é uma candidata bem fundamentada. A pesquisa não estabelece uma combinação universalmente mais barata ou mais precisa para este cofre ainda inexistente. Vetores devem participar da comparação desde o início; não é justificável adiá-los apenas por intuição de custo. Também não há razão para executar todas as técnicas em toda pergunta sem medir sua contribuição.

O tratamento de tempo, correções, origem e leitura da evidência importa tanto quanto o algoritmo que encontra candidatos. O objetivo não é só achar uma nota parecida: é recuperar e utilizar os registros corretos para a situação.

## Artigos e suas implicações

### LongMemEval — ICLR 2025

O [artigo e seus resultados](https://arxiv.org/html/2410.10813v2) avaliam memória entre sessões, atualização, tempo e ausência de informação. No apêndice E.2, tabela 9, os recuperadores densos testados superam BM25 na maioria das configurações. A seção 5.2 encontra perdas ao substituir fontes por fatos ou resumos isolados, com diferenças por tarefa; a seção 5.3 melhora a recuperação expandindo as chaves sem abandonar a fonte original.

**Aplicação:** comparar vetores seriamente, preservar fontes e testar mudanças temporais. **Limite:** perguntas e históricos construídos e revisados para avaliação; não prova identificação fiel da personalidade nem eficácia de conselhos de vida.

### Zep/Graphiti — artigo dos próprios desenvolvedores, 2025

A [seção 3.1 do artigo](https://arxiv.org/html/2501.13956v1) descreve combinação de cosseno semântico, BM25 e busca em largura no grafo; a arquitetura também trata validade temporal. **Aplicação:** existe precedente técnico próximo do desenho proposto. **Limite:** avaliação dos autores do sistema; não isola o ganho de cada componente nem demonstra que o mesmo custo se aplicará ao nosso projeto. Não é decisão de contratar ou adotar esse produto.

### BEIR — NeurIPS 2021

O [benchmark BEIR](https://arxiv.org/abs/2104.08663) comparou recuperação em diferentes domínios e encontrou BM25 como referência robusta, com custos maiores em algumas alternativas sofisticadas. **Aplicação:** manter uma base lexical como comparador. **Limite:** recuperação geral com modelos de outra geração, não avaliação de memória pessoal contemporânea.

### Conversa contextual — pesquisa de 2026

[When Users Don't Ask](https://arxiv.org/abs/2609.03467) examina perguntas em contexto conversacional, incluindo pedidos implícitos e compostos. Os resultados mostram lacunas que perguntas factuais explícitas não capturam, e recuperar melhor não se traduz automaticamente em responder melhor. **Aplicação:** testar perguntas naturais e a utilidade final da resposta, além da localização da evidência. **Limite:** estudo de benchmark, não validação deste sistema ou da interpretação comportamental do usuário.

## Relatos de uso: evidência informal

Um [experimento publicado pelo autor no Reddit sobre LoCoMo](https://www.reddit.com/r/Rag/comments/1ujwwu6/for_multisession_agent_memory_a_single_vector/) relata vantagem da combinação lexical-vetorial sobre os componentes isolados no conjunto avaliado. O texto discute limitações por tipo de pergunta e mede recuperação, não qualidade final. O endereço do script anunciado não pôde ser confirmado como disponível pela análise delegada; o teste não foi reproduzido nesta revisão. Serve como hipótese prática, não como resultado verificado por nós ou garantia de custo.

Outro [relato sobre busca híbrida](https://www.reddit.com/r/AI_Agents/comments/1tvrkg3/is_bm25_vector_rrf_really_worth_it/) descreve maior contribuição lexical no caso do autor, sem conjunto e medidas suficientes para comparação. É um contraponto útil à ideia de que acrescentar vetores sempre compensa.

Um [relato sobre informações que mudam no tempo](https://www.reddit.com/r/LangChain/comments/1sdhmd8/anyone_seeing_rag_break_on_temporally_evolving/) aponta recuperação de versões antigas como atuais, mas os números apresentados não têm material suficiente para reprodução. Reforça uma preocupação a testar, sem comprovar uma solução universal.

Os relatos têm contextos e possíveis interesses próprios. Popularidade, concordância em comentários e números sem método não equivalem a confirmação independente. Nenhuma comparação de custo do nosso cérebro pode ser calculada a partir desses posts isoladamente.

## A ideia de uma comunicação interna melhor

Essa capacidade já faz parte do planejamento: P12 propõe melhorias, P13 as verifica, P04 recupera contexto e P05 adapta a investigação. Não é necessário acrescentar outro subfluxo com a mesma finalidade.

Existem três linhas distintas a considerar:

1. **Reduzir coordenação desnecessária.** O [AgentPrune](https://arxiv.org/abs/2410.02506) reduz mensagens e conexões redundantes entre agentes nos cenários estudados. Isso apoia testar quais interações realmente ajudam. Não demonstra uma linguagem universal nem garante ganhos iguais em memória pessoal.
2. **Comprimir prompts.** O [LLMLingua-2](https://aclanthology.org/2024.findings-acl.57/) aprende a selecionar conteúdo para reduzir o texto de entrada, com avaliação em tarefas específicas. Não é o mesmo que uma notação arbitrária inventada durante conversas. Como o usuário prioriza acesso às evidências completas, compressão com possível perda não é adotada automaticamente.
3. **Comunicar representações internas.** O [Interlat, ACL 2026](https://aclanthology.org/2026.acl-long.1248/), estuda comunicação por estados internos dos modelos e usa mecanismos aprendidos. Os próprios autores o apresentam como estudo de viabilidade. Isso exige recursos específicos; não demonstra que ler um manual por MCP faça diferentes IAs fechadas compartilhar uma linguagem interna universal.

Formato compacto, cache, algoritmo de recuperação e canal latente são intervenções diferentes. Melhorar uma não garante melhorar as demais.

## Recomendação revisada de desenho

- Prever índice lexical, canal semântico e navegação por relações, com estratégias substituíveis e contratos comuns.
- Comparar lexical, vetorial, combinação e combinação com grafo em condições equivalentes. A extensão por grafo precisa demonstrar benefício, não apenas existir.
- Avaliar ranking e também leitura das fontes, atualidade e utilidade da resposta final.
- Manter os registros originais e contratos completos acessíveis; um índice, vetor ou fato extraído ajuda a localizar, mas não substitui a evidência.
- Permitir que os processos existentes proponham consultas alternativas, melhor fusão de resultados, índices incrementais e comunicação mais eficiente.
- Promover cada mudança segundo testes e critérios prévios, mantendo compatibilidade entre versões e alternativas de recuperação.
- Otimizar primeiro o desperdício: retentativas inúteis, coordenação sem benefício, reindexação completa desnecessária e repetição de dados. Não eliminar exceções ou correções pessoais só para reduzir tokens.

## Como testar sem pressupor o vencedor

Preparar casos próprios com fontes autorizadas ou exemplos sintéticos: nomes exatos, paráfrases em português, transcrição de voz imperfeita, informação distribuída entre conversas, correção recente, preferência dependente do contexto, fonte excluída, hipótese contradita e pergunta sem resposta na base.

Para cada alternativa, conferir fontes recuperadas, lacunas, uso de correções, resposta final, tempo, memória, custo de indexação e atualização e quantidade de chamadas aos modelos. Usar condições equivalentes e separar dados de ajuste dos de avaliação.

Uma proposta de protocolo deve ser testada também na troca de IA: os componentes precisam interpretar corretamente o significado, as referências, as versões e a incerteza. Mensagem menor com perda de contexto não é melhoria aprovada. Não prometer custo mínimo nem entendimento completo da pessoa com base somente no tamanho do prompt ou em um placar público.

## Pendências preservadas

A pesquisa orienta a lógica, mas não fecha biblioteca, banco, modelo de embeddings, algoritmo aproximado ou número de vizinhos. Ainda faltam os contratos completos de interação entre processos e os valores das políticas operacionais. Entidades e campos continuam para depois desse trabalho, conforme a ordem pedida pelo usuário.
