# Relatório de Testes — Pipeline RAG NovaTech

## Configuração do teste
- Modelo de embedding: `all-MiniLM-L6-v2`
- Vector store: ChromaDB (distância cosseno)
- Chunks recuperados por query: 8
- Estratégia de chunking: header-based (## / ###) com fallback por parágrafo

---

## Resultados por pergunta

### Teste 1: Qual o prazo de devolução?

**✅ Recall:** 100% | **Fonte no top-3:** ✅

**Observação:** Chunk central: seção 3.1 da POL-001 (7 dias úteis).

**Keywords esperadas encontradas:** ['7 (sete) dias úteis', 'data de recebimento']

**Chunks recuperados:**

| # | Chunk ID | Score | Fonte |
|---|----------|-------|-------|
| 1 | `PROC-042-v2-frete-especial-revisado-3__Prazo_de_entrega_para_frete_especial` | 0.5463 | PROC-042-v2-frete-especial-revisado |
| 2 | `POL-001-politica-devolucao-3_1__Prazo_geral` | 0.5442 | POL-001-politica-devolucao |
| 3 | `PROC-042-frete-especial-v1-3__Prazo_de_entrega_para_frete_especial` | 0.5249 | PROC-042-frete-especial-v1 |
| 4 | `SLA-2024-tabela-sla-clientes-5__Medição_e_reportes` | 0.4636 | SLA-2024-tabela-sla-clientes |
| 5 | `POL-001-politica-devolucao-3_5__Custos_de_devolução` | 0.4605 | POL-001-politica-devolucao |
| 6 | `POL-001-politica-devolucao-3_3__Procedimento_de_devolução` | 0.4406 | POL-001-politica-devolucao |
| 7 | `POL-001-politica-devolucao-3__Regras_de_Devolução` | 0.4253 | POL-001-politica-devolucao |
| 8 | `FAQ-atendimento-Item_38____Cliente_quer_saber_a_política` | 0.4176 | FAQ-atendimento |

---

### Teste 2: Posso devolver carga perigosa?

**✅ Recall:** 100% | **Fonte no top-3:** ❌

**Observação:** Deve recuperar a seção de exceções da POL-001 que lista cargas perigosas.

**Keywords esperadas encontradas:** ['não são elegíveis', 'cargas perigosas', 'Gestão de Riscos']

**Chunks recuperados:**

| # | Chunk ID | Score | Fonte |
|---|----------|-------|-------|
| 1 | `FAQ-atendimento-Item_3____Cliente_perguntou_se_pode_devo` | 0.5672 | FAQ-atendimento |
| 2 | `FAQ-atendimento-Item_38____Cliente_quer_saber_a_política` | 0.5378 | FAQ-atendimento |
| 3 | `PROC-042-v2-frete-especial-revisado-4__Condições_especiais` | 0.4644 | PROC-042-v2-frete-especial-revisado |
| 4 | `POL-001-politica-devolucao-3_5__Custos_de_devolução` | 0.4485 | POL-001-politica-devolucao |
| 5 | `PROC-042-frete-especial-v1-4__Condições_especiais` | 0.4297 | PROC-042-frete-especial-v1 |
| 6 | `POL-001-politica-devolucao-3_2__Exceções_ao_prazo_geral-p0` | 0.4255 | POL-001-politica-devolucao |
| 7 | `FAQ-atendimento-Item_22____Cliente_quer_saber_sobre_segu` | 0.4121 | FAQ-atendimento |
| 8 | `SLA-2024-tabela-sla-clientes-3__Definição_de_incidente_crítico` | 0.3718 | SLA-2024-tabela-sla-clientes |

**⚠️ Problema:** fonte esperada 'POL-001-politica-devolucao' não está no top-3

---

### Teste 3: Qual o SLA do cliente Gold?

**⚠️ Recall:** 33% | **Fonte no top-3:** ✅

**Observação:** Tabela de SLA seção 2. Gold: 2h resposta, 24h resolução.

**Keywords esperadas encontradas:** ['Gold']
**Keywords ausentes:** ['2h úteis', '24h úteis']

**Chunks recuperados:**

| # | Chunk ID | Score | Fonte |
|---|----------|-------|-------|
| 1 | `FAQ-atendimento-Item_41____Qual_a_diferença_entre_SLA_de` | 0.4787 | FAQ-atendimento |
| 2 | `FAQ-atendimento-Item_15____Cliente_diz_que_é_Platinum__E` | 0.4663 | FAQ-atendimento |
| 3 | `SLA-2024-tabela-sla-clientes-5__Medição_e_reportes` | 0.4395 | SLA-2024-tabela-sla-clientes |
| 4 | `SLA-2024-tabela-sla-clientes-4__Penalidades_por_descumprimento` | 0.3812 | SLA-2024-tabela-sla-clientes |
| 5 | `FAQ-atendimento-Item_27____O_tracking_mostra__em_trânsit` | 0.3369 | FAQ-atendimento |
| 6 | `SLA-2024-tabela-sla-clientes-1__Classificação_de_clientes` | 0.3256 | SLA-2024-tabela-sla-clientes |
| 7 | `FAQ-atendimento-Item_45____O_cliente_quer_desconto_no_fr` | 0.3230 | FAQ-atendimento |
| 8 | `POL-001-politica-devolucao-2__Escopo` | 0.3046 | POL-001-politica-devolucao |

---

### Teste 4: Qual o SLA do cliente Platinum?

**✅ Recall:** 100% | **Fonte no top-3:** ✅

**Observação:** Deve recuperar a classificação de clientes que diz que Platinum NÃO existe.

**Keywords esperadas encontradas:** ['Não existem outros tiers', 'Gold, Silver e Standard']

**Chunks recuperados:**

| # | Chunk ID | Score | Fonte |
|---|----------|-------|-------|
| 1 | `FAQ-atendimento-Item_15____Cliente_diz_que_é_Platinum__E` | 0.6751 | FAQ-atendimento |
| 2 | `FAQ-atendimento-Item_41____Qual_a_diferença_entre_SLA_de` | 0.3705 | FAQ-atendimento |
| 3 | `SLA-2024-tabela-sla-clientes-1__Classificação_de_clientes` | 0.3656 | SLA-2024-tabela-sla-clientes |
| 4 | `SLA-2024-tabela-sla-clientes-5__Medição_e_reportes` | 0.3515 | SLA-2024-tabela-sla-clientes |
| 5 | `POL-001-politica-devolucao-2__Escopo` | 0.3482 | POL-001-politica-devolucao |
| 6 | `PROC-042-v2-frete-especial-revisado-4__Condições_especiais` | 0.3256 | PROC-042-v2-frete-especial-revisado |
| 7 | `FAQ-atendimento-Item_8____Como_funciona_o_frete_especial` | 0.3175 | FAQ-atendimento |
| 8 | `FAQ-atendimento-Item_22____Cliente_quer_saber_sobre_segu` | 0.3158 | FAQ-atendimento |

---

### Teste 5: Como calcular o frete para 600kg com destino a Manaus?

**✅ Recall:** 67% | **Fonte no top-3:** ✅

**Observação:** Deve usar versão v2 (mais recente). Risco: recuperar PROC-042 v1 junto (contradição).

**Keywords esperadas encontradas:** ['Norte', 'Multiplicador regional']
**Keywords ausentes:** ['1.8']

**Chunks recuperados:**

| # | Chunk ID | Score | Fonte |
|---|----------|-------|-------|
| 1 | `PROC-042-v2-frete-especial-revisado-2__Fórmula_de_cálculo` | 0.5383 | PROC-042-v2-frete-especial-revisado |
| 2 | `PROC-042-frete-especial-v1-2__Fórmula_de_cálculo` | 0.5366 | PROC-042-frete-especial-v1 |
| 3 | `PROC-042-frete-especial-v1-1__Objetivo` | 0.4910 | PROC-042-frete-especial-v1 |
| 4 | `PROC-042-v2-frete-especial-revisado-4__Condições_especiais` | 0.4002 | PROC-042-v2-frete-especial-revisado |
| 5 | `PROC-042-v2-frete-especial-revisado-1__Objetivo` | 0.3897 | PROC-042-v2-frete-especial-revisado |
| 6 | `PROC-042-frete-especial-v1-4__Condições_especiais` | 0.3810 | PROC-042-frete-especial-v1 |
| 7 | `FAQ-atendimento-Item_27____O_tracking_mostra__em_trânsit` | 0.3210 | FAQ-atendimento |
| 8 | `PROC-042-v2-frete-especial-revisado-3__Prazo_de_entrega_para_frete_especial` | 0.3204 | PROC-042-v2-frete-especial-revisado |

---

## Métricas agregadas

| Métrica | Valor |
|---------|-------|
| Recall médio | 80% |
| Precisão média | 90% |
| Testes com recall = 100% | 3/5 |
