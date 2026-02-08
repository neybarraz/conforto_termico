# ui/auth.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# FASES (abas)
# =============================================================================
PHASE_KEYS: Dict[str, str] = {
    "Problema": "habilitado_problema",
    "Investigação": "habilitado_investigacao",
    "Solução": "habilitado_solucao",
    "Avaliação": "habilitado_avaliacao",
}

# =============================================================================
# STAGES (blocos dentro de uma fase)
# Ex.: Avaliação tem "avaliacao_prova" e "avaliacao_recuperativa"
# =============================================================================
STAGE_KEYS: Dict[str, str] = {
    # Avaliação
    "avaliacao_prova": "habilitado_prova",                 # opcional (fallback para habilitado_avaliacao)
    "avaliacao_recuperativa": "habilitado_recuperativa",   # novo (controle fino)
}


@dataclass(frozen=True)
class StudentRecord:
    nome: str
    senha: str  # MVP: texto puro
    grupo_id: str
    grupo_nome: str
    flags: Dict[str, bool]  # ex: {"habilitado_problema": True, ...}


def _bool_from_01(value: object) -> bool:
    """
    Converte 0/1 e variações comuns em bool.
    Aceita strings, ints, None.
    """
    if value is None:
        return False
    s = str(value).strip()
    return s in {"1", "true", "True", "SIM", "sim", "yes", "YES"}


def load_students_csv(csv_path: Path) -> List[StudentRecord]:
    """
    Lê data/alunos.csv e monta StudentRecord.

    Colunas mínimas:
      nome, senha, grupo_id, grupo_nome

    Flags por fase:
      habilitado_problema, habilitado_investigacao, habilitado_solucao, habilitado_avaliacao

    Flags por stage (novas / opcionais):
      habilitado_recuperativa (recomendado)
      habilitado_prova (opcional; se ausente, usa habilitado_avaliacao)
    """
    if not csv_path.exists():
        return []

    records: List[StudentRecord] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nome = (row.get("nome") or "").strip()
            senha = (row.get("senha") or "").strip()

            grupo_id = (row.get("grupo_id") or "").strip()
            grupo_nome = (row.get("grupo_nome") or "").strip()

            # Mínimos obrigatórios
            if not nome or not senha or not grupo_id or not grupo_nome:
                continue

            # Flags por fase (sempre existem no seu CSV atual)
            flags: Dict[str, bool] = {
                "habilitado_problema": _bool_from_01(row.get("habilitado_problema", "0")),
                "habilitado_investigacao": _bool_from_01(row.get("habilitado_investigacao", "0")),
                "habilitado_solucao": _bool_from_01(row.get("habilitado_solucao", "0")),
                "habilitado_avaliacao": _bool_from_01(row.get("habilitado_avaliacao", "0")),
            }

            # Flags por stage (novas). Fallback seguro para não quebrar CSV antigo:
            # - recuperativa: padrão = 0 (ninguém autorizado por padrão)
            # - prova: padrão = igual à habilitado_avaliacao (se não existir coluna)
            flags["habilitado_recuperativa"] = _bool_from_01(row.get("habilitado_recuperativa", "0"))

            if "habilitado_prova" in (reader.fieldnames or []):
                flags["habilitado_prova"] = _bool_from_01(row.get("habilitado_prova", "0"))
            else:
                flags["habilitado_prova"] = bool(flags.get("habilitado_avaliacao", False))

            records.append(
                StudentRecord(
                    nome=nome,
                    senha=senha,
                    grupo_id=grupo_id,
                    grupo_nome=grupo_nome,
                    flags=flags,
                )
            )

    records.sort(key=lambda r: r.nome.lower())
    return records


def authenticate(
    records: List[StudentRecord],
    nome: str,
    senha_plain: str,
) -> Tuple[bool, Optional[StudentRecord]]:
    """
    MVP: compara a senha digitada com o valor exato no CSV (texto puro).
    """
    nome = nome.strip()
    senha_plain = senha_plain.strip()
    if not nome or not senha_plain:
        return False, None

    for r in records:
        if r.nome == nome and r.senha == senha_plain:
            return True, r

    return False, None


def is_enabled_for_phase(student: StudentRecord, phase_label: str) -> bool:
    """
    Gate por aba/fase.
    """
    flag_key = PHASE_KEYS.get(phase_label)
    if not flag_key:
        return False
    return bool(student.flags.get(flag_key, False))


def is_enabled_for_stage(student: StudentRecord, stage_id: str) -> bool:
    """
    Gate por bloco/etapa (mais granular).
    Ex.: "avaliacao_recuperativa" depende de habilitado_recuperativa.

    Regras:
    - Se stage_id estiver mapeado em STAGE_KEYS, usa aquele flag.
    - Se não estiver mapeado, retorna False (seguro).
    """
    flag_key = STAGE_KEYS.get(stage_id)
    if not flag_key:
        return False
    return bool(student.flags.get(flag_key, False))
