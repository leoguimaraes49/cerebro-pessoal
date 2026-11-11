#!/usr/bin/env python3
"""
Assistente de Inicialização Limpa do Cérebro Pessoal
Configura um novo cofre do Obsidian completamente vazio e inicializa
os bancos SQLite com integridade estrutural para um novo usuário.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

VAULT_DIRS = [
    "00_Manual",
    "10_Entidades",
    "20_Afirmacoes",
    "30_Fontes",
    "50_Sinteses",
    "70_Operacao",
    "80_Visoes"
]

def inicializar_novo_cofre(caminho_cofre: Path, nome_usuario: str = "Meu Cérebro Pessoal"):
    print(f"📁 Inicializando novo cofre em: {caminho_cofre}")
    caminho_cofre.mkdir(parents=True, exist_ok=True)

    for d in VAULT_DIRS:
        sub = caminho_cofre / d
        sub.mkdir(exist_ok=True)
        print(f"  ✓ Diretório criado: {d}/")

    manual_origem = ROOT / "00_Manual"
    if manual_origem.is_dir():
        for arq in manual_origem.glob("*.md"):
            destino_arq = caminho_cofre / "00_Manual" / arq.name
            if not destino_arq.exists():
                destino_arq.write_bytes(arq.read_bytes())

    # Inicializar os bancos de dados
    print("\n📦 Inicializando bancos relacionais e ledger atômico...")
    os.environ.setdefault("EMC_SYSTEM", str(ROOT))
    os.environ.setdefault("EMC_VAULT", str(caminho_cofre.resolve()))
    from nucleo import Store
    from conhecimento import Knowledge
    store = Store(str(ROOT), str(caminho_cofre.resolve()))
    knowledge = Knowledge(store)

    # Criação da nota de boas-vindas / início
    inicio_file = caminho_cofre / "README.md"
    if not inicio_file.exists():
        inicio_file.write_text(
            f"# {nome_usuario}\n\n"
            "Este cofre foi gerado pelo **Epistemic Memory Core**.\n"
            "Todos os registros adicionados aqui por assistentes de IA (via MCP) "
            "possuem verificação atômica de integridade, controle estrito de revisões e "
            "separação epistemológica entre relatos primários e inferências.\n\n"
            "## Primeiros Passos\n"
            "1. Conecte seu assistente de IA ao servidor MCP (`src/ponte_pessoal.py`).\n"
            "2. Inicie suas conversas ou relatos por voz.\n"
            "3. Execute o dashboard (`python src/dashboard.py`) para monitorar o estado em tempo real.\n",
            encoding="utf-8"
        )
        print("  ✓ Criada nota de introdução: README.md")

    print("\n✅ Inicialização concluída com sucesso!")
    print(f"Seu novo cofre limpo está pronto para receber seus dados em: {caminho_cofre}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Inicializa um novo cofre limpo para o Cérebro Pessoal.")
    parser.add_argument("--destino", default=str(ROOT / "meu-cofre"), help="Caminho onde o novo cofre será criado")
    parser.add_argument("--nome", default="Meu Cérebro Pessoal", help="Nome ou título da sua base")
    args = parser.parse_args()
    inicializar_novo_cofre(Path(args.destino), args.nome)
