# storage/paths.py
from __future__ import annotations

from pathlib import Path
from typing import Dict


def get_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def get_data_root() -> Path:
    root = get_base_dir() / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_students_csv_path() -> Path:
    return get_data_root() / "alunos.csv"


def stage_path(ctx: Dict, stage_id: str) -> Path:
    """
    Caminho de salvamento por TURMA e GRUPO.
    - grupo_id é a chave técnica (ex: G01) -> robusto
    - grupo_nome é só rótulo (não entra no caminho)
    """
    turma = (ctx.get("turma") or "turma_default").strip()

    # Preferência: usar grupo_id (robusto)
    grupo_id = (ctx.get("grupo_id") or "").strip()
    if not grupo_id:
        # fallback (se você ainda não setou no ctx por algum motivo)
        grupo_id = (ctx.get("grupo") or "grupo_default").strip()

    folder = get_data_root() / turma / grupo_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{stage_id}.json"
