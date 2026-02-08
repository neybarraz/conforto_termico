# blocks/problema/conteudos_essenciais.py
from __future__ import annotations

from typing import Dict, List
from datetime import datetime
from pathlib import Path
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_conteudos_essenciais"

CONTEUDOS = [
    "Temperatura e escalas térmicas",
    "Teoria cinética dos gases",
    "Calor e formas de transferência",
    "Primeira Lei da Termodinâmica",
    "Noções de convecção natural e forçada",
    "Conceito de equilíbrio térmico",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_filename(name: str) -> str:
    """
    Gera um nome de arquivo estável e seguro a partir do nome do aluno.
    - remove espaços extras
    - troca espaços por underscore
    - remove caracteres não seguros
    """
    name = (name or "Aluno").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_\-]", "", name)
    return name or "Aluno"


def _problema_path(aluno: str) -> Path:
    # salva em data/problema/problema_<aluno>.json
    base = Path("data") / "problema"
    base.mkdir(parents=True, exist_ok=True)
    fname = f"problema_{_safe_filename(aluno)}.json"
    return base / fname


def mostrar_figura(caminho: str, legenda: str):
    st.image(
        caminho,
        caption=legenda,
        use_container_width=True,
    )


_EQ_BLOCK = re.compile(r"^\s*\$\$(.*?)\$\$\s*$", re.DOTALL)


def texto(conteudo: str, indent_px: int = 40, margin_bottom_px: int = 15) -> None:
    """
    Renderiza texto justificado por parágrafos e permite blocos LaTeX no formato:

    $$
    ...latex...
    $$

    Regras:
    - Parágrafo = separado por uma ou mais linhas em branco (mesmo com espaços).
    - Dentro de parágrafos, quebras de linha simples viram espaço.
    - HTML inline (<b>...</b>) é preservado.
    - Fórmulas inline tipo $\Delta T$ permanecem no texto (markdown).
    """
    if not conteudo:
        return

    s = conteudo.strip().replace("\r\n", "\n").replace("\r", "\n")
    blocos = [b for b in re.split(r"\n\s*\n+", s) if b.strip()]

    for bloco in blocos:
        bloco = bloco.strip()

        m = _EQ_BLOCK.match(bloco)
        if m:
            expr = m.group(1).strip()
            st.latex(expr)
            continue

        texto_limpo = re.sub(r"\s*\n\s*", " ", bloco).strip()

        st.markdown(
            f"""
            <p style="
                text-align: justify;
                text-indent: {indent_px}px;
                margin-bottom: {margin_bottom_px}px;
            ">{texto_limpo}</p>
            """,
            unsafe_allow_html=True,
        )


def _render_lista(conteudos: List[str]) -> None:
    st.markdown(
        "<div style='text-align: justify;'><ul>"
        + "".join([f"<li>{c}</li>" for c in conteudos])
        + "</ul></div>",
        unsafe_allow_html=True,
    )


def _load_root_container(path: Path, aluno: str, grupo_id: str, grupo_nome: str) -> Dict:
    root = load_json(path) or {}

    root.setdefault("aluno", aluno)
    if grupo_id:
        root.setdefault("grupo_id", grupo_id)
    if grupo_nome:
        root.setdefault("grupo_nome", grupo_nome)

    root.setdefault("stages", {})
    if not isinstance(root.get("stages"), dict):
        root["stages"] = {}

    return root


def _get_stage_data(root: Dict, stage_id: str) -> Dict:
    stages = root.get("stages", {})
    if not isinstance(stages, dict):
        stages = {}
        root["stages"] = stages

    data = stages.get(stage_id, {})
    if not isinstance(data, dict):
        data = {}
        stages[stage_id] = data

    return data


def _update_stage(root: Dict, stage_id: str, stage_payload: Dict) -> None:
    root.setdefault("stages", {})
    if not isinstance(root["stages"], dict):
        root["stages"] = {}
    root["stages"][stage_id] = stage_payload
    root["updated_at"] = _now_iso()


# ----------------------------
# caixas "o que entendi" + salvar por tema (no container do aluno)
# ----------------------------
def _caixa_entendimento(
    tema_key: str,
    titulo_tema: str,
    valor_inicial: str,
    path: Path,
    aluno: str,
    grupo_id: str,
    grupo_nome: str,
) -> str:
    st.markdown(
        f"""
        <div style="margin-bottom: 4px;">
            <strong>O que você entendeu deste tema: {titulo_tema}?</strong>
        </div>

        <div style="
            background-color: #1f2937;
            border-left: 4px solid #3b82f6;
            padding: 10px 12px;
            margin-top: 4px;
            margin-bottom: 10px;
            font-size: 0.95rem;
            color: #e5e7eb;
        ">
            <strong>Orientações:</strong>
            <ul style="margin-top: 6px;">
                <li>Escreva com suas palavras (3–8 linhas).</li>
                <li>Diga o conceito principal e como ele ajuda a interpretar o problema.</li>
                <li>Se tiver dúvida, registre a dúvida.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    txt = st.text_area(
        "Registro individual (será salvo):",
        value=valor_inicial or "",
        height=140,
        key=f"{STAGE_ID}_ent_{tema_key}",
    )

    colb1, colb2 = st.columns([1, 3])
    with colb1:
        if st.button("Salvar este tema", key=f"{STAGE_ID}_btn_salvar_{tema_key}"):
            # carrega container do aluno
            root = _load_root_container(path, aluno, grupo_id, grupo_nome)

            # pega o stage atual (sem destruir outros campos do stage)
            stage_data = _get_stage_data(root, STAGE_ID)

            ents = stage_data.get("entendimentos", {})
            if not isinstance(ents, dict):
                ents = {}

            ents[tema_key] = (txt or "").strip()
            stage_data["entendimentos"] = ents

            # metadados do stage
            stage_data["stage_id"] = STAGE_ID
            stage_data["saved_at"] = _now_iso()
            stage_data["aluno"] = aluno
            stage_data["grupo_id"] = grupo_id
            stage_data["grupo_nome"] = grupo_nome

            _update_stage(root, STAGE_ID, stage_data)
            save_json(path, root)

            st.success("Salvo.")

    st.markdown("---")
    return txt


def render(ctx: Dict) -> None:
    # Contexto
    aluno = (ctx.get("aluno") or "Aluno").strip()
    grupo_id = (ctx.get("grupo_id") or "").strip()
    grupo_nome = (ctx.get("grupo_nome") or "").strip()

    if grupo_id and grupo_nome:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id} ({grupo_nome})")
    elif grupo_id:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id}")

    # arquivo do aluno em data/problema
    path = _problema_path(aluno)

    # container completo + stage atual
    root = _load_root_container(path, aluno, grupo_id, grupo_nome)
    stage_data = _get_stage_data(root, STAGE_ID)

    # entendimentos salvos deste stage
    entendimentos_salvos = stage_data.get("entendimentos", {})
    if not isinstance(entendimentos_salvos, dict):
        entendimentos_salvos = {}

    # acumula respostas nesta execução (para o salvar final)
    entendimentos: Dict[str, str] = {}

    # -------------------------------------------------------------------------
    # CONTEÚDOS ESSENCIAIS — Conforto Térmico
    # -------------------------------------------------------------------------

    # =========================
    # 1) TEMPERATURA E ESCALAS
    # =========================
    st.markdown(
        """
        <div style="text-align: justify;">
        <h3>Temperatura e Escalas Térmicas</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=8fo8_m-qP9M")

    texto(r"""
    <b>Temperatura</b> é uma grandeza física que caracteriza o estado térmico de um sistema e
    está associada ao nível de agitação microscópica de suas partículas. Em termos físicos,
    quanto maior a <b>energia cinética média</b> das moléculas, maior é a temperatura do sistema.
    """)

    texto(r"""
    No problema de conforto térmico, a temperatura do ar é uma variável ambiental central,
    pois influencia a intensidade e o sentido das trocas de energia entre o corpo humano e
    o ambiente. Assim, medir temperatura não é apenas registrar um número: é obter um
    indicador físico direto da condição térmica que poderá favorecer conforto ou induzir
    desconforto, dependendo das demais variáveis (umidade, movimento do ar e radiação).
    """)

    texto(r"""
    A interpretação correta das medições exige atenção às <b>escalas térmicas</b>. As mais usadas
    são Celsius (°C), Kelvin (K) e Fahrenheit (°F). A escala Celsius é comum em medições ambientais;
    a escala Kelvin é a escala <b>absoluta</b> e é a referência natural para relações termodinâmicas;
    a escala Fahrenheit pode aparecer em índices e referências específicas.
    """)

    st.video("https://www.youtube.com/watch?v=02HqOFprQoc")

    texto(r"""
    No contexto do PBL, um erro de escala (por exemplo, usar °F como se fosse °C) compromete
    todo o diagnóstico: índices térmicos, conclusões sobre desconforto e decisões práticas
    podem ficar incorretas. Portanto, a primeira verificação física do dado é sempre: 
    <b>qual escala está sendo usada e o que ela significa</b>.
    """)

    mostrar_figura(
        "assets/temperatura_escalas.jpeg",
        "Escalas de temperatura: Celsius (°C), Kelvin (K) e Fahrenheit (°F)",
    )

    texto(r"""
    A relação entre Celsius (°C), Fahrenheit (°F) e Kelvin (K) é uma transformação linear e pode
    ser expressa por uma equação comparativa. As escalas diferem por um deslocamento de origem
    e por um fator de escala, preservando proporcionalidade entre variações de temperatura.

    $$\frac{T}{100} = \frac{F - 32}{180} = \frac{K - 273{,}15}{100}$$
    """)

    texto(r"""
    Fisicamente, diferenças de temperatura ($\Delta T$) são as grandezas mais relevantes para
    analisar trocas de calor e conforto térmico, pois determinam intensidade e direção do fluxo
    energético. No diagnóstico do ambiente, a temperatura deve ser interpretada como parte de um
    balanço de trocas, não como valor isolado.
    """)

    entendimentos["temp_escalas"] = _caixa_entendimento(
        tema_key="temp_escalas",
        titulo_tema="Temperatura e Escalas Térmicas",
        valor_inicial=entendimentos_salvos.get("temp_escalas", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # =============================
    # 2) TEORIA CINÉTICA DOS GASES
    # =============================
    st.markdown(
        """
        <div style="text-align: justify;">
        <h3>Teoria Cinética dos Gases</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=QnNk82CX2Es&t=496s")

    texto(r"""
    A teoria cinética dos gases fornece a leitura microscópica da temperatura: um gás é composto
    por moléculas em movimento contínuo e desordenado, interagindo por colisões entre si e com
    as superfícies do ambiente. Nessa perspectiva, a temperatura mede a <b>energia cinética média</b>
    das moléculas. Para um gás ideal:

    $$\langle E_c \rangle = \frac{3}{2} k_B T$$

    onde $\langle E_c \rangle$ é a energia cinética média por molécula, $k_B$ é a constante de Boltzmann
    e $T$ é a temperatura absoluta (Kelvin). Portanto, elevar a temperatura significa aumentar, em média,
    a agitação molecular do ar.
    """)

    texto(r"""
    No PBL de conforto térmico, essa ponte é decisiva: a temperatura do ar representa o nível de energia
    disponível para trocas com a pele por colisões moleculares, afetando especialmente condução e convecção.
    Assim, o sensor de temperatura fornece um indicador direto do “potencial” de troca térmica do ar com o corpo.
    """)

    entendimentos["teoria_cinetica"] = _caixa_entendimento(
        tema_key="teoria_cinetica",
        titulo_tema="Teoria Cinética dos Gases",
        valor_inicial=entendimentos_salvos.get("teoria_cinetica", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # =================================
    # 3) CALOR E FORMAS DE TRANSFERÊNCIA
    # =================================
    st.markdown(
        """
        <div style="text-align: justify;">
        <h3>Calor e Formas de Transferência</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/embed/0Hu0KmdraD0")
    st.video("https://www.youtube.com/embed/Du4ahjrkMcQ")
    st.video("https://www.youtube.com/embed/XABOuQhXwSo")

    texto(r"""
    Em Física, <b>calor</b> é energia em trânsito: não é “algo contido” no corpo, mas a transferência de energia
    que ocorre devido a uma diferença de temperatura. Sempre que existe um gradiente térmico, há fluxo espontâneo
    de energia do sistema mais quente para o mais frio, até que as condições tendam ao equilíbrio.
    """)

    texto(r"""
    No conforto térmico, o corpo humano (com geração metabólica de energia) troca calor com o ambiente por mecanismos
    distintos. O desconforto surge quando a combinação desses mecanismos dificulta manter o balanço energético corporal
    em uma faixa estável: o corpo acumula energia (sensação de calor) ou perde energia em excesso (sensação de frio).
    """)

    entendimentos["calor_transferencia"] = _caixa_entendimento(
        tema_key="calor_transferencia",
        titulo_tema="Calor e Formas de Transferência",
        valor_inicial=entendimentos_salvos.get("calor_transferencia", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # ----------------
    # 3.1) Condução
    # ----------------
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Condução — calor por contato direto</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/embed/R8xvZQ7zkUE")

    st.markdown(
        """
        <div style='text-align: justify'>
        <b>Condução</b> é a transferência de energia térmica de molécula para molécula, sem movimento global do material.
        Ocorre quando há contato térmico e diferença de temperatura.

        <b>Exemplos:</b>
        <ul>
        <li>Encostar a mão em uma superfície metálica fria.</li>
        <li>Caminhar descalço em um piso aquecido pelo sol.</li>
        </ul>

        Materiais como metais conduzem bem o calor; ar, madeira e tecidos conduzem mal.
        </div>
        """,
        unsafe_allow_html=True,
    )

    texto(r"""
    No diagnóstico de conforto, a condução é particularmente relevante quando há contato com superfícies (cadeiras,
    mesas, pisos, paredes). Um ambiente pode estar “com ar confortável”, mas causar desconforto por contato com materiais
    muito frios ou muito quentes.
    """)

    entendimentos["conducao"] = _caixa_entendimento(
        tema_key="conducao",
        titulo_tema="Condução — calor por contato direto",
        valor_inicial=entendimentos_salvos.get("conducao", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # ----------------
    # 3.2) Convecção
    # ----------------
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Convecção — calor transportado pelo movimento do ar</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/embed/nKUjAKkAnkU")

    st.markdown(
        """
        <div style='text-align: justify'>
        <b>Convecção</b> é a transferência de calor associada ao movimento de um fluido (ar). O ar em movimento transporta energia e
        altera a taxa de troca térmica com a superfície do corpo.

        Existem dois regimes importantes:
        <ul>
        <li><b>Convecção natural:</b> movimento gerado por diferenças de densidade (ar aquecido sobe; ar resfriado desce).</li>
        <li><b>Convecção forçada:</b> movimento imposto por agentes externos (vento, ventiladores, ar-condicionado, ventilação).</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    texto(r"""
    No conforto térmico, a convecção costuma ser decisiva porque a <b>velocidade do ar</b> pode alterar a sensação térmica mesmo
    com temperatura praticamente constante. Assim, o mesmo ambiente pode ser percebido como “abafado” (ar parado) ou “fresco”
    (ar em movimento). No PBL, isso fundamenta o uso de medições de vento/ventilação para sustentar o diagnóstico.
    """)

    texto(r"""
    A distinção entre convecção natural e forçada é importante para interpretar dados no 
    aplicativo. Na <b>natural</b>, o escoamento emerge do próprio gradiente térmico do 
    ambiente (plumas de ar quente, estratificação). Na <b>forçada</b>, a ventilação é imposta 
    por dispositivos ou aberturas, elevando a taxa de troca térmica com a pele e podendo 
    aumentar a sensação de resfriamento mesmo sem reduzir a temperatura do ar. Esse ponto 
    ajuda o estudante a justificar por que “abrir uma janela” ou “ligar um ventilador” 
    altera o conforto, ainda que o termômetro mude pouco.
    """)

    st.video("https://www.youtube.com/embed/nKUjAKkAnkU")

    entendimentos["conveccao"] = _caixa_entendimento(
        tema_key="conveccao",
        titulo_tema="Convecção — calor transportado pelo movimento do ar",
        valor_inicial=entendimentos_salvos.get("conveccao", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # ----------------
    # 3.3) Radiação
    # ----------------
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Radiação térmica — calor na forma de ondas</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/embed/8ra9SD-8xJc")

    st.markdown(
        """
        <div style='text-align: justify'>
        <b>Radiação</b> é a transferência de energia por ondas eletromagnéticas, não exigindo contato nem movimento do ar.
        Todos os corpos emitem radiação térmica e também podem absorvê-la (paredes, teto, janelas, pessoas).

        <b>Exemplos:</b>
        <ul>
        <li>Parede aquecida pelo sol irradiando calor para o interior.</li>
        <li>Sensação de calor ao sentar perto de uma janela ensolarada.</li>
        <li>Telhas aquecidas emitindo radiação mesmo quando o ar está mais ameno.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    texto(r"""
    No conforto térmico, a radiação explica por que a pessoa pode sentir calor mesmo com “temperatura do ar aceitável”:
    superfícies quentes elevam o ganho radiativo do corpo. No PBL, isso orienta o diagnóstico para além do termômetro,
    incluindo insolação, materiais, orientação solar e temperatura de superfícies.
    """)

    entendimentos["radiacao"] = _caixa_entendimento(
        tema_key="radiacao",
        titulo_tema="Radiação térmica — calor na forma de ondas",
        valor_inicial=entendimentos_salvos.get("radiacao", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # --------------------------------
    # 3.4) Integração dos mecanismos
    # --------------------------------
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Integração dos mecanismos</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=tuNHFe8kauA")

    st.markdown(
        """
        <div style='text-align: justify'>
        Em ambientes reais, <b>condução</b>, <b>convecção</b> e <b>radiação</b> atuam simultaneamente. 
        A sensação térmica resulta do efeito combinado desses processos sobre o corpo humano.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='text-align: justify'>
        O desconforto térmico surge quando <b>um ou mais mecanismos domina</b> de modo desfavorável:
        ar parado (convecção fraca), radiação intensa de superfícies aquecidas, contato com superfícies muito frias/quentes, etc.
        No PBL, a meta é transformar essa percepção em diagnóstico: identificar qual mecanismo é o principal responsável e
        justificar com medições e observações do ambiente.
        </div>
        """,
        unsafe_allow_html=True,
    )

    entendimentos["integracao"] = _caixa_entendimento(
        tema_key="integracao",
        titulo_tema="Integração dos mecanismos",
        valor_inicial=entendimentos_salvos.get("integracao", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # ==================================
    # 4) PRIMEIRA LEI DA TERMODINÂMICA
    # ==================================
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Primeira Lei da Termodinâmica</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=U_2AJc1mcas")
    st.video("https://www.youtube.com/embed/MK7YxiqJSCk")

    texto(r"""
    A <b>Primeira Lei da Termodinâmica</b> expressa a conservação da energia: a variação da energia interna de um sistema
    depende da energia trocada com o meio. Em forma compacta:

    $$\Delta U = Q - W$$

    onde ΔU é a variação da energia interna, Q é a energia trocada como calor e W é o trabalho realizado pelo sistema.
    """)

    texto(r"""
    No conforto térmico, o corpo humano pode ser tratado como um sistema termodinâmico com geração metabólica de energia
    e trocas contínuas com o ambiente (condução, convecção e radiação). Quando o balanço energético se aproxima de zero ao longo
    do tempo, a temperatura corporal tende a permanecer estável; quando não, surgem respostas fisiológicas e sensação de desconforto.
    No PBL, essa lei fornece o “esqueleto” do diagnóstico: identificar entradas e saídas de energia que explicam a sensação térmica.
    """)

    entendimentos["primeira_lei"] = _caixa_entendimento(
        tema_key="primeira_lei",
        titulo_tema="Primeira Lei da Termodinâmica",
        valor_inicial=entendimentos_salvos.get("primeira_lei", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # ==========================
    # 5) EQUILÍBRIO TÉRMICO
    # ==========================
    st.markdown(
        """<h3 style='margin-bottom: 0.5rem;'>Equilíbrio Térmico</h3>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=pCqBui3RhqI")

    texto(r"""
    O <b>equilíbrio térmico</b> é a condição em que não há fluxo líquido de calor entre sistemas em interação térmica.
    Na formulação clássica, isso ocorre quando as temperaturas se igualam e as trocas por condução, convecção e radiação
    não geram variação líquida de energia.
    """)

    texto(r"""
    No conforto térmico humano, o equilíbrio deve ser entendido de modo funcional: o objetivo não é igualar a temperatura do corpo
    à do ambiente, mas manter o <b>balanço energético aproximadamente nulo</b> (produção metabólica compensada por perdas/ganhos).
    Quando o ambiente impede essa compensação, o corpo acumula energia (sensação de calor) ou perde energia em excesso (sensação de frio).
    No PBL, esse conceito fecha o raciocínio: conforto é a condição em que o ambiente permite estabilidade térmica do corpo sem esforço
    fisiológico excessivo.
    """)

    st.markdown("---")

    entendimentos["equilibrio_termico"] = _caixa_entendimento(
        tema_key="equilibrio_termico",
        titulo_tema="Equilíbrio Térmico",
        valor_inicial=entendimentos_salvos.get("equilibrio_termico", ""),
        path=path,
        aluno=aluno,
        grupo_id=grupo_id,
        grupo_nome=grupo_nome,
    )

    # -------------------------------------------------------------------------
    # Checklist (domina vs precisa estudar)
    # -------------------------------------------------------------------------
    st.write("### Checklist")

    st.markdown(
        """
        <div style="text-align: justify;">
            <b>Objetivo desta etapa:</b> registrar, com honestidade, o que <b>você</b> já domina e o que ainda precisa
            consolidar <b>para investigar e explicar o problema</b>.  
            <br><br>
            <b>Como usar:</b> marque <i>“Precisa estudar”</i> quando o conceito ainda não está suficientemente claro
            para interpretar dados, justificar diagnósticos e sustentar decisões no PBL.  
            Os itens marcados como <i>“Precisa estudar”</i> devem orientar a <b>Investigação</b> na próxima etapa.
            <br><br>
            Dica: evite marcar as duas opções no mesmo item; escolha a que melhor representa o seu estado atual.
            Se você estiver em dúvida, prefira marcar <i>“Precisa estudar”</i>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # pré-carregar checklist salvo deste stage (se existir)
    saved = stage_data.get("checklist", {}) if isinstance(stage_data, dict) else {}
    if not isinstance(saved, dict):
        saved = {}

    checklist: Dict[str, Dict[str, bool]] = {}

    for c in CONTEUDOS:
        col1, col2 = st.columns([1, 1])

        with col1:
            domina = st.checkbox(
                f"Já domina: {c}",
                value=bool(saved.get(c, {}).get("domina", False)),
                key=f"{STAGE_ID}_domina_{c}",
            )

        with col2:
            precisa = st.checkbox(
                f"Precisa estudar: {c}",
                value=bool(saved.get(c, {}).get("precisa_estudar", False)),
                key=f"{STAGE_ID}_precisa_{c}",
            )

        if domina and precisa:
            domina = False
            st.info(f"Ajuste automático em “{c}”: mantido como “Precisa estudar” (prioridade para investigação).")

        checklist[c] = {"domina": domina, "precisa_estudar": precisa}
        st.markdown("<div style='margin-top: 0.2rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Síntese curta
    # -------------------------------------------------------------------------
    st.write("### Síntese individual das lacunas conceituais")

    lacunas_auto = [c for c, v in checklist.items() if v.get("precisa_estudar")]
    sugestao = ""
    if lacunas_auto:
        sugestao = (
            "Rascunho (edite livremente):\n"
            "O grupo precisa aprofundar: "
            + "; ".join(lacunas_auto)
            + ".\n"
            "Motivo: ainda não conseguimos usar esses conceitos para interpretar as medições e justificar o diagnóstico "
            "de conforto/desconforto no ambiente analisado."
        )

    sintese = st.text_area(
        "Em 3–6 linhas, descreva quais conteúdos você precisa aprofundar e justifique essa necessidade.",
        value=((stage_data.get("sintese") or "") if isinstance(stage_data, dict) else "") or sugestao,
        height=140,
        key=f"{STAGE_ID}_sintese",
    )

    # -------------------------------------------------------------------------
    # Salvar final (consolida checklist + síntese + entendimentos)
    # -------------------------------------------------------------------------
    msg_box = st.empty()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            # recarrega container para evitar sobrescrever mudanças em outras telas
            root2 = _load_root_container(path, aluno, grupo_id, grupo_nome)
            stage2 = _get_stage_data(root2, STAGE_ID)

            # merge entendimentos: prioriza o que está na tela; se algum não foi tocado, mantém o salvo
            ents_salvos = stage2.get("entendimentos", {})
            if not isinstance(ents_salvos, dict):
                ents_salvos = {}

            ents_tela = {k: (v or "").strip() for k, v in entendimentos.items()}
            ents_final = dict(ents_salvos)
            for k, v in ents_tela.items():
                if v != "":
                    ents_final[k] = v

            lacunas = [c for c, v in checklist.items() if v.get("precisa_estudar")]

            stage2.update(
                {
                    "stage_id": STAGE_ID,
                    "saved_at": _now_iso(),
                    "aluno": aluno,
                    "grupo_id": grupo_id,
                    "grupo_nome": grupo_nome,
                    "conteudos": CONTEUDOS,
                    "entendimentos": ents_final,
                    "checklist": checklist,
                    "sintese": sintese.strip(),
                    "lacunas": lacunas,
                    "concluido": False,
                }
            )

            avisos = []
            if not sintese.strip():
                avisos.append("Escreva a síntese curta (3–6 linhas) registrando as lacunas e a justificativa.")

            if not lacunas and sintese.strip():
                if "não" not in sintese.lower() and "domina" not in sintese.lower() and "sem lacunas" not in sintese.lower():
                    avisos.append(
                        "Se nenhum item foi marcado como “precisa estudar”, justifique na síntese por que você considera "
                        "que domina os conceitos o suficiente para resolver o problema."
                    )

            if not avisos:
                stage2["concluido"] = True

            _update_stage(root2, STAGE_ID, stage2)
            save_json(path, root2)

            if avisos:
                msg_box.success("Salvo.")
                msg_box.warning("A etapa ainda não está totalmente concluída:")
                for a in avisos:
                    msg_box.write(f"- {a}")
            else:
                msg_box.success("Conteúdos essenciais registrados. Etapa concluída.")

    with col2:
        lacunas_count = len([c for c, v in checklist.items() if v.get("precisa_estudar")])

        if lacunas_count == 0:
            status_txt = "Sem lacunas marcadas (exige justificativa coerente na síntese)."
        elif 1 <= lacunas_count <= 2:
            status_txt = "Poucas lacunas: foque em aprofundamento dirigido."
        else:
            status_txt = "Múltiplas lacunas: priorize os itens com maior impacto no diagnóstico."

        # bloco de resumo opcional (mantido comentado como no seu original)
        # st.markdown(
        #     f"""
        #     <div style="text-align: justify;">
        #         <strong>Resumo:</strong><br>
        #         Itens marcados como “precisa estudar”: <strong>{lacunas_count}</strong><br>
        #         <span style="color:#555;">{status_txt}</span>
        #     </div>
        #     """,
        #     unsafe_allow_html=True,
        # )
