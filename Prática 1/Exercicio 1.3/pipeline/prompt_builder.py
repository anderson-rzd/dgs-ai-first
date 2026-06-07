"""
Módulo de montagem de prompt para o LLM.

O prompt segue a estrutura:
  1. System prompt — define papel, guardrails e comportamento esperado.
  2. Contexto recuperado — chunks ordenados por score de similaridade.
  3. Pergunta do usuário.

Guardrails embutidos no system prompt:
  - Responder SOMENTE com base nos documentos fornecidos.
  - Citar a fonte (documento + seção) para cada informação.
  - Se a informação não estiver nos chunks, dizer explicitamente que não encontrou.
  - Alertar sobre contradições entre versões de documentos quando detectadas.
  - NÃO inventar SLAs, regras ou valores não presentes no contexto.
"""

from typing import List, Dict, Any

SYSTEM_PROMPT = """Você é o Assistente de Atendimento da NovaTech, uma empresa de logística.
Sua função é responder perguntas dos atendentes com base EXCLUSIVAMENTE nos documentos internos fornecidos abaixo como contexto.

REGRAS OBRIGATÓRIAS:
1. Responda SOMENTE com informações presentes nos documentos de contexto.
2. Para cada informação relevante, cite a fonte no formato: [FONTE: <nome_documento>, <seção>].
3. Se a informação solicitada NÃO estiver nos documentos, responda: "Não encontrei essa informação na documentação disponível. Consulte o responsável pela área."
4. Se houver contradição entre documentos (ex: duas versões do mesmo procedimento), aponte a contradição explicitamente e indique qual versão é mais recente.
5. NUNCA invente SLAs, multiplicadores, prazos ou regras que não estejam no contexto.
6. Documentos do FAQ são informais e podem estar desatualizados — prefira sempre documentos normativos (POL, PROC, SLA) quando houver sobreposição.

Contexto dos documentos recuperados:
---
{context}
---
"""

USER_PROMPT_TEMPLATE = "Pergunta do atendente: {question}"


def build_prompt(chunks: List[Dict[str, Any]], question: str) -> str:
    """
    Monta o prompt completo (system + contexto + pergunta) pronto para envio ao LLM.

    Args:
        chunks: Lista de chunks recuperados (output de store.search()).
        question: Pergunta do atendente.

    Returns:
        String com o prompt completo formatado.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        doc = chunk["source_doc"]
        section = chunk["section_title"]
        score = chunk["score"]
        content = chunk["content"]
        context_parts.append(
            f"[Documento {i} — {doc} / {section} (score: {score})]\n{content}"
        )

    context = "\n\n".join(context_parts)
    system = SYSTEM_PROMPT.format(context=context)
    user = USER_PROMPT_TEMPLATE.format(question=question)

    full_prompt = f"{system}\n{user}"
    return full_prompt


def format_prompt_for_display(chunks: List[Dict[str, Any]], question: str) -> str:
    """Versão formatada do prompt para exibição/debug."""
    prompt = build_prompt(chunks, question)
    separator = "=" * 60
    return f"\n{separator}\nPROMPT GERADO PELO PIPELINE\n{separator}\n{prompt}\n{separator}\n"
