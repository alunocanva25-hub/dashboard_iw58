import streamlit as st
import pandas as pd
import plotly.express as px
import requests, re
from io import BytesIO

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(page_title="Dashboard Notas – AM x AS", layout="wide")

# ======================================================
# CSS (visual do print + organização)
# ======================================================
st.markdown("""
<style>
.stApp { background: #6fa6d6; }
.block-container{ padding-top: 0.6rem; max-width: 1500px; }

.card{
  background: #b9d3ee;
  border: 2px solid rgba(10,40,70,0.30);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 10px 18px rgba(0,0,0,0.18);
  margin-bottom: 14px;
}
.card-title{
  font-weight: 950;
  color:#0b2b45;
  font-size: 13px;
  text-transform: uppercase;
  margin-bottom: 10px;
  letter-spacing: .3px;
}

.kpi-row{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap: 10px;
}
.kpi-big{
  font-size: 42px;
  font-weight: 950;
  color:#9b0d0d;
  line-height: 1.0;
}
.kpi-mini{
  text-align:center;
}
.kpi-mini .lbl{
  font-weight:900; color:#0b2b45; font-size:12px; text-transform:uppercase;
}
.kpi-mini .val{
  font-weight:950; color:#9b0d0d; font-size:26px; line-height: 1.0;
}

.topbar{
  background: rgba(255,255,255,0.35);
  border: 2px solid rgba(10,40,70,0.22);
  border-radius: 18px;
  padding: 10px 14px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom: 10px;
}
.brand{
  display:flex; align-items:center; gap:12px;
}
.brand-badge{
  width:46px; height:46px; border-radius: 14px;
  background: rgba(255,255,255,0.55);
  border: 2px solid rgba(10,40,70,0.22);
  display:flex; align-items:center; justify-content:center;
  font-weight: 950; color:#0b2b45;
}
.brand-text .t1{ font-weight:950; color:#0b2b45; line-height:1.1; }
.brand-text .t2{ font-weight:800; color:#0b2b45; opacity:.85; font-size:12px; }

.right-note{
  text-align:right; font-weight:950; color:#0b2b45;
}
.right-note small{ font-weight:800; opacity:.9; font-size:12px; }

div.stButton > button{
  border-radius: 10px;
  font-weight: 900;
  border: 2px solid rgba(10,40,70,0.22);
  background: rgba(255,255,255,0.45);
  color:#0b2b45;
  padding: .25rem .6rem;
}
div.stButton > button:hover{
  background: rgba(255,255,255,0.65);
  border-color: rgba(10,40,70,0.35);
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# LOGIN
# ======================================================
def tela_login():
    st.markdown("## 🔐 Acesso Restrito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario == st.secrets["auth"]["usuario"] and senha == st.secrets["auth"]["senha"]:
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
# TOPO
# ======================================================
st.markdown("""
<div class="topbar">
  <div class="brand">
    <div class="brand-badge">3C</div>
    <div class="brand-text">
      <div class="t1">DASHBOARD NOTAS – AM x AS</div>
      <div class="t2">Visão gerencial no padrão do painel de referência</div>
    </div>
  </div>
  <div class="right-note">
    FUNÇÃO MEDIÇÃO<br>
    <small>NOTAS AM – ANÁLISE DE MEDIÇÃO<br>NOTAS AS – AUDITORIA DE SERVIÇO</small>
  </div>
</div>
""", unsafe_allow_html=True)

# ======================================================
# FUNÇÕES
# ======================================================
MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}
MESES_ORDEM = [MESES_PT[i] for i in range(1, 13)]

COR_PROC = "#2e7d32"
COR_IMP  = "#c62828"
COR_OUT  = "#546e7a"

def achar_coluna(df, palavras):
    for col in df.columns:
        for p in palavras:
            if p in col:
                return col
    return None

def validar_estrutura(df):
    obrig = {
        "ESTADO/UF": ["ESTADO", "LOCALIDADE", "UF"],
        "RESULTADO": ["RESULTADO"],
        "TIPO": ["TIPO"],
        "DATA": ["DATA"],
    }
    faltando = [nome for nome, alts in obrig.items() if not achar_coluna(df, alts)]
    if faltando:
        st.error("Estrutura da base incompatível. Faltando: " + ", ".join(faltando))
        st.stop()

def _extrair_sheet_id(url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _extrair_drive_id(url: str) -> str | None:
    m = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", url)
    if m: return m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _normalizar_para_csv(url: str) -> str:
    sid = _extrair_sheet_id(url)
    if sid:
        return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid=0"
    did = _extrair_drive_id(url)
    if did:
        return f"https://drive.google.com/uc?id={did}"
    return url

@st.cache_data(ttl=600, show_spinner="🔄 Carregando base...")
def carregar_base(url_original: str) -> pd.DataFrame:
    url = _normalizar_para_csv(url_original)
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    raw = r.content
    head = raw[:400].lstrip().lower()
    if head.startswith(b"<!doctype html") or b"<html" in head:
        raise RuntimeError("URL retornou HTML (não CSV). Verifique permissões do Drive/Sheets.")
    for enc in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=enc)
            df.columns = df.columns.str.upper().str.strip()
            return df
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding="utf-8", encoding_errors="replace")
    df.columns = df.columns.str.upper().str.strip()
    return df

def donut_resultado(df_base, titulo):
    proc = df_base["_RES_"].str.contains("PROCED", na=False).sum()
    imp  = df_base["_RES_"].str.contains("IMPROCED", na=False).sum()

    dados = pd.DataFrame({"Resultado": ["Procedente", "Improcedente"], "QTD": [proc, imp]})
    fig = px.pie(
        dados, names="Resultado", values="QTD", hole=0.62,
        template="plotly_white",
        color="Resultado",
        color_discrete_map={"Procedente": COR_PROC, "Improcedente": COR_IMP}
    )
    fig.update_layout(
        title=titulo,
        height=260,
        margin=dict(l=10, r=10, t=45, b=10),
        legend_title_text=""
    )
    fig.update_traces(textinfo="percent+value")
    return fig

def barh_contagem(df_base, col_dim, titulo):
    if col_dim is None or df_base.empty:
        return None
    dados = df_base.groupby(col_dim).size().reset_index(name="QTD").sort_values("QTD")
    if dados.empty:
        return None
    fig = px.bar(
        dados, x="QTD", y=col_dim, orientation="h", text="QTD",
        title=titulo, template="plotly_white"
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=45, b=10), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig

def acumulado_mensal_fig_e_tabela(df_base, col_data):
    base = df_base.dropna(subset=[col_data]).copy()
    if base.empty:
        return None, None

    base["MES_NUM"] = base[col_data].dt.month
    base["MÊS"] = base["MES_NUM"].map(MESES_PT)

    # Classe (procedente / improcedente / outros)
    base["_CLASSE_"] = "OUTROS"
    base.loc[base["_RES_"].str.contains("PROCED", na=False), "_CLASSE_"] = "PROCEDENTE"
    base.loc[base["_RES_"].str.contains("IMPROCED", na=False), "_CLASSE_"] = "IMPROCEDENTE"

    dados = base.groupby(["MES_NUM", "MÊS", "_CLASSE_"]).size().reset_index(name="QTD")
    dados = dados.sort_values("MES_NUM")

    # Label % somente em PROCEDENTE
    total_mes = dados.groupby("MES_NUM")["QTD"].transform("sum")
    dados["PCT"] = (dados["QTD"] / total_mes * 100).round(0)
    dados["LABEL"] = ""
    dados.loc[dados["_CLASSE_"] == "PROCEDENTE", "LABEL"] = dados.loc[dados["_CLASSE_"] == "PROCEDENTE", "PCT"].astype(int).astype(str) + "%"

    fig = px.bar(
        dados,
        x="MÊS", y="QTD", color="_CLASSE_", barmode="stack",
        text="LABEL",
        category_orders={"MÊS": MESES_ORDEM, "_CLASSE_": ["PROCEDENTE", "IMPROCEDENTE", "OUTROS"]},
        template="plotly_white",
        color_discrete_map={"PROCEDENTE": COR_PROC, "IMPROCEDENTE": COR_IMP, "OUTROS": COR_OUT}
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")

    # Tabela final
    tab = dados.pivot_table(index=["MES_NUM", "MÊS"], columns="_CLASSE_", values="QTD", fill_value=0).reset_index()
    for c in ["IMPROCEDENTE", "PROCEDENTE", "OUTROS"]:
        if c not in tab.columns:
            tab[c] = 0
    tab["TOTAL"] = tab["IMPROCEDENTE"] + tab["PROCEDENTE"] + tab["OUTROS"]
    tab = tab.sort_values("MES_NUM").drop(columns=["MES_NUM"])
    tab = tab.rename(columns={"MÊS": "MÊS", "IMPROCEDENTE": "IMPROCEDENTE", "PROCEDENTE": "PROCEDENTE", "TOTAL": "TOTAL"})
    tab = tab[["MÊS", "IMPROCEDENTE", "PROCEDENTE", "TOTAL"]]

    return fig, tab

# ======================================================
# BOTÃO ATUALIZAR BASE
# ======================================================
colA, colB = st.columns([1, 6])
with colA:
    if st.button("🔄 Atualizar base"):
        st.cache_data.clear()
        st.rerun()
with colB:
    st.caption("Use quando atualizar o arquivo no Drive/Sheets.")

# ======================================================
# CARREGAMENTO
# ======================================================
URL_BASE = "https://drive.google.com/uc?id=1xg5D9tAqhy0DlX7uu6X8e2BsQku1KOs7"
df = carregar_base(URL_BASE)
validar_estrutura(df)

COL_ESTADO    = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO      = achar_coluna(df, ["TIPO"])
COL_MOTIVO    = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL  = achar_coluna(df, ["REGIONAL"])
COL_DATA      = achar_coluna(df, ["DATA"])

# Preparação
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=True)
df["_TIPO_"] = df[COL_TIPO].astype(str).str.upper().str.strip()
df["_RES_"]  = df[COL_RESULTADO].astype(str).str.upper().str.strip()

# Ano referência (último ano encontrado)
ano_ref = int(df[COL_DATA].dt.year.dropna().max()) if df[COL_DATA].notna().any() else None
df_ano = df if ano_ref is None else df[df[COL_DATA].dt.year == ano_ref].copy()
ano_txt = str(ano_ref) if ano_ref else "—"

# ======================================================
# "ABAS" UF
# ======================================================
ufs = sorted(df[COL_ESTADO].dropna().astype(str).str.upper().unique().tolist())
ufs = ["TOTAL"] + ufs

if "uf_sel" not in st.session_state:
    st.session_state.uf_sel = "TOTAL"

per_row = 10
for start in range(0, len(ufs), per_row):
    row = st.columns(min(per_row, len(ufs) - start))
    for i, uf in enumerate(ufs[start:start + per_row]):
        if row[i].button(uf):
            st.session_state.uf_sel = uf

uf_sel = st.session_state.uf_sel
df_filtro = df_ano if uf_sel == "TOTAL" else df_ano[df_ano[COL_ESTADO].astype(str).str.upper() == uf_sel]

df_am = df_filtro[df_filtro["_TIPO_"].str.contains("AM", na=False)]
df_as = df_filtro[df_filtro["_TIPO_"].str.contains("AS", na=False)]

# ======================================================
# 6 BLOCOS (CARDS)
#   Linha 1: KPI + Donut AM + Donut AS
#   Linha 2: Regional AM + Motivos AM + Motivos AS
# ======================================================
row1 = st.columns([1.05, 1.15, 1.15], gap="large")

# Card KPI (mais simples)
with row1[0]:
    total = len(df_filtro)
    am = len(df_am)
    az = len(df_as)

    total_fmt = f"{total:,}".replace(",", ".")
    am_fmt    = f"{am:,}".replace(",", ".")
    as_fmt    = f"{az:,}".replace(",", ".")

    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">ACUMULADO DE NOTAS AM / AS • {ano_txt}</div>
          <div class="kpi-row">
            <div class="kpi-big">{total_fmt}</div>
            <div class="kpi-mini">
              <div class="lbl">AM</div>
              <div class="val">{am_fmt}</div>
            </div>
            <div class="kpi-mini">
              <div class="lbl">AS</div>
              <div class="val">{as_fmt}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Donut AM
with row1[1]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO ANUAL – AM</div>', unsafe_allow_html=True)
    if df_am.empty:
        st.info("Sem dados AM.")
    else:
        st.plotly_chart(donut_resultado(df_am, " "), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Donut AS
with row1[2]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO ANUAL – AS</div>', unsafe_allow_html=True)
    if df_as.empty:
        st.info("Sem dados AS.")
    else:
        st.plotly_chart(donut_resultado(df_as, " "), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Linha 2 (3 cards)
row2 = st.columns(3, gap="large")

with row2[0]:
    st.markdown('<div class="card"><div class="card-title">IMPROCEDÊNCIAS POR REGIONAL – NOTA AM</div>', unsafe_allow_html=True)
    base_imp_am = df_am[df_am["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base_imp_am, COL_REGIONAL, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem improcedências (AM) por regional.")
    st.markdown("</div>", unsafe_allow_html=True)

with row2[1]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTA AM</div>', unsafe_allow_html=True)
    base_imp_am = df_am[df_am["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base_imp_am, COL_MOTIVO, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem motivos (AM).")
    st.markdown("</div>", unsafe_allow_html=True)

with row2[2]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTAS AS</div>', unsafe_allow_html=True)
    base_imp_as = df_as[df_as["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base_imp_as, COL_MOTIVO, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem motivos (AS).")
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# ACUMULADO MENSAL (gráfico) — fora dos 6 cards
# ======================================================
st.markdown('<div class="card"><div class="card-title">ACUMULADO MENSAL DE NOTAS AM – AS</div>', unsafe_allow_html=True)
fig_mensal, tabela_mensal = acumulado_mensal_fig_e_tabela(df_filtro, COL_DATA)
if fig_mensal is not None:
    st.plotly_chart(fig_mensal, use_container_width=True)
else:
    st.info("Sem dados mensais (DATA vazia/ inválida).")
st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# TABELA NO FINAL (como você pediu)
# ======================================================
st.markdown('<div class="card"><div class="card-title">TABELA — VALORES MENSAIS</div>', unsafe_allow_html=True)
if tabela_mensal is not None:
    st.dataframe(tabela_mensal, use_container_width=True, hide_index=True)
else:
    st.info("Sem tabela mensal para exibir.")
st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# EXPORTAÇÃO
# ======================================================
st.markdown('<div class="card"><div class="card-title">EXPORTAR DADOS (FILTRO ATUAL)</div>', unsafe_allow_html=True)
st.download_button(
    label="⬇️ Baixar CSV",
    data=df_filtro.to_csv(index=False).encode("utf-8"),
    file_name="IW58_Dashboard.csv",
    mime="text/csv",
)
st.markdown("</div>", unsafe_allow_html=True)
