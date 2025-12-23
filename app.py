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
# CSS (ALTERAÇÃO 2 – centralizar gráficos)
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
}

.plotly-container {
  display: flex;
  justify-content: center;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# FUNÇÕES
# ======================================================
def achar_coluna(df, palavras):
    for c in df.columns:
        for p in palavras:
            if p in c:
                return c
    return None

def _extrair_sheet_id(url):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _extrair_drive_id(url):
    m = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", url)
    if m: return m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _normalizar_para_csv(url):
    sid = _extrair_sheet_id(url)
    if sid:
        return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid=0"
    did = _extrair_drive_id(url)
    if did:
        return f"https://drive.google.com/uc?id={did}"
    return url

@st.cache_data(ttl=600)
def carregar_base(url):
    url = _normalizar_para_csv(url)
    raw = requests.get(url, timeout=30).content
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

def barh_contagem(df_base, col, titulo):
    if df_base.empty or col is None:
        return None

    dados = df_base.groupby(col).size().reset_index(name="QTD").sort_values("QTD")

    fig = px.bar(
        dados,
        x="QTD",
        y=col,
        orientation="h",
        text="QTD",
        title=titulo,
        template="plotly_white"
    )

    # ======================================================
    # ALTERAÇÃO 3 – margens corrigidas (centralização visual)
    # ======================================================
    fig.update_layout(
        height=300,
        margin=dict(l=80, r=30, t=45, b=10),
        showlegend=False
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig

# ======================================================
# CARREGAMENTO
# ======================================================
URL_BASE = "https://drive.google.com/uc?id=1NteTwRrAnnpOCVZH6mlassTzeWKsOdYY"
df = carregar_base(URL_BASE)

COL_ESTADO    = achar_coluna(df, ["ESTADO", "UF", "LOCALIDADE"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO      = achar_coluna(df, ["TIPO"])
COL_MOTIVO    = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL  = achar_coluna(df, ["REGIONAL"])
COL_DATA      = achar_coluna(df, ["DATA"])

df["_RES_"]  = df[COL_RESULTADO].astype(str).str.upper()
df["_TIPO_"] = df[COL_TIPO].astype(str).str.upper()

df_am = df[df["_TIPO_"].str.contains("AM", na=False)]
df_as = df[df["_TIPO_"].str.contains("AS", na=False)]

# ======================================================
# LINHA 2 – ALTERAÇÃO 1 (larguras ajustadas)
# ======================================================
row2 = st.columns([1, 1.6, 0.9], gap="large")

with row2[0]:
    st.markdown('<div class="card"><div class="card-title">IMPROCEDÊNCIAS POR REGIONAL – NOTA AM</div>', unsafe_allow_html=True)
    base = df_am[df_am["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base, COL_REGIONAL, "")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")
    st.markdown("</div>", unsafe_allow_html=True)

with row2[1]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTA AM</div>', unsafe_allow_html=True)
    base = df_am[df_am["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base, COL_MOTIVO, "")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")
    st.markdown("</div>", unsafe_allow_html=True)

with row2[2]:
    st.markdown('<div class="card"><div class="card-title">MOTIVOS DE IMPROCEDÊNCIAS – NOTAS AS</div>', unsafe_allow_html=True)
    base = df_as[df_as["_RES_"].str.contains("IMPROCED", na=False)]
    fig = barh_contagem(base, COL_MOTIVO, "")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")
    st.markdown("</div>", unsafe_allow_html=True)
