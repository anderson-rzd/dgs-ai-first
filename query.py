#!/usr/bin/env python3
"""
Script de busca interativa no pipeline de RAG.

Uso:
    python query.py "Qual o prazo de devolução?"
    python query.py --n 3 "Qual o SLA do cliente Gold?"
    python query.py --show-prompt "Frete para 600kg para Manaus?"

Flags:
    --n N            Número de chunks a recuperar (padrão: 5)
    --show-prompt    Exibe o prompt completo montado pelo pipeline
"""

import argparse
import sys

from pipeline.embedder import embed_query
from pipeline.store import search
from pipeline.prompt_builder import build_prompt, format_prompt_for_display


def query(question: str, n_results: int = 5, show_prompt: bool = False) -> None:
    print(f"\nPergunta: {question}")
    print("-" * 60)

    print("Gerando embedding da pergunta...")
    query_embedding = embed_query(question)

    print(f"Buscando {n_results} chunks mais similares...")
    results = search(query_embedding, n_results=n_results)

    if not results:
        print("Nenhum chunk encontrado na base de dados. Execute ingest.py primeiro.")
        sys.exit(1)

    print(f"\nChunks recuperados ({len(results)}):")
    for i, chunk in enumerate(results, 1):
        print(f"\n  [{i}] Score: {chunk['score']:.4f}")
        print(f"       Fonte: {chunk['source_doc']} / {chunk['section_title']}")
        print(f"       ID: {chunk['chunk_id']}")
        print(f"       Conteúdo (primeiros 200 chars): {chunk['content'][:200]}...")

    if show_prompt:
        prompt = format_prompt_for_display(results, question)
        print(prompt)
    else:
        print("\n[Use --show-prompt para ver o prompt completo gerado pelo pipeline]")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca semântica no pipeline RAG NovaTech")
    parser.add_argument("question", help="Pergunta a ser buscada")
    parser.add_argument("--n", type=int, default=5, help="Número de chunks a recuperar")
    parser.add_argument("--show-prompt", action="store_true", help="Exibe o prompt completo")
    args = parser.parse_args()

    query(question=args.question, n_results=args.n, show_prompt=args.show_prompt)


if __name__ == "__main__":
    main()
