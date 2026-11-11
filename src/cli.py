"""CLI local para operação segura da ponte pessoal via terminal / Antigravity."""
import argparse
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
os.environ.setdefault('CEREBRO_PESSOAL_ACESSO', 'permitido')

import ponte_pessoal as p

def main():
    parser = argparse.ArgumentParser(description="CLI da Ponte MCP Pessoal")
    subparsers = parser.add_subparsers(dest="cmd")

    subparsers.add_parser("estado")
    subparsers.add_parser("listar-fontes")
    subparsers.add_parser("verificar-fluxo")
    subparsers.add_parser("autotestes")
    buscar_parser=subparsers.add_parser("buscar-contexto")
    buscar_parser.add_argument("consulta")
    conhecimento_parser=subparsers.add_parser("registrar-conhecimento")
    conhecimento_parser.add_argument("--pedido",required=True,help="Arquivo JSON com o pedido estruturado")
    contrib_parser=subparsers.add_parser("processar-contribuicao")
    contrib_parser.add_argument("--pedido",required=True,help="Arquivo JSON contendo texto original e extrações")
    subparsers.add_parser("executor-status")
    fila_parser=subparsers.add_parser("executor-enfileirar")
    fila_parser.add_argument("--key",required=True);fila_parser.add_argument("--tipo",required=True)
    cancel_parser=subparsers.add_parser("executor-cancelar");cancel_parser.add_argument("execution_id")
    decisao_parser=subparsers.add_parser("preparar-decisao");decisao_parser.add_argument("--pedido",required=True)

    subparsers.add_parser('estado-execucao')
    subparsers.add_parser('listar-demandas').add_argument('--limite',type=int,default=20)
    subparsers.add_parser('liberar-recuperacao').add_argument('job_id')
    for command in ('iniciar-demanda','responder-pendencia','registrar-documento','concluir-avaliacao','pontuar-avaliacao','adotar-melhoria','reverter-melhoria','registrar-revisao','avaliar-resposta','consultar-comprovante'):
        subparsers.add_parser(command).add_argument('--pedido',required=True)
    for command in ('consultar-demanda','cancelar-demanda'):
        subparsers.add_parser(command).add_argument('execution_id')

    ler_parser = subparsers.add_parser("ler-fonte")
    ler_parser.add_argument("record_id")

    reg_parser = subparsers.add_parser("registrar-fonte")
    reg_parser.add_argument("--key", required=True)
    reg_parser.add_argument("--titulo", required=True)
    reg_parser.add_argument("--conteudo", required=True)

    ret_parser = subparsers.add_parser("retificar-fonte")
    ret_parser.add_argument("--key", required=True)
    ret_parser.add_argument("--record-id", required=True)
    ret_parser.add_argument("--revisao", type=int, required=True)
    ret_parser.add_argument("--conteudo", required=True)
    ret_parser.add_argument("--motivo", required=True)

    cons_parser = subparsers.add_parser("consultar")
    cons_parser.add_argument("--key", required=True)

    args = parser.parse_args()

    functions={'iniciar-demanda':p.iniciar_demanda,'responder-pendencia':p.responder_pendencia,
               'registrar-documento':p.registrar_documento,'concluir-avaliacao':p.concluir_avaliacao,
               'pontuar-avaliacao':p.pontuar_avaliacao,'adotar-melhoria':p.adotar_melhoria,'reverter-melhoria':p.reverter_melhoria,'registrar-revisao':p.registrar_revisao,
               'avaliar-resposta':p.avaliar_resposta,'consultar-comprovante':p.consultar_comprovante}
    if args.cmd in functions:
        res=functions[args.cmd](**json.loads(Path(args.pedido).read_text(encoding='utf-8-sig')))
    elif args.cmd=='estado-execucao':res=p.estado_execucao()
    elif args.cmd=='listar-demandas':res=p.listar_demandas(args.limite)
    elif args.cmd=='liberar-recuperacao':res=p.liberar_recuperacao(args.job_id)
    elif args.cmd=='consultar-demanda':res=p.consultar_demanda(args.execution_id)
    elif args.cmd=='cancelar-demanda':res=p.cancelar_demanda(args.execution_id)
    elif args.cmd == "estado":
        res = p.estado()
    elif args.cmd == "listar-fontes":
        res = p.listar_fontes()
    elif args.cmd == "ler-fonte":
        res = p.ler_fonte(args.record_id)
    elif args.cmd == "registrar-fonte":
        res = p.registrar_fonte(args.key, args.titulo, args.conteudo)
    elif args.cmd == "retificar-fonte":
        res = p.retificar_fonte(args.key, args.record_id, args.revisao, args.conteudo, args.motivo)
    elif args.cmd == "consultar":
        res = p.consultar_operacao(args.key)
    elif args.cmd == "verificar-fluxo":
        res = p.verificar_fluxo()
    elif args.cmd == "autotestes":
        res = p.executar_autotestes()
    elif args.cmd == "buscar-contexto":
        res = p.buscar_contexto(args.consulta)
    elif args.cmd == "registrar-conhecimento":
        res = p.registrar_conhecimento(**json.loads(Path(args.pedido).read_text(encoding='utf-8-sig')))
    elif args.cmd == "processar-contribuicao":
        res = p.processar_contribuicao(**json.loads(Path(args.pedido).read_text(encoding='utf-8-sig')))
    elif args.cmd == "executor-status":res=p.estado_executor()
    elif args.cmd == "executor-enfileirar":res=p.enfileirar_manutencao(args.key,args.tipo)
    elif args.cmd == "executor-cancelar":res=p.cancelar_execucao(args.execution_id)
    elif args.cmd == "preparar-decisao":res=p.preparar_decisao(**json.loads(Path(args.pedido).read_text(encoding='utf-8-sig')))
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
