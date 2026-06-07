"""
Módulo de chunking semântico baseado em estrutura Markdown.

Estratégia escolhida: chunking por seção de documento (header-based).
Justificativa:
- Os documentos da NovaTech seguem estrutura de seções bem definidas (POL, PROC, SLA, FAQ).
- Uma seção = um tópico = um chunk garante coerência semântica.
- Evita cortar tabelas de multiplicadores ou listas de regras no meio.
- Chunking fixo por tokens (ex: 512 tokens) seria inadequado aqui porque quebraria
  tabelas de SLA, listas de exceções e referências cruzadas entre itens da mesma seção.
- Fallback: seções muito longas (>800 chars) são subdivididas por parágrafo para evitar
  chunks que diluem o sinal semântico no embedding.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Chunk:
    chunk_id: str
    source_doc: str
    section_title: str
    content: str
    metadata: dict = field(default_factory=dict)


MAX_CHUNK_CHARS = 800


def _split_by_paragraphs(text: str, source_doc: str, section_title: str, base_id: str) -> List[Chunk]:
    """Subdivide uma seção longa em parágrafos, preservando o contexto da seção."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks = []
    buffer = ""
    part = 0
    for para in paragraphs:
        if len(buffer) + len(para) > MAX_CHUNK_CHARS and buffer:
            chunk_id = f"{base_id}-p{part}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                source_doc=source_doc,
                section_title=section_title,
                content=buffer.strip(),
                metadata={"split_reason": "max_chars_exceeded"},
            ))
            buffer = para
            part += 1
        else:
            buffer = f"{buffer}\n\n{para}" if buffer else para
    if buffer.strip():
        chunk_id = f"{base_id}-p{part}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            source_doc=source_doc,
            section_title=section_title,
            content=buffer.strip(),
            metadata={"split_reason": "max_chars_exceeded"},
        ))
    return chunks


def chunk_markdown(file_path: str) -> List[Chunk]:
    """
    Lê um arquivo Markdown e divide em chunks por seção (## e ###).
    Cada header de nível 2/3 inicia um novo chunk. Seções longas
    são subdivididas por parágrafo.
    """
    path = Path(file_path)
    source_doc = path.stem
    text = path.read_text(encoding="utf-8")

    # Padrão: captura headers ## e ### e seu conteúdo até o próximo header
    pattern = re.compile(r"(#{2,3})\s+(.+?)(?=\n#{2,3}\s|\Z)", re.DOTALL)
    matches = list(pattern.finditer(text))

    # Se não há headers, trata o documento inteiro como um único chunk
    if not matches:
        return [Chunk(
            chunk_id=f"{source_doc}-full",
            source_doc=source_doc,
            section_title="Documento completo",
            content=text.strip(),
        )]

    chunks = []
    seen_titles: dict[str, int] = {}

    for match in matches:
        level = len(match.group(1))
        # group(0) = full match including "## Title\nbody"
        # group(2) = everything after "## " — title + body — extract only first line
        full_text = match.group(0).strip()
        section_title = full_text.split('\n')[0].lstrip('#').strip()
        content = full_text

        # Gera ID único mesmo quando o título se repete entre documentos
        title_key = f"{source_doc}::{section_title}"
        count = seen_titles.get(title_key, 0)
        seen_titles[title_key] = count + 1
        safe_title = re.sub(r"[^\w]", "_", section_title)[:40]
        base_id = f"{source_doc}-{safe_title}" + (f"-{count}" if count else "")

        if len(content) > MAX_CHUNK_CHARS:
            sub_chunks = _split_by_paragraphs(content, source_doc, section_title, base_id)
            chunks.extend(sub_chunks)
        else:
            chunks.append(Chunk(
                chunk_id=base_id,
                source_doc=source_doc,
                section_title=section_title,
                content=content,
                metadata={"header_level": level},
            ))

    return chunks
