#!/usr/bin/env python3
"""
Teste do pipeline RAG com as 5 perguntas do mapa de cobertura do Anexo B.

Compara os chunks recuperados pelo pipeline com o gabarito esperado,
calcula métricas de precisão por pergunta e gera relatório em Markdown.

Uso:
    python test_pipeline.py
    python test_pipeline.py --output relatorio-testes.md
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Optional

from pipeline.embedder import embed_query
from pipeline.store import search
from pipeline.prompt_builder import build_prompt


# ---------------------------------------------------------------------------
# Gabarito do Anexo B — mapa de cobertura
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    question: str
    # Palavras-chave que DEVEM aparecer no conteúdo de pelo menos um chunk recuperado.
    # Matching por conteúdo é mais robusto que matching por ID (IDs mudam com o chunker).
    expected_keywords: List[str]
    acceptable_keywords: List[str]
    expected_source: str          # documento esperado no topo do ranking
    notes: str = ""


TEST_CASES = [
    TestCase(
        question="Qual o prazo de devolução?",
        expected_keywords=["7 (sete) dias úteis", "data de recebimento"],
        acceptable_keywords=["Portal do Cliente", "coleta reversa", "processo padrão"],
        expected_source="POL-001-politica-devolucao",
        notes="Chunk central: seção 3.1 da POL-001 (7 dias úteis).",
    ),
    TestCase(
        question="Posso devolver carga perigosa?",
        expected_keywords=["não são elegíveis", "cargas perigosas", "Gestão de Riscos"],
        acceptable_keywords=["ramal 4500", "tratamento especial"],
        expected_source="POL-001-politica-devolucao",
        notes="Deve recuperar a seção de exceções da POL-001 que lista cargas perigosas.",
    ),
    TestCase(
        question="Qual o SLA do cliente Gold?",
        expected_keywords=["Gold", "2h úteis", "24h úteis"],
        acceptable_keywords=["Silver", "Standard", "incidentes críticos"],
        expected_source="SLA-2024-tabela-sla-clientes",
        notes="Tabela de SLA seção 2. Gold: 2h resposta, 24h resolução.",
    ),
    TestCase(
        question="Qual o SLA do cliente Platinum?",
        expected_keywords=["Não existem outros tiers", "Gold, Silver e Standard"],
        acceptable_keywords=["Platinum", "programa de fidelidade", "tier"],
        expected_source="SLA-2024-tabela-sla-clientes",
        notes="Deve recuperar a classificação de clientes que diz que Platinum NÃO existe.",
    ),
    TestCase(
        question="Como calcular o frete para 600kg com destino a Manaus?",
        expected_keywords=["Norte", "1.8", "Multiplicador regional"],
        acceptable_keywords=["1.6"],   # v1 antiga — aceitável mas risco de contradição
        expected_source="PROC-042-v2-frete-especial-revisado",
        notes="Deve usar versão v2 (mais recente). Risco: recuperar PROC-042 v1 junto (contradição).",
    ),
]

N_RESULTS = 8  # aumentado de 5 para capturar subsecções relevantes que ficam fora do top-5


# ---------------------------------------------------------------------------
# Lógica de avaliação
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    question: str
    retrieved_chunks: List[dict]
    expected_found: List[str]
    expected_missing: List[str]
    unexpected_found: List[str]
    precision: float
    recall: float
    notes: str = ""
    prompt: str = ""


def _strip_markdown(text: str) -> str:
    """Remove marcadores simples de markdown para busca de keywords."""
    import re
    text = re.sub(r"\*+", "", text)   # bold/italic
    text = re.sub(r"`+", "", text)    # code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    return text


def _keywords_in_results(keywords: List[str], results: List[dict]) -> List[str]:
    """Retorna quais keywords aparecem em pelo menos um chunk recuperado."""
    found = []
    all_content = _strip_markdown(" ".join(r["content"] for r in results))
    for kw in keywords:
        if kw.lower() in all_content.lower():
            found.append(kw)
    return found


def evaluate(test_case: TestCase, results: List[dict]) -> TestResult:
    expected_found = _keywords_in_results(test_case.expected_keywords, results)
    expected_missing = [k for k in test_case.expected_keywords if k not in expected_found]

    # "Inesperado" = nenhum chunk do documento esperado está no topo 3
    top3_sources = {r["source_doc"] for r in results[:3]}
    unexpected_found = [] if test_case.expected_source in top3_sources else [
        f"fonte esperada '{test_case.expected_source}' não está no top-3"
    ]

    recall = len(expected_found) / max(len(test_case.expected_keywords), 1)
    precision = 1.0 if test_case.expected_source in top3_sources else 0.5

    return TestResult(
        question=test_case.question,
        retrieved_chunks=results,
        expected_found=expected_found,
        expected_missing=expected_missing,
        unexpected_found=unexpected_found,
        precision=round(precision, 2),
        recall=round(recall, 2),
        notes=test_case.notes,
        prompt=build_prompt(results, test_case.question),
    )


def run_tests(n_results: int = N_RESULTS) -> List[TestResult]:
    test_results = []
    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] Testando: {tc.question}")
        embedding = embed_query(tc.question)
        results = search(embedding, n_results=n_results)
        result = evaluate(tc, results)
        test_results.append(result)

        status = "✓" if result.recall == 1.0 else "✗"
        print(f"  {status} Recall: {result.recall:.0%} | Precisão: {result.precision:.0%}")
        print(f"     Chunks esperados encontrados: {result.expected_found or 'NENHUM'}")
        print(f"     Chunks esperados ausentes: {result.expected_missing or 'nenhum'}")
        print(f"     Chunks inesperados: {result.unexpected_found or 'nenhum'}")

    return test_results


def generate_report(test_results: List[TestResult]) -> str:
    lines = [
        "# Relatório de Testes — Pipeline RAG NovaTech",
        "",
        "## Configuração do teste",
        f"- Modelo de embedding: `all-MiniLM-L6-v2`",
        f"- Vector store: ChromaDB (distância cosseno)",
        f"- Chunks recuperados por query: {N_RESULTS}",
        f"- Estratégia de chunking: header-based (## / ###) com fallback por parágrafo",
        "",
        "---",
        "",
        "## Resultados por pergunta",
        "",
    ]

    for i, result in enumerate(test_results, 1):
        avg = (result.precision + result.recall) / 2
        icon = "✅" if avg >= 0.7 else "⚠️" if avg >= 0.4 else "❌"
        tc = TEST_CASES[i - 1]

        lines += [
            f"### Teste {i}: {result.question}",
            "",
            f"**{icon} Recall:** {result.recall:.0%} | **Fonte no top-3:** {'✅' if not result.unexpected_found else '❌'}",
            "",
            f"**Observação:** {result.notes}",
            "",
            f"**Keywords esperadas encontradas:** {result.expected_found or 'NENHUMA'}",
        ]
        if result.expected_missing:
            lines += [f"**Keywords ausentes:** {result.expected_missing}"]

        lines += [
            "",
            "**Chunks recuperados:**",
            "",
            "| # | Chunk ID | Score | Fonte |",
            "|---|----------|-------|-------|",
        ]

        for j, chunk in enumerate(result.retrieved_chunks, 1):
            lines.append(
                f"| {j} | `{chunk['chunk_id']}` | {chunk['score']:.4f} | {chunk['source_doc']} |"
            )

        if result.unexpected_found:
            lines += ["", f"**⚠️ Problema:** {', '.join(result.unexpected_found)}"]

        lines += ["", "---", ""]

    # Métricas agregadas
    avg_recall = sum(r.recall for r in test_results) / len(test_results)
    avg_precision = sum(r.precision for r in test_results) / len(test_results)

    lines += [
        "## Métricas agregadas",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Recall médio | {avg_recall:.0%} |",
        f"| Precisão média | {avg_precision:.0%} |",
        f"| Testes com recall = 100% | {sum(1 for r in test_results if r.recall == 1.0)}/{len(test_results)} |",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa o pipeline RAG contra o gabarito do Anexo B")
    parser.add_argument("--output", default="relatorio-testes.md", help="Arquivo de saída do relatório")
    parser.add_argument("--n", type=int, default=N_RESULTS, help="Chunks por query")
    args = parser.parse_args()

    print("=" * 60)
    print("TESTE DO PIPELINE RAG — NovaTech")
    print("=" * 60)

    test_results = run_tests(n_results=args.n)
    report = generate_report(test_results)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✓ Relatório gerado: {args.output}")

    avg_recall = sum(r.recall for r in test_results) / len(test_results)
    avg_precision = sum(r.precision for r in test_results) / len(test_results)
    print(f"\nMétricas finais:")
    print(f"  Recall médio:    {avg_recall:.0%}")
    print(f"  Precisão média:  {avg_precision:.0%}")


if __name__ == "__main__":
    main()
