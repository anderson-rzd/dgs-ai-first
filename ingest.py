#!/usr/bin/env python3
"""
Script de ingestão dos documentos da NovaTech no pipeline de RAG.

Uso:
    python ingest.py [--docs-dir CAMINHO] [--reset]

Flags:
    --docs-dir  Diretório com os arquivos .md (padrão: diretório atual)
    --reset     Apaga e recria a coleção antes de ingerir (re-ingestão completa)
"""

import argparse
import glob
import sys
from pathlib import Path

from pipeline.chunker import chunk_markdown
from pipeline.embedder import embed_texts
from pipeline.store import reset_collection, store_chunks


DOCS_PATTERN = [
    "POL-001-politica-devolucao.md",
    "PROC-042-frete-especial-v1.md",
    "PROC-042-v2-frete-especial-revisado.md",
    "SLA-2024-tabela-sla-clientes.md",
    "FAQ-atendimento.md",
]


def ingest(docs_dir: str = ".", reset: bool = False) -> None:
    base = Path(docs_dir)

    if reset:
        print("Resetando coleção ChromaDB...")
        reset_collection()

    all_chunks = []
    for doc_name in DOCS_PATTERN:
        path = base / doc_name
        if not path.exists():
            print(f"  [AVISO] Arquivo não encontrado: {path}")
            continue

        print(f"Processando: {doc_name}")
        chunks = chunk_markdown(str(path))
        print(f"  → {len(chunks)} chunks gerados")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("Nenhum chunk gerado. Verifique os arquivos de entrada.")
        sys.exit(1)

    print(f"\nTotal de chunks: {len(all_chunks)}")
    print("Gerando embeddings (pode levar alguns segundos no primeiro uso)...")

    texts = [c.content for c in all_chunks]
    embeddings = embed_texts(texts)

    print("Armazenando no ChromaDB...")
    store_chunks(all_chunks, embeddings)

    print("\n✓ Ingestão concluída com sucesso!")
    print(f"  Chunks armazenados: {len(all_chunks)}")
    print(f"  Documentos processados: {len(DOCS_PATTERN)}")

    print("\nResumo dos chunks por documento:")
    from collections import Counter
    counts = Counter(c.source_doc for c in all_chunks)
    for doc, count in sorted(counts.items()):
        print(f"  {doc}: {count} chunks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestão de documentos NovaTech no ChromaDB")
    parser.add_argument("--docs-dir", default=".", help="Diretório com os arquivos .md")
    parser.add_argument("--reset", action="store_true", help="Apaga e recria a coleção antes de ingerir")
    args = parser.parse_args()

    ingest(docs_dir=args.docs_dir, reset=args.reset)


if __name__ == "__main__":
    main()
