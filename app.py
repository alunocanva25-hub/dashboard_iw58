import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(page_title="Dashboard IW58", layout="wide")

# ======================================================
# LOGIN
# ======================================================
def tela_login():
    st.markdown("## 🔐 Acesso Restrito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == st.secrets["auth"]["usuario"] and senha == st.secrets["auth"]["senha"]:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    tela_login()
    st.stop()

# ======================================================
# TÍTULO
# ======================================================
st.title("📊 Dashboard IW58 – AM x AS")

# ======================================================
# FUNÇÃO COLUNA
# ======================================================
def achar_coluna(df, palavras):
    for c in df.columns:
        for p in palavras:
            if p in c:
                return c
    return None

# ======================================================
# BASE (GOOGLE DRIVE)
# ======================================================
@st.cache_data
def carregar_base():
    url = "https://drive.google.com/uc?id=1WzXQVd7nwMKv02I2DLPNuMh4wK7bKQVO"
    df = pd.read_csv(url, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.upper().str.strip()
    return df

df = carregar_base()

# ======================================================
# COLUNAS
# ======================================================
COL_ESTADO = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO = achar_coluna(df, ["TIPO"])
COL_MOTIVO = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL = achar_coluna(df, ["REGIONAL"])
COL_DATA = achar_coluna(df, ["DATA"])

obrigatorias = [COL_ESTADO, COL_RESULTADO, COL_TIPO, COL_DATA]
if any(c is None for c in obrigatorias):
    st.error("❌ A base não contém todas as colunas obrigatórias.")
    st.stop()

# ======================================================
# DATA
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce")
df["MES_ANO"] = df[COL_DATA].dt.strftime("%b/%Y")

# ======================================================
# FILTRO ESTADO
# ======================================================
st.subheader("📍 Localidade")
estados = ["TOTAL"] + sorted(df[COL_ESTADO].dropna().unique().tolist())

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

cols = st.columns(len(estados))
for i, e in enumerate(estados):
    if cols[i].button(e):
        st.session_state.estado_sel = e

estado = st.session_state.estado_sel
df_filtro = df if estado == "TOTAL" else df[df[COL_ESTADO] == estado]

# ======================================================
# AM / AS
# ======================================================
df_am = df_filtro[df_filtro[COL_TIPO].astype(str).str.contains("AM", na=False)]
df_as = df_filtro[df_filtro[COL_TIPO].astype(str).str.contains("AS", na=False)]

# ======================================================
# KPIs
# ======================================================
k1, k2, k3 = st.columns(3)
k1.metric("Total Geral", len(df_filtro))
k2.metric("Total AM", len(df_am))
k3.metric("Total AS", len(df_as))

# ======================================================
# DONUT SEGURO
# ======================================================
def donut_seguro(df_base, titulo):
    if df_base.empty:
        st.info(f"Sem dados para {titulo}")
        return

    dados = (
        df_base[COL_RESULTADO]
        .dropna()
        .value_counts()
        .reset_index()
    )
    dados.columns = ["Resultado", "Quantidade"]

    fig = px.pie(
        dados,
        names="Resultado",
        values="Quantidade",
        hole=0.6,
        title=titulo,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    donut_seguro(df_am, f"AM – {estado}")
with c2:
    donut_seguro(df_as, f"AS – {estado}")

# ======================================================
# EXPORTAÇÃO (100% ESTÁVEL)
# ======================================================
st.subheader("📤 Exportar Dados")

def gerar_excel(df):
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

e1, e2 = st.columns(2)

with e1:
    st.download_button(
        "⬇️ Baixar CSV",
        df_filtro.to_csv(index=False).encode("utf-8"),
        "IW58_Dashboard.csv",
        "text/csv"
    )

with e2:
    st.download_button(
        "⬇️ Baixar Excel",
        gerar_excel(df_filtro),
        "IW58_Dashboard.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# TABELA
# ======================================================
st.subheader("📋 Base de Dados")
st.dataframe(df_filtro, use_container_width=True, height=300)
