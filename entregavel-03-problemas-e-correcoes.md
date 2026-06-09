# Entregável 3 — Problemas Identificados e Propostas de Correção

> Os problemas abaixo foram identificados ao observar os resultados reais do pipeline durante os 5 testes. Não são hipotéticos — cada um tem evidência de score e comportamento do LLM documentada no Entregável 2.

---

## Problema 1 — Documentos de versões diferentes competem com scores quase idênticos

### Descrição

No Teste 5 ("Como calcular o frete para 600kg com destino a Manaus?"), o pipeline retornou as seções "2. Fórmula de cálculo" do PROC-042-v1 e do PROC-042-v2 com scores praticamente idênticos:

| Chunk | Score |
|---|---|
| `PROC-042-v2 / 2. Fórmula de cálculo` | **0.5383** |
| `PROC-042-v1 / 2. Fórmula de cálculo` | **0.5366** |

Diferença: **0.0017** — praticamente indistinguíveis para o modelo de embedding. O LLM recebeu no mesmo prompt fatores de peso contraditórios:
- v1: `1.0 (500-1.000kg); 1.2 (1.001-3.000kg); 1.5 (>3.000kg)`
- v2: `1.0 (500-1.000kg); 1.15 (1.001-3.000kg); 1.4 (>3.000kg)`

### Causa raiz

Os dois documentos têm **estrutura idêntica** (mesmo título de seção, mesma fórmula, mesmo layout de tabela) — apenas os valores numéricos diferem. O embedding de similaridade semântica **não detecta diferenças de versão** porque não é treinado para isso. Ele mede proximidade de significado, e os dois textos são semanticamente quase iguais.

Adicionalmente, nenhum dos dois documentos está marcado como obsoleto no SharePoint — eles coexistem sem hierarquia. Essa é uma falha de governança documental que o pipeline herda automaticamente.

### Impacto

Se o LLM não tiver o guardrail "alertar sobre contradições", pode:
1. Usar o fator de peso da v1 (1.2) em vez da v2 (1.15) para cargas entre 1.001–3.000kg — erro de 4% no cálculo
2. Mesclar multiplicadores regionais das duas versões na mesma resposta (Norte 1.6 da v1 em vez de 1.8 da v2 — erro de 12%)

### Proposta de Correção

**Correção imediata (no pipeline):**

Adicionar campo `doc_version` e `is_current` no metadata durante a ingestão:

```python
# chunker.py — ao processar um documento, inferir versão pelo nome do arquivo
def _get_version_metadata(file_path: str) -> dict:
    name = Path(file_path).stem
    if "v2" in name or "revisado" in name:
        return {"doc_version": "v2", "is_current": True, "supersedes": "PROC-042-v1"}
    elif "PROC-042" in name:
        return {"doc_version": "v1", "is_current": False, "superseded_by": "PROC-042-v2"}
    return {"doc_version": "1.0", "is_current": True}
```

Na busca, filtrar apenas documentos vigentes:

```python
# store.py — busca apenas documentos marcados como atuais
results = search(query_embedding, where={"is_current": True})
```

**Correção estrutural (no processo de ingestão):**

Ao ingerir o PROC-042-v1, prefixar o conteúdo de cada chunk com aviso de obsolescência:

```python
if not metadata["is_current"]:
    content = f"[VERSÃO OBSOLETA — substituída por {metadata['superseded_by']}]\n\n{content}"
```

Isso muda o embedding do chunk e reduz sua similaridade para queries atuais, pois o vetor agora representa "versão obsoleta + conteúdo" ao invés de apenas o conteúdo.

**Correção definitiva (no processo documental):**

Exigir que a equipe de Operações/Compliance marque documentos obsoletos com um header padronizado antes da ingestão:

```markdown
> ⚠️ DOCUMENTO OBSOLETO — Substituído por PROC-042-v2 (nov/2023). 
> Não utilizar para novos cálculos.
```

Esse header modifica o embedding naturalmente, sem necessidade de lógica especial no pipeline.

---

## Problema 2 — FAQ informal ranqueia acima de documentos normativos para queries críticas

### Descrição

Em dois dos cinco testes, o FAQ-Atendimento ficou em rank 1 acima de documentos normativos (POL, PROC, SLA):

| Teste | FAQ em rank | Documento normativo correto em rank | Diferença de score |
|---|---|---|---|
| Teste 2 — "Posso devolver carga perigosa?" | 1 (score 0.567) | POL-001 / 3.2 em rank **6** (score 0.426) | 0.141 |
| Teste 3 — "Qual o SLA do cliente Gold?" | 1 (score 0.479) | SLA-2024 / 2. Tabela em rank **12** (score 0.260) | 0.219 |

O FAQ é descrito no próprio documento como: *"NÃO validado por Compliance ou Operações. Pode conter informações desatualizadas ou imprecisas."* No entanto, o modelo de embedding não distingue confiabilidade de fonte — apenas similaridade semântica. O FAQ usa linguagem conversacional ("a gente orienta", "o Gold tem 2h de resposta") que é semanticamente mais próxima de queries naturais do que títulos formais como "3.2. Exceções ao prazo geral" ou "2. Tabela de SLAs".

### Causa raiz

Dois fatores combinados:

1. **Mismatch de estilo:** queries de atendentes são conversacionais ("posso devolver?"); documentos normativos têm títulos formais ("Exceções ao prazo geral"). O embedding aproxima estilos similares, favorecendo o FAQ.

2. **Concentração temática:** o FAQ tem 10 chunks todos sobre atendimento. Qualquer query de atendimento ativa múltiplos chunks do FAQ simultaneamente, "inundando" os primeiros rankings.

### Impacto

- Teste 2: se o guardrail não existisse, a resposta estaria baseada no FAQ (informal) como fonte primária para uma pergunta de compliance (carga perigosa). O atendente poderia informar "já tiveram exceções" como regra, em vez de citar a proibição formal da POL-001.
- Teste 3: a resposta foi acidentalmente correta porque o FAQ tinha os valores certos. Se o FAQ estivesse desatualizado, o Claude responderia com SLAs errados sem ter como perceber — o documento normativo com os valores corretos não estava no contexto.

### Proposta de Correção

**Correção 1 — Reranking por confiabilidade (no pipeline de retrieval):**

Após o retrieval por similaridade, aplicar um segundo score que pondera a confiabilidade da fonte:

```python
RELIABILITY_WEIGHT = {
    "POL": 1.0,    # políticas normativas
    "PROC": 1.0,   # procedimentos operacionais
    "SLA": 1.0,    # documentos contratuais
    "FAQ": 0.6,    # FAQ informal
}

def rerank_by_reliability(results: list[dict]) -> list[dict]:
    for r in results:
        doc_type = r["source_doc"].split("-")[0]  # POL, PROC, SLA, FAQ
        weight = RELIABILITY_WEIGHT.get(doc_type, 0.8)
        r["adjusted_score"] = r["score"] * weight
    return sorted(results, key=lambda x: x["adjusted_score"], reverse=True)
```

Efeito no Teste 2: FAQ-Item 3 (score 0.567 × 0.6 = **0.340**) ficaria abaixo de POL-001-3.2 (score 0.426 × 1.0 = **0.426**) — invertendo a ordem corretamente.

**Correção 2 — Metadata de confiabilidade no prompt:**

Incluir o campo `doc_reliability` no contexto enviado ao LLM, para que ele possa priorizar:

```python
# prompt_builder.py
context_parts.append(
    f"[Documento {i} — {doc} / {section} | "
    f"tipo: {reliability} | score: {score}]\n{content}"
)
```

**Correção 3 — Instrução explícita aprimorada no system prompt:**

O guardrail atual ("FAQ é informal — prefira documentos normativos") funciona mas depende do LLM interpretar corretamente. Uma instrução mais explícita seria:

```
Hierarquia de fontes (em ordem decrescente de autoridade):
1. POL-XXX (Políticas): uso obrigatório para regras normativas
2. PROC-XXX (Procedimentos): uso obrigatório para cálculos e processos
3. SLA-XXXX (SLAs): uso obrigatório para compromissos com clientes
4. FAQ-Atendimento: use APENAS como contexto complementar ou para orientações práticas
   NUNCA como fonte principal para regras, valores ou prazos formais.
Quando fontes de hierarquia diferente contradizem, use sempre a de maior hierarquia.
```

---

## Problema Bônus — Mapeamento geográfico implícito não resolvido

### Descrição

No Teste 5, a query "Como calcular o frete para **600kg com destino a Manaus**?" deveria recuperar a tabela de multiplicadores regionais com "Norte = 1.8". No entanto, a tabela usa "Norte" como chave, e "Manaus" não aparece em nenhum documento — a relação "Manaus → Norte" é um conhecimento implícito que o pipeline não tem.

Resultado: a seção "2.1. Multiplicadores regionais" ficou fora dos **top-20 resultados** para essa query. O Claude respondeu corretamente dizendo que não tinha a informação do multiplicador, mas o atendente recebeu uma resposta incompleta.

### Proposta de Correção

**Correção 1 — Enriquecimento de conteúdo na ingestão:**

Adicionar um arquivo de mapeamento geográfico à base de documentos:

```markdown
# Mapeamento de Cidades por Região (NovaTech)
## Região Norte
Manaus, Belém, Porto Velho, Macapá, Rio Branco, Boa Vista, Palmas

## Região Nordeste
Salvador, Recife, Fortaleza, São Luís, Natal, Maceió, Aracaju, Teresina, João Pessoa

## Região Sudeste
São Paulo, Rio de Janeiro, Belo Horizonte, Vitória, Campinas, Guarulhos

## Região Sul
Curitiba, Porto Alegre, Florianópolis, Londrina, Caxias do Sul

## Região Centro-Oeste
Brasília, Goiânia, Campo Grande, Cuiabá
```

Com esse documento ingerido, a query "frete para Manaus" recuperaria o chunk "Região Norte" → que por sua vez alimentaria o retrieval da tabela de multiplicadores.

**Correção 2 — Query expansion antes do embedding:**

Antes de gerar o embedding da query, expandir termos geográficos:

```python
GEO_MAP = {
    "manaus": "região norte",
    "belém": "região norte",
    "salvador": "região nordeste",
    "são paulo": "região sudeste",
    # ...
}

def expand_query(query: str) -> str:
    for city, region in GEO_MAP.items():
        if city in query.lower():
            query = f"{query} ({region})"
    return query

# Uso:
expanded = expand_query("Como calcular o frete para 600kg com destino a Manaus?")
# → "Como calcular o frete para 600kg com destino a Manaus? (região norte)"
embedding = embed_query(expanded)
```

---

## Aprendizado Geral: RAG é Engenharia de Dados

Os três problemas acima demonstram que **o pipeline RAG não é apenas uma chamada de API** — é um sistema de engenharia de dados com decisões que impactam diretamente a qualidade das respostas:

| Decisão de Engenharia | Impacto nos testes |
|---|---|
| Qual modelo de embedding usar | Recall de 0% (inglês) → 80% (multilingual PT-BR) |
| Como gerenciar versões de documentos | Contradição de multiplicadores no mesmo prompt |
| Como rankear fontes de confiabilidade diferente | FAQ informal acima de política normativa |
| Como representar conhecimento implícito (cidade → região) | Falha total para queries geográficas |
| Estratégia de chunking (tokens fixos vs. por seção) | Preservação ou destruição de tabelas e listas |

Cada uma dessas decisões é independente de qual LLM é usado. Trocar o Claude por GPT-4 ou Gemini não resolveria nenhum dos problemas acima — todos são problemas de pipeline, não de geração.
