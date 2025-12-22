# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(page_title="Dashboard IW58 – AM x AS", layout="wide")

# ======================================================
# CSS (bem próximo ao layout da imagem enviada)
# ======================================================
CSS = """
<style>
/* Fundo azul claro (print) */
.stApp{
  background: #84add8;
}

/* Container principal mais “compacto” */
.block-container{
  padding-top: 0.8rem;
  max-width: 1500px;
}

/* Remove espaço extra de elementos */
div[data-testid="stVerticalBlock"]{ gap: 0.75rem; }

/* Barra superior */
.topbar{
  background: rgba(255,255,255,0.35);
  border: 2px solid rgba(20,50,80,0.25);
  border-radius: 18px;
  padding: 12px 14px;
  display:flex;
  align-items:center;
  justify-content:space-between;
}

/* “Logo” placeholder */
.brand{
  display:flex;
  gap:12px;
  align-items:center;
}
.brand-badge{
  width:44px;
  height:44px;
  border-radius: 12px;
  background: rgba(0,0,0,0.15);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:900;
  color:#0b2b45;
  font-size:18px;
}
.brand-title{
  font-weight:900;
  color:#0b2b45;
  line-height:1.1;
}
.brand-sub{
  font-size: 12px;
  font-weight: 700;
  color:#0b2b45;
  opacity:0.85;
}

/* Tabs (UFs) */
.tabs{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  justify-content:center;
}
.tab{
  background: rgba(255,255,255,0.55);
  border: 2px solid rgba(20,50,80,0.25);
  padding: 6px 12px;
  border-radius: 10px;
  font-weight:800;
  color:#0b2b45;
  font-size: 14px;
}

/* Cards */
.card{
  background: rgba(214,232,252,0.85);
  border: 2px solid rgba(20,50,80,0.25);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 10px 18px rgba(0,0,0,0.20);
}

.card-title{
  font-weight: 900;
  color:#0b2b45;
  font-size: 14px;
  letter-spacing: .2px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.kpi-big{
  font-size: 42px;
  font-weight: 950;
  color: #9b0d0d;
  line-height: 1.0;
}
.kpi-mid{
  font-size: 30px;
  font-weight: 950;
  color: #9b0d0d;
  line-height: 1.0;
}
.kpi-row{
  display:flex;
  justify-content:space-between;
  gap:12px;
  margin-top: 10px;
}
.kpi-block{
  flex:1;
  background: rgba(255,255,255,0.35);
  border: 1px solid rgba(20,50,80,0.18);
  border-radius: 14px;
  padding: 10px 12px;
}
.kpi-label{
  font-weight: 900;
  color:#0b2b45;
  font-size: 13px;
  opacity: .9;
  margin-bottom: 6px;
}

/* Plotly dentro do card */
[data-testid="stPlotlyChart"] > div{
  border-radius: 12px;
}

/* Botões de UF — deixa mais “flat” */
div.stButton > button{
  width:100%;
  border-radius: 10px;
  font-weight: 900;
  border: 2px solid rgba(20,50,80,0.25);
  background: rgba(255,255,255,0.55);
  color:#0b2b45;
}
div.stButton > button:hover{
  border: 2px solid rgba(20,50,80,0.45);
  background: rgba(255,255,255,0.75);
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================
# LOGIN
# ======================================================
def tela_login():
    st.markdown("## 🔐 Acesso Restrito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        try:
            ok = (
                usuario == st.secrets["auth"]["usuario"]
                and senha == st.secrets["auth"]["senha"]
            )
        except Exception:
            st.error("Configuração de secrets ausente. Configure auth.usuario e auth.senha em .streamlit/secrets.toml")
            st.stop()

        if ok:
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    tela_login()
    st.stop()

# ======================================================
# FUNÇÕES UTILITÁRIAS
# ======================================================
def achar_coluna(df, palavras):
    # df.columns já em UPPER
    for coluna in df.columns:
        for palavra in palavras:
            if palavra in coluna:
                return coluna
    return None

def norm_str(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.strip()

def safe_contains(series: pd.Series, pattern: str) -> pd.Series:
    return norm_str(series).str.contains(pattern, na=False)

def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")

# ======================================================
# CARREGAMENTO DA BASE (GOOGLE DRIVE)
# ======================================================
@st.cache_data(show_spinner=False)
def carregar_base():
    url = "https://drive.google.com/uc?id=1JRI_yTUKrj94ocfMLa1Llh9jRU-z4FOd"
    df = pd.read_csv(url, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.upper().str.strip()
    return df

df = carregar_base()

# ======================================================
# IDENTIFICAÇÃO DAS COLUNAS
# ======================================================
COL_ESTADO   = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO     = achar_coluna(df, ["TIPO"])
COL_MOTIVO   = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL = achar_coluna(df, ["REGIONAL"])
COL_DATA     = achar_coluna(df, ["DATA", "DT", "EMISSAO", "EMISSÃO", "DIA"])

obrig = [COL_ESTADO, COL_RESULTADO, COL_TIPO, COL_DATA]
if any(c is None for c in obrig):
    st.error(
        "Colunas obrigatórias não encontradas. Preciso de colunas equivalentes a: "
        "ESTADO/UF, RESULTADO, TIPO (AM/AS), DATA."
    )
    st.stop()

# ======================================================
# TRATAMENTO DE DATA
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=True)
df = df.dropna(subset=[COL_DATA]).copy()

df["ANO"] = df[COL_DATA].dt.year
df["MES_NUM"] = df[COL_DATA].dt.month
df["MES_NOME"] = df[COL_DATA].dt.strftime("%B").str.upper()
df["MES_ANO"] = df[COL_DATA].dt.to_period("M").astype(str)  # 2025-01 etc.
df["MES_ANO_LABEL"] = df[COL_DATA].dt.strftime("%b/%Y").str.upper()

# ======================================================
# TOPO (barra de navegação / UFs)
# ======================================================
# texto no canto direito (igual ao print)
st.markdown(
    """
    <div class="topbar">
      <div class="brand">
        <div class="brand-badge">3C</div>
        <div>
          <div class="brand-title">Dashboard IW58</div>
          <div class="brand-sub">AM = Análise de Medição | AS = Auditoria de Serviço</div>
        </div>
      </div>
      <div style="text-align:right; font-weight:900; color:#0b2b45;">
        FUNÇÃO MEDIÇÃO<br>
        <span style="font-weight:800; font-size:12px; opacity:.9;">
          NOTAS AM – ANÁLISE DE MEDIÇÃO<br>
          NOTAS AS – AUDITORIA DE SERVIÇO
        </span>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================================================
# FILTRO POR ESTADO (botões como “tabs”)
# ======================================================
estados = sorted(df[COL_ESTADO].dropna().astype(str).str.upper().str.strip().unique().tolist())
estados = ["TOTAL"] + estados

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

# grid responsivo (em vez de 1 coluna por estado, que estoura)
# vamos mostrar em 7 por linha
per_row = 7
for start in range(0, len(estados), per_row):
    row = st.columns(min(per_row, len(estados) - start))
    for i, est in enumerate(estados[start:start+per_row]):
        if row[i].button(est):
            st.session_state.estado_sel = est

estado = st.session_state.estado_sel
df_filtro = df if estado == "TOTAL" else df[norm_str(df[COL_ESTADO]) == estado]

# ======================================================
# SEPARAÇÃO AM / AS
# ======================================================
df_am = df_filtro[safe_contains(df_filtro[COL_TIPO], "AM")]
df_as = df_filtro[safe_contains(df_filtro[COL_TIPO], "AS")]

# ======================================================
# KPIs (ACUMULADO + AM + AS) - como no print
# ======================================================
kpi_row = st.columns([1.1, 1.3, 2.6])

# total do ano corrente do filtro (se tiver anos diferentes, usa o mais recente)
ano_ref = int(df_filtro["ANO"].max()) if len(df_filtro) else int(df["ANO"].max())
base_ano = df_filtro[df_filtro["ANO"] == ano_ref]

total_ano = len(base_ano)
am_ano = len(base_ano[safe_contains(base_ano[COL_TIPO], "AM")])
as_ano = len(base_ano[safe_contains(base_ano[COL_TIPO], "AS")])

with kpi_row[0]:
    st.markdown(f"""
      <div class="card">
        <div class="card-title">ACUMULADO DE NOTAS AM / AS – {ano_ref}</div>
        <div class="kpi-big">{fmt_int(total_ano)}</div>
        <div class="kpi-row">
          <div class="kpi-block">
            <div class="kpi-label">AM</div>
            <div class="kpi-mid">{fmt_int(am_ano)}</div>
          </div>
          <div class="kpi-block">
            <div class="kpi-label">AS</div>
            <div class="kpi-mid">{fmt_int(as_ano)}</div>
          </div>
        </div>
      </div>
    """, unsafe_allow_html=True)

# ======================================================
# ACUMULADO ANUAL (stacked horizontal) - como no print
# ======================================================
def acumulado_anual(df_base, ano):
    base = df_base[df_base["ANO"] == ano].copy()
    if base.empty:
        return None

    base["TIPO_NORM"] = norm_str(base[COL_TIPO]).str.extract(r"(AM|AS)", expand=False).fillna(norm_str(base[COL_TIPO]))
    base["RES_NORM"] = norm_str(base[COL_RESULTADO])

    # Procedente / Improcedente
    base["CLASSE"] = "OUTROS"
    base.loc[base["RES_NORM"].str.contains("PROCED", na=False), "CLASSE"] = "PROCEDENTE"
    base.loc[base["RES_NORM"].str.contains("IMPROCED", na=False), "CLASSE"] = "IMPROCEDENTE"

    dados = (
        base.groupby(["TIPO_NORM", "CLASSE"])
        .size()
        .reset_index(name="QUANTIDADE")
    )

    # manter ordem AM/AS
    ordem_tipo = [t for t in ["AM", "AS"] if t in dados["TIPO_NORM"].unique()]
    if not ordem_tipo:
        ordem_tipo = sorted(dados["TIPO_NORM"].unique().tolist())

    fig = px.bar(
        dados,
        x="QUANTIDADE",
        y="TIPO_NORM",
        color="CLASSE",
        orientation="h",
        barmode="stack",
        text="QUANTIDADE",
        category_orders={"TIPO_NORM": ordem_tipo, "CLASSE": ["PROCEDENTE", "IMPROCEDENTE", "OUTROS"]},
        title="ACUMULADO ANUAL",
        template="plotly_white",
    )
    fig.update_layout(
        height=235,
        margin=dict(l=10, r=10, t=40, b=10),
        legend_title_text="",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig

with kpi_row[1]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO ANUAL</div>', unsafe_allow_html=True)
    fig_aa = acumulado_anual(df_filtro, ano_ref)
    if fig_aa is None:
        st.info("Sem dados no período.")
    else:
        st.plotly_chart(fig_aa, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# ACUMULADO MENSAL AM-AS (barras por mês, percentuais no topo)
# ======================================================
def acumulado_mensal(df_base, ano):
    base = df_base[df_base["ANO"] == ano].copy()
    if base.empty:
        return None

    base["TIPO_NORM"] = norm_str(base[COL_TIPO]).str.extract(r"(AM|AS)", expand=False).fillna(norm_str(base[COL_TIPO]))
    base["RES_NORM"] = norm_str(base[COL_RESULTADO])

    base["CLASSE"] = "OUTROS"
    base.loc[base["RES_NORM"].str.contains("PROCED", na=False), "CLASSE"] = "PROCEDENTE"
    base.loc[base["RES_NORM"].str.contains("IMPROCED", na=False), "CLASSE"] = "IMPROCEDENTE"

    # Agrupa por mês e tipo
    dados = (
        base.groupby(["MES_NUM", "MES_ANO_LABEL", "TIPO_NORM", "CLASSE"])
        .size()
        .reset_index(name="QUANTIDADE")
    )

    # total por mês/tipo para %
    totais = dados.groupby(["MES_NUM", "MES_ANO_LABEL", "TIPO_NORM"])["QUANTIDADE"].transform("sum")
    dados["PCT"] = (dados["QUANTIDADE"] / totais * 100).round(0).astype("Int64")

    # só coloca label % para PROCEDENTE (como no print)
    dados["LABEL"] = ""
    mask_proc = dados["CLASSE"].eq("PROCEDENTE")
    dados.loc[mask_proc, "LABEL"] = dados.loc[mask_proc, "PCT"].astype(str) + "%"

    # manter ordem meses
    ordem_mes = (
        dados[["MES_NUM", "MES_ANO_LABEL"]]
        .drop_duplicates()
        .sort_values("MES_NUM")["MES_ANO_LABEL"]
        .tolist()
    )

    fig = px.bar(
        dados,
        x="MES_ANO_LABEL",
        y="QUANTIDADE",
        color="CLASSE",
        facet_row="TIPO_NORM",
        barmode="stack",
        text="LABEL",
        category_orders={"MES_ANO_LABEL": ordem_mes, "CLASSE": ["PROCEDENTE", "IMPROCEDENTE", "OUTROS"]},
        title="ACUMULADO MENSAL DE NOTAS AM – AS",
        template="plotly_white",
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text="",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    # reduz texto do facet
    fig.for_each_annotation(lambda a: a.update(text=a.text.replace("TIPO_NORM=", "")))
    return fig

with kpi_row[2]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO MENSAL DE NOTAS AM – AS</div>', unsafe_allow_html=True)
    fig_am = acumulado_mensal(df_filtro, ano_ref)
    if fig_am is None:
        st.info("Sem dados no período.")
    else:
        st.plotly_chart(fig_am, use_container_width=True)

    # Tabela-resumo abaixo (como no print)
    base_ano2 = df_filtro[df_filtro["ANO"] == ano_ref].copy()
    if not base_ano2.empty:
        base_ano2["TIPO_NORM"] = norm_str(base_ano2[COL_TIPO]).str.extract(r"(AM|AS)", expand=False).fillna(norm_str(base_ano2[COL_TIPO]))
        base_ano2["RES_NORM"] = norm_str(base_ano2[COL_RESULTADO])
        base_ano2["CLASSE"] = "OUTROS"
        base_ano2.loc[base_ano2["RES_NORM"].str.contains("PROCED", na=False), "CLASSE"] = "PROCEDENTE"
        base_ano2.loc[base_ano2["RES_NORM"].str.contains("IMPROCED", na=False), "CLASSE"] = "IMPROCEDENTE"

        tb = (
            base_ano2.groupby(["MES_NUM", "MES_ANO_LABEL", "CLASSE"])
            .size()
            .reset_index(name="QTD")
        )
        tb_piv = tb.pivot_table(index=["MES_NUM", "MES_ANO_LABEL"], columns="CLASSE", values="QTD", fill_value=0).reset_index()
        tb_piv["TOTAL"] = tb_piv.sum(axis=1, numeric_only=True)
        tb_piv = tb_piv.sort_values("MES_NUM").drop(columns=["MES_NUM"])
        tb_piv = tb_piv.rename(columns={"MES_ANO_LABEL": "MÊS"})

        st.dataframe(tb_piv, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# LINHA 3 — IMPROCEDÊNCIAS POR REGIONAL (AM) + MOTIVOS (AM) + MOTIVOS (AS)
# ======================================================
row3 = st.columns(3)

def improcedencias_por_regional_am(df_base):
    if COL_REGIONAL is None:
        return None
    base = df_base.copy()
    base = base[safe_contains(base[COL_TIPO], "AM")]
    base = base[safe_contains(base[COL_RESULTADO], "IMPROCED")]
    if base.empty:
        return None

    dados = (
        base.groupby(COL_REGIONAL)
        .size()
        .reset_index(name="QUANTIDADE")
        .sort_values("QUANTIDADE")
    )

    fig = px.bar(
        dados,
        x="QUANTIDADE",
        y=COL_REGIONAL,
        orientation="h",
        text="QUANTIDADE",
        title="IMPROCEDÊNCIAS POR REGIONAL – NOTA AM",
        template="plotly_white",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=55, b=10), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig

def motivos_improcedencia(df_base, tipo_alvo, titulo):
    if COL_MOTIVO is None:
        return None
    base = df_base.copy()
    base = base[safe_contains(base[COL_TIPO], tipo_alvo)]
    base = base[safe_contains(base[COL_RESULTADO], "IMPROCED")]
    if base.empty:
        return None

    dados = (
        base.groupby(COL_MOTIVO)
        .size()
        .reset_index(name="QUANTIDADE")
        .sort_values("QUANTIDADE", ascending=True)
    )

    fig = px.bar(
        dados,
        x="QUANTIDADE",
        y=COL_MOTIVO,
        orientation="h",
        text="QUANTIDADE",
        title=titulo,
        template="plotly_white",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=55, b=10), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig

with row3[0]:
    st.markdown('<div class="card"><div class="card-title">IMPROCEDÊNCIAS POR REGIONAL – NOTA AM</div>', unsafe_allow_html=True)
    fig_r = improcedencias_por_regional_am(df_filtro[df_filtro["ANO"] == ano_ref])
    if fig_r is None:
        st.info("Sem dados de improcedência por regional (AM).")
    else:
        st.plotly_chart(fig_r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with row3[1]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTA AM</div>', unsafe_allow_html=True)
    fig_m_am = motivos_improcedencia(df_filtro[df_filtro["ANO"] == ano_ref], "AM", "MOTIVOS DE IMPROCEDÊNCIAS – NOTA AM")
    if fig_m_am is None:
        st.info("Sem dados de motivos (AM).")
    else:
        st.plotly_chart(fig_m_am, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with row3[2]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTAS AS</div>', unsafe_allow_html=True)
    fig_m_as = motivos_improcedencia(df_filtro[df_filtro["ANO"] == ano_ref], "AS", "MOTIVOS DE IMPROCEDÊNCIAS – NOTAS AS")
    if fig_m_as is None:
        st.info("Sem dados de motivos (AS).")
    else:
        st.plotly_chart(fig_m_as, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# EXPORTAÇÃO
# ======================================================
st.markdown('<div class="card"><div class="card-title">EXPORTAR DADOS (FILTRO ATUAL)</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1, 3])

with c1:
    st.download_button(
        label="⬇️ Baixar CSV",
        data=df_filtro.to_csv(index=False).encode("utf-8"),
        file_name=f"IW58_Dashboard_{estado}_{ano_ref}.csv".replace(" ", "_"),
        mime="text/csv"
    )

with c2:
    st.caption(
        f"Filtro atual: **{estado}** | Ano de referência: **{ano_ref}** | "
        f"Registros no filtro: **{fmt_int(len(df_filtro))}**"
    )

st.markdown("</div>", unsafe_allow_html=True)
