import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests, re
from io import BytesIO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(page_title="Dashboard Notas – AM x AS", layout="wide")

# ======================================================
# CSS (VISUAL do print)
# ======================================================
st.markdown("""
<style>
.stApp { background: #6fa6d6; } /* azul do fundo */
.block-container{ padding-top: 0.6rem; max-width: 1500px; }

.card{
  background: #b9d3ee;
  border: 2px solid rgba(10,40,70,0.30);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 10px 18px rgba(0,0,0,0.18);
}
.card-title{
  font-weight: 900;
  color:#0b2b45;
  font-size: 14px;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.kpi-big{
  font-size: 44px;
  font-weight: 950;
  color:#9b0d0d;
  line-height: 1.0;
}
.kpi-sub{
  display:flex;
  gap:22px;
  justify-content:center;
  margin-top: 6px;
}
.kpi-sub .lbl{
  font-weight:900; color:#0b2b45; font-size:14px; text-align:center;
}
.kpi-sub .val{
  font-weight:950; color:#9b0d0d; font-size:28px; text-align:center;
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
# LOGIN (mantido)
# ======================================================
def tela_login():
    st.markdown("## 🔐 Acesso Restrito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if (usuario == st.secrets["auth"]["usuario"] and senha == st.secrets["auth"]["senha"]):
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
# FUNÇÕES BASE
# ======================================================
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
    faltando = []
    for nome, alts in obrig.items():
        if not achar_coluna(df, alts):
            faltando.append(nome)
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

# ======================================================
# TOPO (como no print)
# ======================================================
st.markdown("""
<div class="topbar">
  <div class="brand">
    <div class="brand-badge">3C</div>
    <div class="brand-text">
      <div class="t1">DASHBOARD NOTAS – AM x AS</div>
      <div class="t2">Visual no padrão do painel de referência</div>
    </div>
  </div>
  <div class="right-note">
    FUNÇÃO MEDIÇÃO<br>
    <small>NOTAS AM – ANÁLISE DE MEDIÇÃO<br>NOTAS AS – AUDITORIA DE SERVIÇO</small>
  </div>
</div>
""", unsafe_allow_html=True)

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
URL_BASE = "https://drive.google.com/uc?id=1NteTwRrAnnpOCVZH6mlassTzeWKsOdYY"
df = carregar_base(URL_BASE)
validar_estrutura(df)

COL_ESTADO    = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO      = achar_coluna(df, ["TIPO"])
COL_MOTIVO    = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL  = achar_coluna(df, ["REGIONAL"])
COL_DATA      = achar_coluna(df, ["DATA"])

# Data (não derruba linhas)
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=True)

# Normalizações
df["_TIPO_"] = df[COL_TIPO].astype(str).str.upper().str.strip()
df["_RES_"]  = df[COL_RESULTADO].astype(str).str.upper().str.strip()

df["_CLASSE_"] = "OUTROS"
df.loc[df["_RES_"].str.contains("PROCED", na=False), "_CLASSE_"] = "PROCEDENTE"
df.loc[df["_RES_"].str.contains("IMPROCED", na=False), "_CLASSE_"] = "IMPROCEDENTE"

# Ano ref (pega o ano mais recente com data)
ano_ref = int(df[COL_DATA].dt.year.dropna().max()) if df[COL_DATA].notna().any() else None
df_ano = df if ano_ref is None else df[df[COL_DATA].dt.year == ano_ref].copy()

# ======================================================
# "ABAS" (UF) – como no print
# ======================================================
st.markdown("### ")
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

# Separação AM/AS
df_am = df_filtro[df_filtro["_TIPO_"].str.contains("AM", na=False)]
df_as = df_filtro[df_filtro["_TIPO_"].str.contains("AS", na=False)]

# ======================================================
# FUNÇÕES DE GRÁFICOS NO ESTILO DO PRINT
# ======================================================
COR_PROC = "#2e7d32"   # verde
COR_IMP  = "#c62828"   # vermelho
COR_OUT  = "#546e7a"   # cinza

def fig_acumulado_anual(df_base):
    # barras horizontais empilhadas AM/AS por classe
    if df_base.empty:
        return None

    base = df_base.copy()
    base["_TIPO2_"] = base["_TIPO_"].str.extract(r"(AM|AS)", expand=False).fillna(base["_TIPO_"])
    dados = base.groupby(["_TIPO2_", "_CLASSE_"]).size().reset_index(name="QTD")

    ordem_tipo = [t for t in ["AM", "AS"] if t in dados["_TIPO2_"].unique()]
    if not ordem_tipo:
        ordem_tipo = sorted(dados["_TIPO2_"].unique().tolist())

    fig = px.bar(
        dados, x="QTD", y="_TIPO2_", color="_CLASSE_", orientation="h",
        barmode="stack", text="QTD",
        category_orders={"_TIPO2_": ordem_tipo, "_CLASSE_": ["PROCEDENTE","IMPROCEDENTE","OUTROS"]},
        template="plotly_white",
        color_discrete_map={"PROCEDENTE": COR_PROC, "IMPROCEDENTE": COR_IMP, "OUTROS": COR_OUT}
    )
    fig.update_layout(height=240, margin=dict(l=10,r=10,t=10,b=10), legend_title_text="")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig

def fig_acumulado_mensal(df_base):
    # barras verticais empilhadas (procedente/improcedente) com % do procedente em cima + tabela
    base = df_base.dropna(subset=[COL_DATA]).copy()
    if base.empty:
        return None, None

    base["MES"] = base[COL_DATA].dt.month
    base["MES_LABEL"] = base[COL_DATA].dt.strftime("%B").str.upper()  # JANEIRO...
    # total do mês por classe
    dados = base.groupby(["MES","MES_LABEL","_CLASSE_"]).size().reset_index(name="QTD")
    dados = dados.sort_values("MES")

    # percent procedente por mês
    tot_mes = dados.groupby("MES")["QTD"].transform("sum")
    dados["PCT"] = (dados["QTD"] / tot_mes * 100).round(0)
    dados["LABEL"] = ""
    dados.loc[dados["_CLASSE_"]=="PROCEDENTE","LABEL"] = dados.loc[dados["_CLASSE_"]=="PROCEDENTE","PCT"].astype(int).astype(str) + "%"

    ordem_mes = dados[["MES","MES_LABEL"]].drop_duplicates().sort_values("MES")["MES_LABEL"].tolist()

    fig = px.bar(
        dados, x="MES_LABEL", y="QTD", color="_CLASSE_",
        barmode="stack", text="LABEL",
        category_orders={"MES_LABEL": ordem_mes, "_CLASSE_": ["PROCEDENTE","IMPROCEDENTE","OUTROS"]},
        template="plotly_white",
        color_discrete_map={"PROCEDENTE": COR_PROC, "IMPROCEDENTE": COR_IMP, "OUTROS": COR_OUT}
    )
    fig.update_layout(height=280, margin=dict(l=10,r=10,t=10,b=10), legend_title_text="")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")

    # tabela (procedente, improcedente, total)
    tab = dados.pivot_table(index=["MES","MES_LABEL"], columns="_CLASSE_", values="QTD", fill_value=0).reset_index()
    tab["TOTAL"] = tab.select_dtypes("number").sum(axis=1)
    tab = tab.sort_values("MES").drop(columns=["MES"]).rename(columns={"MES_LABEL":"MÊS"})
    # garante colunas
    for c in ["IMPROCEDENTE","PROCEDENTE","OUTROS"]:
        if c not in tab.columns:
            tab[c] = 0
    # ordem semelhante ao print
    tab = tab[["MÊS","IMPROCEDENTE","PROCEDENTE","TOTAL"]]

    return fig, tab

def fig_barh(df_base, col_dim, titulo):
    if col_dim is None or df_base.empty:
        return None
    dados = df_base.groupby(col_dim).size().reset_index(name="QTD").sort_values("QTD")
    if dados.empty:
        return None
    fig = px.bar(
        dados, x="QTD", y=col_dim, orientation="h", text="QTD",
        template="plotly_white", title=titulo
    )
    fig.update_layout(height=290, margin=dict(l=10,r=10,t=40,b=10), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig

# ... [imports e código anterior permanecem IGUAIS] ...

# ======================================================
# LAYOUT PRINCIPAL (igual ao print)
# ======================================================
top = st.columns([1.05, 1.15, 2.8], gap="large")

# KPI esquerdo
with top[0]:
    total = len(df_filtro)
    am = len(df_am)
    az = len(df_as)
    ano_txt = str(ano_ref) if ano_ref else "—"

    total_fmt = f"{total:,}".replace(",", ".")
    am_fmt    = f"{am:,}".replace(",", ".")
    as_fmt    = f"{az:,}".replace(",", ".")

    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">
            ACUMULADO DE NOTAS<br>
            AM / AS<br>{ano_txt}
          </div>
          <div style="text-align:center" class="kpi-big">{total_fmt}</div>
          <div class="kpi-sub">
            <div>
              <div class="lbl">AM</div>
              <div class="val">{am_fmt}</div>
            </div>
            <div>
              <div class="lbl">AS</div>
              <div class="val">{as_fmt}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ... [RESTO DO SCRIPT CONTINUA IGUAL AO QUE TE MANDEI]


# Acumulado anual
with top[1]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO ANUAL</div>', unsafe_allow_html=True)
    fig = fig_acumulado_anual(df_filtro)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        # percentuais gerais
        proc = (df_filtro["_CLASSE_"]=="PROCEDENTE").sum()
        imp  = (df_filtro["_CLASSE_"]=="IMPROCEDENTE").sum()
        tot  = max(1, proc+imp)
        st.caption(f"Procedente: **{proc}** ({proc/tot:.0%})  •  Improcedente: **{imp}** ({imp/tot:.0%})")
    else:
        st.info("Sem dados.")
    st.markdown("</div>", unsafe_allow_html=True)

# Acumulado mensal + tabela
with top[2]:
    st.markdown('<div class="card"><div class="card-title">ACUMULADO MENSAL DE NOTAS AM - AS</div>', unsafe_allow_html=True)
    fig_m, tab = fig_acumulado_mensal(df_filtro)
    if fig_m is not None:
        st.plotly_chart(fig_m, use_container_width=True)
        st.dataframe(tab, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados mensais (DATA vazia/ inválida).")
    st.markdown("</div>", unsafe_allow_html=True)

# Linha de baixo: 3 gráficos
bottom = st.columns(3, gap="large")

with bottom[0]:
    st.markdown('<div class="card"><div class="card-title">IMPROCEDÊNCIAS POR REGIONAL - NOTA AM</div>', unsafe_allow_html=True)
    base_imp_am = df_am[df_am["_CLASSE_"]=="IMPROCEDENTE"]
    fig = fig_barh(base_imp_am, COL_REGIONAL, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem improcedências (AM) por regional.")
    st.markdown("</div>", unsafe_allow_html=True)

with bottom[1]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS - NOTA AM</div>', unsafe_allow_html=True)
    base_imp_am = df_am[df_am["_CLASSE_"]=="IMPROCEDENTE"]
    fig = fig_barh(base_imp_am, COL_MOTIVO, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem motivos (AM).")
    st.markdown("</div>", unsafe_allow_html=True)

with bottom[2]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS - NOTAS AS</div>', unsafe_allow_html=True)
    base_imp_as = df_as[df_as["_CLASSE_"]=="IMPROCEDENTE"]
    fig = fig_barh(base_imp_as, COL_MOTIVO, " ")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem motivos (AS).")
    st.markdown("</div>", unsafe_allow_html=True)

# Exportação
st.markdown('<div class="card"><div class="card-title">EXPORTAR DADOS (FILTRO ATUAL)</div>', unsafe_allow_html=True)
st.download_button(
    label="⬇️ Baixar CSV",
    data=df_filtro.to_csv(index=False).encode("utf-8"),
    file_name="IW58_Dashboard.csv",
    mime="text/csv",
)
st.markdown("</div>", unsafe_allow_html=True)
