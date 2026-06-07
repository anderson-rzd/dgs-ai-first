# Entregável 1 — Código do Pipeline RAG

## Stack utilizada

| Componente | Tecnologia | Motivo |
|---|---|---|
| Linguagem | Python 3.12 | Exigência do exercício |
| Vector store | ChromaDB 0.4+ | Open-source, roda 100% local, persistência em disco sem servidor |
| Modelo de embedding | `paraphrase-multilingual-MiniLM-L12-v2` | Suporte nativo a 50+ idiomas incluindo PT-BR — necessário pois `all-MiniLM-L6-v2` (sugestão original, inglês) gerou recall ~0% nas queries em português |
| LLM para geração | Claude (chat manual) | Conforme instrução do exercício |
| Orquestração | Código manual (sem LangChain) | Controle total do pipeline para fins didáticos |

---

## Arquivos do pipeline

```
pipeline/
├── chunker.py          # Estratégia de chunking por seção Markdown
├── embedder.py         # Geração de embeddings (sentence-transformers)
├── store.py            # Operações ChromaDB (store/search)
└── prompt_builder.py   # Montagem do prompt com guardrails

ingest.py               # Etapa 1: lê documentos → chunks → embeddings → ChromaDB
query.py                # Etapa 2: recebe pergunta → embedding → busca → retorna chunks
test_pipeline.py        # Testes automatizados contra gabarito do Anexo B
```

---

## Etapa 1 — Ingestão

**Arquivo:** `ingest.py`

Fluxo executado por `python ingest.py --reset`:

```
Documentos .md
      │
      ▼
  chunker.py ──► divide em chunks por seção de Markdown
      │
      ▼
  embedder.py ──► gera embedding de 384 dimensões por chunk
      │            (modelo: paraphrase-multilingual-MiniLM-L12-v2)
      ▼
  store.py ──► persiste no ChromaDB com metadata
                (source_doc, section_title, chunk_id)
```

**Resultado:** 35 chunks armazenados

| Documento | Chunks |
|---|---|
| POL-001-politica-devolucao | 9 |
| PROC-042-frete-especial-v1 | 5 |
| PROC-042-v2-frete-especial-revisado | 6 |
| SLA-2024-tabela-sla-clientes | 5 |
| FAQ-atendimento | 10 |
| **Total** | **35** |

---

## Etapa 2 — Busca

**Arquivo:** `query.py` + `pipeline/store.py`

```python
# Núcleo da função de busca (store.py)
def search(query_embedding, n_results=5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    # Converte distância cosseno → score de similaridade (0-1)
    similarity = 1.0 - distance
    return [{ chunk_id, content, source_doc, section_title, score }]
```

A busca usa **similaridade cosseno** (configurada no ChromaDB via `"hnsw:space": "cosine"`), que é a métrica padrão para embeddings de texto — invariante à magnitude do vetor, mede apenas direção semântica.

---

## Etapa 3 — Montagem do Prompt

**Arquivo:** `pipeline/prompt_builder.py`

O prompt enviado ao Claude tem 3 camadas:

```
┌─────────────────────────────────────────────────────┐
│ SYSTEM PROMPT                                       │
│  • Define papel: "Assistente de Atendimento NovaTech"│
│  • Guardrails:                                      │
│    1. Responda SOMENTE com base nos documentos      │
│    2. Cite a fonte [FONTE: doc, seção]              │
│    3. Se não encontrar, diga explicitamente         │
│    4. Se houver contradição, aponte                 │
│    5. Nunca invente SLAs/multiplicadores/regras     │
│    6. FAQ é informal — prefira POL/PROC/SLA         │
├─────────────────────────────────────────────────────┤
│ CONTEXTO RECUPERADO                                 │
│  [Documento 1 — fonte / seção (score: 0.xx)]        │
│  conteúdo do chunk...                               │
│                                                     │
│  [Documento 2 — fonte / seção (score: 0.xx)]        │
│  ...                                                │
├─────────────────────────────────────────────────────┤
│ PERGUNTA DO ATENDENTE                               │
│  "Qual o prazo de devolução?"                       │
└─────────────────────────────────────────────────────┘
```

---

## Estratégia de Chunking — Justificativa

**Estratégia adotada:** chunking por seção de documento (header-based), dividindo no nível `##` e `###` do Markdown.

**Por que NÃO usar chunking fixo por tokens (ex: 512 tokens)?**

Os documentos da NovaTech têm estrutura bem definida: cada seção do POL-001, PROC-042 e SLA-2024 cobre exatamente um tópico (ex: "3.1. Prazo geral", "2.1. Multiplicadores regionais"). Dividir por token fixo quebraria essas unidades no meio, gerando três problemas concretos:

1. **Tabelas partidas ao meio:** A tabela de multiplicadores regionais (6 linhas) caberia inteira em ~200 tokens. Com chunking de 512 tokens, ficaria embutida em um chunk gigante com conteúdo de outras seções, diluindo o sinal semântico.

2. **Listas de exceções cortadas:** A seção 3.2 da POL-001 lista 3 categorias de carga não elegível. Com chunking fixo, a terceira categoria poderia ir para o chunk seguinte, tornando o chunk incompleto.

3. **Embedding dilui o sinal:** Um chunk que contém "prazo de devolução" + "fórmula de frete" + "multiplicadores" gera um embedding que representa *tudo isso junto* e não representa *nenhum desses tópicos* com precisão.

**Fallback para seções longas:** seções com mais de 800 caracteres são subdivididas por parágrafo, preservando o contexto da seção no metadata.

**Limitação identificada:** seções que são apenas subsections (`###`) ficam separadas de seu contexto pai (`##`). Exemplo: "2.1. Multiplicadores regionais" é um chunk isolado sem o cabeçalho "2. Fórmula de cálculo", o que reduz sua recuperabilidade para queries que usam os termos do `##` pai. Solução: contextual chunking (incluir o título do pai no conteúdo de cada filho) — ver Entregável 3.

---

## Como executar

```bash
# Pré-requisito: python3 + venv criado com .venv/bin/activate
cd "Plano JK da IA/DGS/dgs-ai-first/Exercicio 1.3"

# Instalar dependências (primeira vez)
.venv/bin/pip install -r requirements.txt

# Ingestão dos 5 documentos
.venv/bin/python ingest.py --reset

# Busca interativa com prompt gerado
.venv/bin/python query.py "Qual o prazo de devolução?" --show-prompt

# Rodar os 5 testes do gabarito
.venv/bin/python test_pipeline.py
```
