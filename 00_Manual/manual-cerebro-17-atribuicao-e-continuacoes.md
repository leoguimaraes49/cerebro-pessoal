# Atribuição de informações e retomada de continuações — complemento 07

Este complemento preserva os contratos dos capítulos 01–16 e acrescenta controles à execução 0.5. A implantação e a atividade corrente devem ser conferidas no relatório e no serviço; a existência deste capítulo não comprova ativação.

## Pessoas, citações e identidade

Um trecho literal verdadeiro pode estar ligado à pessoa errada. A validação estrutural, o hash e a confirmação da gravação não certificam a verdade da afirmação.

O subprocesso local `atribuicao.py` compara nomes e aliases de pessoas identificadas, a pessoa referenciada na afirmação e o trecho da fonte. Uma menção explícita a outra pessoa impede a gravação da atribuição conflitante. Valores literais encontrados em uma frase de outra pessoa também são recusados nas rotas legadas. Frases com várias pessoas são separadas conservadoramente; homônimos e pronomes sem resolução não são decididos pela ordem do catálogo.

`execucao.json.owner_person_id` identifica explicitamente o proprietário quando se deseja resolver a primeira pessoa do relato ou “você” na resposta. A identidade deve existir e ser do tipo pessoa; não inferir proprietário por popularidade, nome ou primeira entidade recuperada. O campo é opcional para bases anteriores. Alterá-lo exige rever o contexto de demandas pendentes.

A primeira pessoa em publicação, documento externo, página ou saída de ferramenta não é vinculada automaticamente ao proprietário. A autoria e a natureza da fonte precisam permanecer separadas do sujeito da afirmação.

Extrações com `evidence_quote` retêm `attribution_evidence` com a fonte/revisão e o trecho literal. `evidence_source` distingue o relato original de um esclarecimento. `$resposta` aponta somente à fonte da resposta recebida na mesma demanda. `attribution_resolution_ref`, quando necessário para resolver um pronome do relato, deve apontar a essa resposta e constar em `source_refs`. A resposta não é copiada para dentro da fala original.

O coordenador tenta reparar uma proposta inválida dentro do orçamento existente. Se o relato realmente não identificar a pessoa, registra pergunta e espera. A resposta vira fonte separada e a retomada verifica novamente revisões, texto e bases. Uma troca explícita de pessoa proposta pelo modelo é primeiro um erro técnico, não uma obrigação de o usuário consertar a extração. Uma lista vazia não transforma uma proposta de identidade rejeitada em processamento aprovado.

## Respostas e clientes de entrevista

O coordenador verifica a atribuição também antes da entrega de respostas. Pode tentar uma correção dentro dos mesmos limites; se não houver suporte, entrega uma limitação em vez da descrição conflitante. `avaliar_resposta`, inclusive sem `claims` opcionais, aplica o controle local quando há citações. A CLI mantém `avaliar-resposta --pedido ARQUIVO.json`.

Antes de descrever o perfil, biografia, formação ou características de uma pessoa, o cliente deve recuperar as fontes atuais, distinguir proprietário e terceiros e enviar resposta com citações a `avaliar_resposta`. Se a atribuição for recusada, corrigir ou declarar a limitação. Não acrescentar na fala ou no texto final uma caracterização pessoal que não passou por essa conferência. O resultado `confirmed` de uma gravação não autoriza apresentá-la como fato verificado.

Esses controles têm alcance delimitado: menções conhecidas, primeira pessoa configurada e coincidências literais. Não são um resolvedor universal de correferência ou um certificador de paráfrases, causalidade, diagnósticos e texto livre. Pedidos legados sem fragmento explícito continuam provisórios; não se inventa retroativamente uma comprovação. Um cliente externo que ignore o contrato pode gerar uma fala fora do serviço; o software local não controla a geração de áudio desse cliente.

## Continuação e confirmação perdida

Ao concluir um trabalho que exige outro, a fila registra na mesma transação a intenção e o contrato do filho em `continuation_contracts`. Esse contrato congela tipo, tentativas, timeout e duração. A publicação e a confirmação podem ser retomadas sem reconstruir o pedido com uma configuração posterior.

Quando já existe um filho de uma intenção legada, a migração confere a chave determinística, o tipo, a ausência de entrada substituta, o fingerprint e os limites originais. Reconcilia o filho existente sem duplicá-lo ou renovar seu prazo. Intenções/contratos divergentes permanecem pendentes para revisão; não são ajustados silenciosamente.

As permissões, manutenção, capacidade da fila e frequência de execução atuais continuam sendo respeitadas. A mudança não aumenta os orçamentos do modelo, não cria novas permissões e não instala correções arbitrárias vindas de uma nota.

## Validação, comparação e reversão

Os casos adversariais incluem troca de duas pessoas, aliases homônimos, valores numéricos trocados, primeira pessoa, resposta final conflitante, esclarecimento com origem própria, correção da fonte da resposta e retomada sem repetir gravações. A fila é testada com confirmação perdida, alterações de limites, intenções legadas, contratos adulterados e publicadores concorrentes. Testes usam dados fictícios e provedores controlados.

O pacote deve conservar as melhorias anteriores e passar pelos testes de regressão antes da ativação. Registrar o hash do código efetivamente validado, cópias consistentes e comparação dos dados pessoais antes/depois. A reversão de código não restaura bancos antigos sobre notas mais recentes; mudanças posteriores exigem revisão própria. Uma falha ou teste ausente não conta como aprovação.
