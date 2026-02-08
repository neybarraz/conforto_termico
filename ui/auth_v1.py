# ui/auth.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PHASE_KEYS = {
    "Problema": "habilitado_problema",
    "Investigação": "habilitado_investigacao",
    "Solução": "habilitado_solucao",
    "Avaliação": "habilitado_avaliacao",
}


@dataclass(frozen=True)
class StudentRecord:
    nome: str
    senha: str  # MVP: texto puro
    grupo_id: str
    grupo_nome: str
    flags: Dict[str, bool]  # ex: {"habilitado_problema": True, ...}


def _bool_from_01(value: str) -> bool:
    return str(value).strip() in {"1", "true", "True", "SIM", "sim", "yes", "YES"}


def load_students_csv(csv_path: Path) -> List[StudentRecord]:
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

            flags = {
                "habilitado_problema": _bool_from_01(row.get("habilitado_problema", "0")),
                "habilitado_investigacao": _bool_from_01(row.get("habilitado_investigacao", "0")),
                "habilitado_solucao": _bool_from_01(row.get("habilitado_solucao", "0")),
                "habilitado_avaliacao": _bool_from_01(row.get("habilitado_avaliacao", "0")),
            }

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
    flag_key = PHASE_KEYS.get(phase_label)
    if not flag_key:
        return False
    return bool(student.flags.get(flag_key, False))
