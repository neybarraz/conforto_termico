# pbl/registry.py
from pbl.schema import PBLStructure, Stage

def get_pbl_structure() -> PBLStructure:
    # MVP: registre só um estágio piloto; você vai expandir isso depois.
    return PBLStructure(
        theme="Conforto Térmico em Ambientes do Campus",
        stages=[
            Stage(phase="problema", stage_id="problema_definicao", title="Definição do Problema"),
        ],
    )
