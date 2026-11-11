# Garantias de execução — versão 0.5

> Complemento de retomada após interrupção: [16 — Retomada e supervisão](manual-cerebro-16-retomada-e-supervisao.md).

Este capítulo descreve a integração das candidatas de confiabilidade ao serviço local. Os contratos dos capítulos 01–11 orientam a execução. O capítulo 14 documenta a base 0.4, e este capítulo acrescenta as rotinas de confirmação e verificação da versão 0.5. O relatório da implantação registra os testes e a ativação efetivamente realizados.

## Gravação e confirmação

As rotinas de fontes e conhecimento reservam o nome do arquivo enquanto registram a operação proposta na transação do respectivo banco. Pedidos simultâneos com títulos iguais recebem nomes disponíveis e identidades próprias. Uma chave repetida continua identificando o mesmo pedido, e sua reutilização com outro conteúdo é conflito.

Uma nova nota de conhecimento cujo arquivo existe, mas cuja operação segue proposta, bloqueia o consumo do catálogo até a reconciliação. A repetição do mesmo pedido permite conferir e confirmar o efeito já aplicado. Esse bloqueio conserva a distinção entre proposta e efeito confirmado. Operações antigas em conflito ou escritas parciais podem exigir recuperação específica. Os testes que conservaram material recuperável não representam recuperação automática de toda falha de disco ou energia.

## Verificador local

O módulo `verificador_evidencias.py` usa somente a biblioteca padrão e pode executar em processo separado. O adaptador `evidencias.py` fornece registros canônicos, escopo, revisões e um manifesto produzido pelo serviço a partir da base atual. A âncora confiável vem do serviço, e o manifesto compartilhado vale para aquela geração.

Os três tipos de alegação verificáveis são `field`, `sum` e `chain`. O primeiro confere um campo explícito de uma fonte cujo `payload.content` contém JSON. O segundo soma operandos inteiros. O terceiro confere uma cadeia de arestas explicitamente registradas com `requires` ou `precedes`, os predicados transitivos desta política. As referências apontam para fontes primárias atuais e caminhos no JSON dessas fontes.

Booleanos, inteiros e decimais conservam seus tipos durante a comparação, inclusive em estruturas aninhadas. Revisões exigem inteiros positivos. O checker confere integridade, identidade, escopo, revisões, citações e o vínculo da representação controlada com suas alegações. Texto livre, causalidade, identidade ambígua, diagnósticos e hipóteses exigem interpretação revisável. Uma cópia literal ou soma conferida prova somente a relação registrada nos dados disponíveis.

## Contrato opcional de resposta

O coordenador continua aceitando as respostas existentes com `answer` e `citations`. Uma resposta pode acrescentar `claims` e `answer_format`. A modalidade padrão é `free_text`. Nesta modalidade, o resultado `claims_verified` informa que as alegações declaradas passaram na checagem, com `answer_verified: false`. O texto natural permanece provisório.

Uma modalidade `controlled` exige que `answer` corresponda exatamente às linhas `id = valor JSON` das alegações. Quando todos os controles passam, o resultado é `verified`, e a qualidade do coordenador é `verified_as_recorded`. O sistema só usa essa qualidade para a representação controlada aceita. `limited` mantém os limites de regra ou interpretação, `rejected` recusa a comprovação, e `stale` exige revalidação em contexto atual.

Exemplo técnico com uma fonte fictícia cujo conteúdo é `{"values":[1,2]}`.

```json
{
  "answer": "c1 = 3",
  "answer_format": "controlled",
  "claims": [
    {
      "id": "c1",
      "kind": "sum",
      "refs": [
        {"record_id": "ID_DA_FONTE", "revision": 1, "path": "/values/0"},
        {"record_id": "ID_DA_FONTE", "revision": 1, "path": "/values/1"}
      ],
      "value": 3
    }
  ],
  "citations": []
}
```

Relatos em linguagem natural permanecem armazenados no formato original recebido. O adaptador carrega os registros existentes para conferir alegações compatíveis. Uma interpretação da IA não pode inventar um campo estruturado para obter um parecer favorável.

## Complementação seletiva

A primeira checagem usa as evidências do contexto recuperado. Quando uma alegação objetiva fica sem uma fonte necessária, o adaptador consulta as referências declaradas na base atual. Se todas as evidências couberem no limite e a alegação for sustentada, o resultado recebe `route: supplemented`. A resposta e a alegação são conservadas durante essa complementação.

`direct` identifica a checagem suficiente no contexto inicial. `context_budget_exceeded` conserva a limitação de tamanho. `unsupported_or_invalid` identifica a ausência de comprovação pelas referências fornecidas. Regras desconhecidas e hipóteses permanecem limitadas. Se uma alegação for recusada, o coordenador entrega uma limitação em vez do texto que continha a conclusão rejeitada.

A pergunta ao usuário e a pesquisa externa continuam sendo encaminhamentos do coordenador. Uma informação pessoal essencial ausente exige pergunta e espera. Uma lacuna de evidência externa pode acionar a pesquisa de temas permitidos. A checagem determinística não cria automaticamente uma pergunta pessoal por qualquer erro de formato ou retorno vazio.

## Ferramentas e continuidade

`avaliar_resposta` recebe `operation_key`, `resposta`, `contexto_ids` opcional e `limite_contexto`, com padrão 8. O limite aceita de 1 a 50 registros. A resposta estruturada admite até 64 alegações e 40.000 bytes. Comprovantes persistidos têm teto de 4 MB. A CLI oferece `avaliar-resposta --pedido ARQUIVO.json` com os mesmos campos.

`consultar_comprovante` recebe `receipt_id`. O serviço refaz a verificação contra a base atual e informa `stale` se a geração mudar, inclusive por uma nota nova sem ligação anterior. A CLI oferece `consultar-comprovante --pedido ARQUIVO.json`. Outra IA precisa acessar o serviço com autorização e consultar as regras vigentes antes de usar os resultados.

Os comprovantes ficam em `estado/comprovantes/respostas`, e os manifestos compartilhados ficam em `estado/comprovantes/manifestos`. Esses arquivos podem conter cópias locais das evidências selecionadas, citações e texto da resposta. Devem receber as mesmas condições de acesso e retenção dos dados de origem. Uma exclusão ou correção torna o comprovante antigo inadequado para entrega como atual. A versão 0.5 não garante eliminação de cópias históricas ou externas.

Uma checagem sem alegações opcionais retorna `not_requested` e segue o contrato de texto livre. A verificação e a complementação são locais e determinísticas. Elas não exigem uma chamada adicional ao modelo textual. O modelo pode produzir mais campos na resposta, cujo custo de tokens depende do uso real.

## Implantação e recuperação

Durante a publicação, `estado/implantacao.lock` sinaliza manutenção para impedir novas operações de conteúdo na ponte. O trabalhador é parado pela configuração e iniciado novamente após conferência de código, manual e autotestes. Os hashes aprovados incluem os módulos novos e seus testes. A cópia anterior de código, configuração e manual permite reversão compatível.

O estado da ponte e da execução informa a versão 0.5. A atividade do trabalhador informa `runtime_version` no seu estado local. A conferência em um cliente MCP de teste e a versão carregada pela conversa atual são verificações próprias. A CLI local atende a operação quando a sessão tiver ferramentas antigas ou bloqueadas pela política do cliente.

O histórico de uma demanda mantém suas etapas e efeitos. Se o contrato ou manifesto mudar durante uma demanda pendente, o coordenador exige replanejamento antes de continuar. A atualização não reexecuta silenciosamente uma entrevista antiga.

## Evidência e alcance

O laboratório anterior encontrou falhas de comparação de tipos, reserva concorrente de nomes e leitura de conhecimento sem confirmação. A integração acrescenta testes no coordenador, nos processos de gravação e nos clientes MCP e CLI. A avaliação usa dados fictícios e saídas controladas de modelo. Os questionários e interpretações pessoais legados conservam suas pendências documentais.

O custo do catálogo e da indexação permanece uma frente própria de trabalho. A redução medida na etapa local de complementação seletiva se refere aos casos estruturados avaliados. O relatório de implantação deve registrar a qualidade e o custo observados, a preservação dos registros existentes, as falhas e os limites ainda abertos.
