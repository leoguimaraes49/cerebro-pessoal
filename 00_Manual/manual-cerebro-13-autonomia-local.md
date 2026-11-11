# Execução local em segundo plano — versão 0.3

## Finalidade

Esta entrega acrescenta um trabalhador local para manutenção determinística. Ele roda sem conversa aberta enquanto o processo e o computador permanecem ativos. Não chama modelos por assinatura, não pesquisa a biografia na web e não altera código ou instrumentos a partir do conteúdo de notas. O núcleo de fontes e o catálogo de conhecimento foram preservados.

## Ordem das capacidades

1. **Memória:** fila persistente, verificação das fontes controladas, geração observada do cofre e histórico de execuções. Uma alteração observada agenda auditoria.
2. **Ligações:** a auditoria usa as referências existentes e detecta derivados que precisam ser revalidados. O executor não inventa relações semânticas a partir de palavras-chave. Novas relações ainda precisam ser fornecidas pela IA às ferramentas de conhecimento.
3. **Apoio a decisões:** uma ferramenta registra uma decisão em consideração, uma análise provisória de opções e questões abertas. Distingue opções relatadas pelo usuário de sugestões da IA, não escolhe nem executa uma ação externa.

## Fila e estados

O estado fica em `estado/fila.sqlite3`. Cada trabalho possui identidade UUID, chave de pedido, contrato por tipo, prazo total, tentativas, tempo por tentativa, responsável e token de reserva. Eventos registram entrada na fila, início, conclusão, falha, perda da reserva e cancelamento. Repetir um pedido idêntico não cria outro trabalho. Uma chave com outro contrato é rejeitada.

Estados implementados: `queued`, `running`, `cancelling`, `completed`, `failed`, `cancelled`. Espera por resultado de modelo e suspensão de tarefas semânticas ainda não são executadas nesta versão. Configuração desativada ou autorização revogada impede novas etapas; trabalho não confirmado pode precisar ser reconciliado pela reserva vencida ao retomar.

Se o responsável desaparecer, uma reserva vencida pode voltar à fila dentro do mesmo limite de tentativas e prazo. O responsável antigo não consegue confirmar a tarefa após perder a reserva. Não se promete execução exatamente uma vez em todo cenário; efeitos das operações de manutenção são limitados e reconstruíveis.

## Funções permitidas

- `audit_vault`: compara gerações antes e depois da auditoria, examina referências e vigência técnica e guarda o resultado. Se a base mudar durante a auditoria, a tentativa não é declarada atual.
- `refresh_view`: atualiza `80_Visoes/Manutenção automática.md`. Alteração externa nessa visão é tratada como conflito, não sobrescrita silenciosamente.
- `selftest`: executa as suítes de código em cofres fictícios, reutilizando somente resultado aprovado para o mesmo hash de código.

Uma visão gerada não é uma nova experiência pessoal. Ela fica fora da varredura de conhecimento para evitar que a própria manutenção se dispare indefinidamente.

## Limites iniciais

| Controle | Valor padrão |
|---|---|
| Varredura de mudanças | A cada 60 segundos |
| Trabalhos iniciados | Até 12 por hora |
| Pendências na fila | Até 100 |
| Tentativas por trabalho | Até 3 |
| Tempo por tentativa | Até 120 segundos |
| Prazo total do trabalho | Até 600 segundos, sem renovação por retentativa |
| Retentativa após falha | Espera crescente a partir de 10 segundos |
| Varredura de arquivos | Até 10 mil notas, 2 MB por arquivo e 64 MB no total |
| Rede e provedores de modelo | Nenhuma chamada pelo executor |

Configuração: `config/autonomia.json`. Por padrão, ausente ou desabilitada, ela não autoriza leitura do cofre em segundo plano. A habilitação é uma operação local expressa. O arquivo não vem do conteúdo de uma fonte.

## Versão de código e controle

O serviço compara o hash dos arquivos cobertos com a versão aprovada na configuração. Se houver alteração de código, ele pede atenção e deixa de iniciar conteúdo pela fila até validação e habilitação local da versão. Não adota nem reescreve código silenciosamente. Depois de mudar o código, o trabalhador deve ser reiniciado para carregar a nova versão.

O arquivo `estado/worker.json` contém PID, último sinal de atividade e estado observado. Ele é diagnóstico local, não prova permanente de que o processo continua vivo. Um arquivo antigo de estado não deve ser apresentado como conexão atual sem verificação.

Comandos:

```powershell
# Validar e habilitar a versão do serviço.
python src/autonomia.py enable
# Executar o trabalhador (ou utilize scripts/iniciar-trabalhador.ps1 em segundo plano).
python src/autonomia.py serve
# Desabilitar e solicitar parada cooperativa.
python src/autonomia.py disable
# Consultar a fila sem depender de recarregamento do catálogo MCP.
python src/cli.py executor-status
```

As ferramentas `estado_executor`, `enfileirar_manutencao`, `consultar_execucao` e `cancelar_execucao` ficam disponíveis em novas conexões MCP. Não iniciam automaticamente outro trabalhador. O arquivo de reserva impede dois trabalhadores locais de manterem o mesmo laço de manutenção; a reserva de cada trabalho também é verificada no banco.

## Apoio a decisões

`preparar_decisao` recebe chave de operação, título, situação, opções, referências às fontes atuais e lacunas. Cada opção possui `descricao`, `origem` (`relatada_pelo_usuario` ou `sugerida_pela_ia`), `pros`, `contras`, `incertezas`. Os prós e contras permanecem formulações da IA; a confirmação da gravação não os torna verdade ou previsão validada.

A ferramenta precisa de pelo menos uma opção relatada pelo usuário, para não inventar o que ele teria considerado. Grava uma entidade `decision` com estado `considering`, uma síntese provisória e perguntas ligadas às lacunas. Resultado parcial informa os efeitos já confirmados. Repetir a operação não duplica efeitos confirmados. Se a fonte mudar, a análise derivada fica suspensa pela verificação de dependências existente.

## Testes e comparação com o estado anterior

Antes, todo trabalho dependia de uma chamada do cliente. Agora mudanças no cofre podem originar uma auditoria local sem conversa e produzir uma visão de manutenção. A nova fila acrescenta orçamento, responsável, retentativas limitadas e eventos. A análise de decisões ganha entrada estruturada e preserva a distinção entre opção relatada e sugerida.

O teste com trabalhador real em subprocesso usa somente fixture fictícia: aguarda auditoria e atualização de visão, desabilita a configuração, espera a parada e verifica o estado. Outros testes cobrem disputa por responsabilidade, recuperação de reserva expirada, prazo, teto por hora, limite de fila, cancelamento, revogação, mudança de código, tamanho da base e edição externa da visão. O teste MCP verifica também descoberta e bloqueio das novas ferramentas.

Histórico: `estado/autotestes/` para suítes e eventos em `estado/fila.sqlite3` para manutenção. Nenhum log é chamado de imutável; mesmos privilégios locais ainda podem alterá-lo. Resultados detalhados da implantação ficam no relatório desta entrega.

## O que permanece fora do alcance

- Não existe chamada autônoma a um modelo sem um provedor, credenciais, orçamento e política específicos.
- Pesquisa científica em segundo plano, interpretação semântica autônoma e promoção de novos agentes/código continuam pendentes.
- Busca vetorial e cache com invalidação completa ainda não estão implementados.
- Não há serviço registrado para reiniciar automaticamente com o Windows. A fila sobrevive ao reinício; o trabalhador precisa ser iniciado novamente.
- O executor não migra nem corrige pontuações clínicas antigas sozinho e não inventa perfil.
- Autenticação individual por IA, criptografia e exclusão de cópias externas mantêm as limitações anteriores.
- Autoria e integridade de uma nota não comprovam a veracidade do conteúdo.
