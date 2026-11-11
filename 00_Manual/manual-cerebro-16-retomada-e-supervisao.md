# Retomada de tarefas e supervisão do trabalhador

Este complemento acrescenta recuperação controlada à execução 0.5. Os capítulos anteriores, os limites de acesso e os contratos de origem, confirmação e revisão continuam vigentes. Os resultados específicos da implantação devem ser consultados no relatório de recuperação.

## Tarefas que vencem

Uma tarefa de contribuição guarda primeiro o relato original e depois executa etapas como busca, extração e ligação. Se o prazo da tarefa expirar, o trabalhador registra a falha; isso não transforma a origem em resultado processado e não apaga o relato.

O agendador pode criar uma nova demanda ligada à demanda anterior e à mesma revisão da fonte. Ele considera apenas falhas de prazo de contribuições, com origem atual e disponível, sem etapa de gravação aplicada, falha ou incerta. Ele também confere se outro registro já referencia a origem e se a fonte já pertence a outra demanda. Quando há dúvida, a recuperação fica para revisão. Os estados, efeitos e erros antigos são preservados.

A nova chave é determinística e a ligação entre tarefa antiga, demanda e trabalho novos é registrada. Após uma interrupção entre criação e enfileiramento, a repetição reutiliza a mesma demanda. Cada trabalho original admite uma recuperação automática. Uma recuperação que também expire não origina uma cadeia de tentativas. O agendador cria no máximo uma recuperação por verificação, respeitando os limites da fila e as configurações existentes de chamadas e tempo.

`estado/fila.sqlite3` guarda `recovery_links` para as recuperações e `recovery_review` para motivos de revisão. Esses registros não são comprovação de sucesso: é preciso consultar a demanda nova e suas etapas. Processar uma contribuição pode gerar chamadas ao modelo e consumir recursos dentro dos limites configurados.

Falhas de referências inexistentes, tipos incompatíveis, conteúdo não sustentado ou efeitos incertos não são tratadas como simples prazo vencido. Exigem uma correção ou revisão própria. Uma referência não é inventada para completar uma ligação, e uma extração inválida não se transforma em fato.

## Supervisão do trabalhador

O supervisor verifica periodicamente se a configuração autoriza a execução, se há manutenção e se existe um processo do trabalhador. Se o acesso estiver desativado, houver manutenção ou a consulta de processos falhar, ele não inicia outra instância. Quando autorizado e ausente, solicita o início do trabalhador, que continua sujeito à sua trava exclusiva, ao código aprovado, aos autotestes e aos demais contratos.

A tarefa do Windows verifica o supervisor a cada dois minutos enquanto a sessão do usuário estiver conectada. Ela também pode executar com o computador em bateria. Não há garantia de execução com o computador desligado, suspenso, sem sessão conectada ou se o agendador do Windows falhar. A presença de configuração e um estado antigo do trabalhador não provam atividade atual; confira o processo e a data do último estado.

## Comprovação e manutenção

Os testes da recuperação usam apenas dados fictícios. A instalação deve preservar um backup de código, configuração e manual, conferir os hashes do pacote testado e manter os relatos pessoais. Testes anteriores continuam necessários. O teste de processo fictício e a verificação do supervisor com trabalhador ativo não comprovam, por si, que um reinício real do Windows foi observado e validado.

Uma alteração no manifesto do manual muda o contexto de demandas antigas, que podem exigir replanejamento. Nunca atualizar silenciosamente seu contexto nem repetir um efeito confirmado para forçar a conclusão. Verificar o estado depois da atualização e documentar os efeitos realmente observados.
