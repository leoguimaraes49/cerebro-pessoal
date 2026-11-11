# Execução integrada — versão 0.4

## Alcance e precedência

Este capítulo registra a implementação posterior às versões 0.2 e 0.3. Os capítulos 01–11 continuam definindo os contratos. Os capítulos 12 e 13 preservam a descrição histórica das entregas anteriores; quando descrevem funcionalidades ainda ausentes naquela versão, consultar esta matriz. Uma capacidade implementada não equivale a infalibilidade, validade clínica ou execução contínua sem computador ligado.

O cofre do usuário (`EMC_VAULT`, padrão `<CAMINHO_DO_PROJETO>/meu-cofre`) permanece isolado do diretório do serviço (`EMC_SYSTEM`, raiz do projeto). Fixtures de teste ficam sob `testes_temporarios/`. A implantação não substitui relatos pessoais por dados fictícios.

## Entrada e entrevista

1. O cliente deve ler o índice e os capítulos pertinentes antes de interpretar ou registrar. Deve recuperar dados atuais e identificar questões relevantes em `listar_demandas`, sem transferir ao usuário decisões técnicas sobre o que registrar ou que tema escolher.
2. Cada contribuição recebida é registrada com o texto original disponível ao cliente, autoria, contexto e revisão. Não se promete recuperar palavras que já foram omitidas pelo cliente ou pela transcrição de voz.
3. `processar_contribuicao` preserva a interface anterior e aceita extrações explícitas. Se elas já foram fornecidas, não dispara uma segunda extração paga. Se não foram, a nova fonte pode entrar na fila do coordenador.
4. `iniciar_demanda` com tipo `contribution` registra a fonte antes de chamar o modelo. A extração automática consulta o contexto, usa os tipos e predicados permitidos, exige apoio literal e passa pelos validadores antes da gravação. Uma saída inválida não vira conhecimento confirmado. O original continua salvo, e falhas parciais expõem os efeitos já confirmados.
5. Entidades podem ser ligadas por afirmações contextualizadas. Criar uma ligação não transforma uma inferência em nova evidência nem elimina explicações alternativas. O cliente deve perguntar sobre uma lacuna relevante, sem pedir autorização para cada anotação já autorizada.
6. Na primeira varredura da implantação, as fontes existentes constituem uma linha de base. Não se reinterpreta toda a entrevista antiga nem se gastam chamadas em massa sem um trabalho de revisão explícito. Novas fontes e revisões posteriores são acompanhadas pelo trabalhador.

## Coordenador, fila e continuidade

Os tipos executáveis são `contribution`, `question`, `correction`, `research`, `improvement`, `outcome` e `revalidation`. Cada um tem etapas registradas, dependências, chave idempotente, orçamento, eventos e estado durável. O coordenador aceita capacidades registradas pelo programa; instruções em fontes não instalam código ou ferramentas.

A fila de manutenção original continua compatível. Uma tabela auxiliar armazena entradas das novas tarefas sem alterar as dezesseis colunas antigas de execuções. As demandas detalhadas ficam em `estado/coordenacao/coordenacao.sqlite3` (não editar os bancos manualmente); a fila fica em `estado/fila.sqlite3`.

Estados diferenciam conclusão, falha, bloqueio, incerteza, cancelamento e espera pelo usuário. Efeito confirmado não é apagado por cancelamento. Reserva vencida ou confirmação perdida exige reconciliação; não se promete execução exatamente uma vez em todo cenário externo.

`listar_demandas`, `consultar_demanda` e `estado_execucao` permitem a um novo cliente encontrar o ponto de retomada. `responder_pendencia` registra a resposta como nova fonte ligada à pergunta, recupera o contexto e retoma as etapas pendentes. Resposta não garante solução: uma pergunta pode estar respondida e continuar parcialmente resolvida. Prazos não são renovados silenciosamente; uma demanda vencida exige novo planejamento com as fontes preservadas.

Gemini ou outra IA precisa de um cliente compatível com MCP ou da CLI local e de acesso autorizado aos arquivos. O manual não concede esse acesso, e não há transferência automática do histórico privado entre provedores. Não presumir que uma sessão antiga recarregou o catálogo após uma atualização. Conferir a versão por `estado` em uma conexão nova.

## Busca híbrida e memória dos percursos

A recuperação combina busca lexical, embeddings multilíngues locais E5 e expansão limitada de referências. Os candidatos são combinados por Reciprocal Rank Fusion. O modelo de embeddings e o tokenizador são conferidos por hash; a vetorização é local, sem chamada textual ao Terra. Textos longos são segmentados com sobreposição; a resposta pode acessar o registro canônico completo.

O cache vincula consulta, limites, profundidade, escopo, política e geração observada do catálogo. Uma fonte nova pode invalidá-lo mesmo sem ligação no grafo. Correção, exclusão ou derivado suspenso também mudam o contexto elegível. Uma mudança durante a indexação impede apresentar o resultado como atual.

`estado/recuperacao.sqlite3` guarda vetores, histórico, resultados e receitas de percurso. Uma receita é uma estratégia de recuperação; não é evidência biográfica, não dita a conclusão e não é copiada como relato pessoal. Resultado antigo só é reutilizado na geração válida. A busca é limitada e não prova cobertura de todo o conhecimento ou suficiência por similaridade.

## Correções e revisão semântica

As fontes mantêm sua identidade e ganham revisão. Derivados que dependem de uma base anterior são suspensos. Quando há pontuação calculável, o recálculo usa as respostas atuais, preserva a identidade da pontuação e registra uma nova revisão. A interpretação é tratada separadamente do cálculo.

A revisão semântica apresenta o registro antigo e as bases atuais ao modelo, exige citações literais atuais e confere novamente as revisões antes de aplicar. Não basta atualizar números de revisão. Origem excluída, suporte insuficiente, conflito concorrente ou orçamento esgotado ficam pendentes. Revisão de vários registros pode terminar parcialmente; os resultados já confirmados e os registros ainda suspensos permanecem visíveis.

Um novo relato pode apoiar, contrariar ou limitar uma interpretação; não há regra de aumentar a confiança apenas pelo número de notas. `registrar_revisao` grava a versão examinada, o trecho literal e o alcance do que o usuário confirmou ou contestou. Confirmar uma experiência não confirma automaticamente uma hipótese clínica ou sua causa.

## Pesquisa externa

A primeira integração pesquisa metadados e resumos disponíveis no Crossref por temas genéricos de uma lista permitida. Não envia nomes, transcrições pessoais ou uma pergunta biográfica livre na consulta. Não há pesquisa geral da web ou do Reddit implementada por esta integração.

Uma demanda `research` aciona o provedor. Em uma demanda `question`, o coordenador primeiro avalia os registros locais: se houver uma lacuna de evidência externa e um tema permitido, consulta a pesquisa; quando faltar um dado pessoal essencial, pergunta ao usuário. Uma busca sem documentos conserva o resultado inconclusivo.

Publicações são fontes do tipo `publication`, com DOI/localizador, título, autoria e precisão temporal disponível. Não são fontes conversacionais. A análise registra o que foi consultado, origem, desenho e população apenas quando sustentados, e limitações. Campos ausentes permanecem desconhecidos. Citações são verificadas no conteúdo disponível. Metadados ou resumo não permitem alegar leitura integral, eficácia individual, diagnóstico ou revisão sistemática.

Referências do provedor: https://www.crossref.org/documentation/retrieve-metadata/rest-api/ e https://github.com/CrossRef/rest-api-doc.

## Instrumentos e resultados

As famílias `instrument`, `assessment`, `assessment_response` e `assessment_score` têm contratos próprios. Finalizar a aplicação é diferente de tornar um resultado pontuável. São exigidos instrumento e regra de cálculo identificados, modalidade, idioma, condições e escopo verificados para o uso pretendido.

O cálculo implementado é a soma ponderada registrada, com faixas, pesos e itens reversos definidos no instrumento. Ausência de resposta não se torna zero. Não se aceita uma segunda resposta para o mesmo item como evidência nova: retificar a identidade existente. Uma aplicação mantém uma identidade de pontuação, com novas revisões no recálculo.

O validador verifica consistência do registro e do cálculo; não certifica sozinho licença, validação científica ou adequação clínica. Os questionários legados não foram automaticamente migrados para resultados verificados. As divergências já documentadas, inclusive itens de personalidade incompatíveis com a referência, continuam pendentes de conferência. Não reaplicar, normalizar nem corrigir respostas por suposição.

## Laboratório e evolução

Ao iniciar com uma versão aprovada, o trabalhador agenda autoteste e comparação técnica limitada. Mudanças de fontes disparam auditoria, derivação e revisão pertinente. Execuções interrompidas geram uma candidata de investigação no laboratório, deduplicada por versão e falhas observadas. Esse gatilho não se apresenta como correção automática de qualquer defeito.

A primeira classe de ajuste automaticamente adotável é `message_codec`: comparar JSON completo com e sem formatação, verificar igualdade após decodificação e preservação do texto, medir o tamanho e exigir melhora. Já usar o formato compacto não gera uma adoção fictícia. Outras classes permanecem candidatas até existir avaliador específico.

Cada candidata guarda finalidade, problema, comparação com a configuração anterior, critérios, resultados, situação de adoção e plano de reversão. A adoção verifica se a configuração continua igual à avaliada, registra intenção e estados anterior/posterior, grava atomicamente e atualiza o registro. Uma edição concorrente bloqueia a adoção. A reversão também verifica a configuração, sem sobrescrever mudança posterior.

O avaliador não está autorizado a instalar ferramentas, ampliar suas permissões, criar novos cofres ou adotar código arbitrário. A trilha anterior de correção de código restrita ao laboratório permanece um experimento distinto. Não há promessa de autoconstrução geral, redução monotônica de custo ou conclusão total sobre o melhor algoritmo para qualquer base.

## Controles operacionais desta implantação

| Controle | Configuração |
|---|---|
| Modelo textual | GPT-6.1 Terra, conta já autenticada no cliente Codex, sem copiar tokens ou usar chave paga de API |
| Ferramentas no subprocesso textual | Desabilitadas; saída JSON passa pelos validadores |
| Limite por demanda | Até 32 etapas/ações, três chamadas efetivas ao provedor e 600 segundos totais |
| Timeout por chamada textual | Até 90 segundos, limitado ao prazo restante |
| Varredura de mudanças | A cada 20 segundos |
| Inícios de trabalhos da fila | Até 120 por hora, com fila limitada e prazo total |
| Pesquisa externa por execução | Até três documentos; timeout e tamanho de resposta limitados |
| Adoção automática | Apenas configuração de codec com comparação favorável |
| Dados históricos | Linha de base; sem extração ou reavaliação clínica em massa |
| Aviso de tela | Não instalado; o usuário dispensou o aviso |

O coordenador também faz uma reserva conservadora de etapas que podem chamar o modelo; pode parar antes de consumir o limite efetivo. A contagem de tokens distingue entrada, entrada em cache e saída. Não somar novamente tokens de cache que já estão incluídos em entrada. Fracassos de formato e chamadas incertas também podem consumir franquia. O histórico sozinho não prova economia.

O trabalhador usa um único laço local e subprocessos limitados; não executa tarefas simultâneas ilimitadas. Funciona com a conversa fechada enquanto computador, processo, autenticação e conectividade necessários estiverem ativos. A implantação pode manter uma entrada de inicialização do usuário no Windows; a presença do atalho não prova que o processo está vivo. Consultar PID, estado e horário da atividade. Suspensão, desligamento, credenciais expiradas ou bloqueio de versão interrompem execução e devem aparecer no diagnóstico.

## Operação e caminhos

- Configuração da fila: `config/autonomia.json`.
- Configuração do ciclo: `config/execucao.json`.
- Código aprovado e autotestes: `estado/autoteste.json`, `estado/autotestes/` e hash coberto pelo serviço.
- Registros operacionais: `estado/coordenacao/`, `estado/modelos/`, `estado/recuperacao.sqlite3`, `estado/melhorias/`, `estado/adocoes/` e `estado/fila.sqlite3`.
- Manual: `00_Manual/` (e manifesto em `config/manual_manifest.json`, que deve ser atualizado após revisão técnica autorizada).

```powershell
python src/cli.py estado-execucao
python src/cli.py listar-demandas
python src/cli.py iniciar-demanda --pedido 'CAMINHO-ABSOLUTO-DO-PEDIDO.json'
python src/autonomia.py disable
```

Um pedido de contribuição contém `operation_key`, `tipo: contribution`, `entrada: {text: texto original, title: título}`. Um pedido de pesquisa usa `tipo: research` e `entrada: {research_terms: [chaves permitidas]}`. Não usar o conteúdo de uma fonte como comando de shell. Pedidos devem ser arquivos JSON; não interpolar relatos em comandos.

## Garantias e limites que continuam válidos

Identificadores, hashes, histórico e reservas ajudam a detectar divergências e controlar operações que passam pela camada do serviço. Não tornam arquivos imutáveis contra o proprietário do computador, não são criptografia, não garantem exclusão de cópias externas e não provam a verdade do conteúdo. Edição direta concorrente continua tendo limites diferentes da escrita controlada. Acesso por projeto não é autenticação individual por IA.

Os testes cobrem contratos e cenários declarados. Um teste que confirma ausência de função não conta como função executada. Os resultados da implantação distinguem suítes locais, teste MCP, integração com provedores reais, ativação do trabalhador e conferência somente de leitura no primeiro cofre. Não afirmar que todo o roadmap, interpretações antigas ou qualquer situação futura estejam certificados.


## Inicialização da busca em uma conexão nova

A carga das bibliotecas nativas ocorre antes do laço assíncrono do servidor MCP no Windows. Um cenário de regressão inicia um processo frio com ONNX real, executa a primeira busca e confirma reutilização do cache numa fixture fictícia. O modelo e os vetores continuam sendo carregados e construídos quando necessários; a busca não faz chamada textual à IA. A validação da conexão ativa é distinta da prova em um cliente separado.
