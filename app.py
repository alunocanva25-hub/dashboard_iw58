import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Dashboard IW58",
    layout="wide"
)

# ======================================================
# LOGIN
# ======================================================
def tela_login():
    st.markdown("## 🔐 Acesso Restrito")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if (
            usuario == st.secrets["auth"]["usuario"]
            and senha == st.secrets["auth"]["senha"]
        ):
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
# TÍTULO
# ======================================================
st.title("📊 Dashboard IW58 – AM x AS")

# ======================================================
# FUNÇÃO PARA IDENTIFICAR COLUNAS
# ======================================================
def achar_coluna(df, palavras):
    for coluna in df.columns:
        for palavra in palavras:
            if palavra in coluna:
                return coluna
    return None

# ======================================================
# CARREGAMENTO DA BASE (GOOGLE DRIVE)
# ======================================================
@st.cache_data
def carregar_base():
    url = "https://drive.google.com/uc?id=1WzXQVd7nwMKv02I2DLPNuMh4wK7bKQVO"
    df = pd.read_csv(url, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.upper().str.strip()
    return df

df = carregar_base()

# ======================================================
# IDENTIFICAÇÃO DAS COLUNAS
# ======================================================
COL_ESTADO = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO = achar_coluna(df, ["TIPO"])
COL_MOTIVO = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL = achar_coluna(df, ["REGIONAL"])
COL_DATA = achar_coluna(df, ["DATA"])

if not all([COL_ESTADO, COL_RESULTADO, COL_TIPO, COL_DATA]):
    st.error("❌ Colunas obrigatórias não encontradas na base.")
    st.stop()

# ======================================================
# DATA
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce")
df["MES_ANO"] = df[COL_DATA].dt.strftime("%b/%Y")

# ======================================================
# FILTRO POR ESTADO
# ======================================================
st.subheader("📍 Localidade")

estados = ["TOTAL"] + sorted(df[COL_ESTADO].dropna().unique().tolist())

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

cols = st.columns(len(estados))
for i, est in enumerate(estados):
    if cols[i].button(est):
        st.session_state.estado_sel = est

estado = st.session_state.estado_sel
df_filtro = df if estado == "TOTAL" else df[df[COL_ESTADO] == estado]

# ======================================================
# AM / AS
# ======================================================
df_am = df_filtro[df_filtro[COL_TIPO].str.contains("AM", na=False)]
df_as = df_filtro[df_filtro[COL_TIPO].str.contains("AS", na=False)]

# ======================================================
# KPIs
# ======================================================
k1, k2, k3 = st.columns(3)
k1.metric("Total Geral", len(df_filtro))
k2.metric("Total AM", len(df_am))
k3.metric("Total AS", len(df_as))

# ======================================================
# DONUT RESULTADO
# ======================================================
def donut(df_base, titulo):
    dados = df_base[COL_RESULTADO].value_counts().reset_index()
    dados.columns = ["Resultado", "Quantidade"]

    return px.pie(
        dados,
        names="Resultado",
        values="Quantidade",
        hole=0.6,
        title=titulo,
        template="plotly_dark"
    )

c1, c2 = st.columns(2)
c1.plotly_chart(donut(df_am, f"AM – {estado}"), use_container_width=True)
c2.plotly_chart(donut(df_as, f"AS – {estado}"), use_container_width=True)

# ======================================================
# MOTIVOS
# ======================================================
def grafico_motivos(df_base, titulo):
    if not COL_MOTIVO:
        return None

    dados = df_base[COL_MOTIVO].value_counts().reset_index()
    dados.columns = [COL_MOTIVO, "Quantidade"]

    return px.bar(
        dados,
        x="Quantidade",
        y=COL_MOTIVO,
        orientation="h",
        title=titulo,
        template="plotly_dark",
        text="Quantidade"
    )

c3, c4 = st.columns(2)
c3.plotly_chart(grafico_motivos(df_am, f"Motivos AM – {estado}"), use_container_width=True)
c4.plotly_chart(grafico_motivos(df_as, f"Motivos AS – {estado}"), use_container_width=True)

# ======================================================
# EVOLUÇÃO MENSAL
# ======================================================
dados_mensal = (
    df_filtro
    .groupby(["MES_ANO", COL_TIPO])
    .size()
    .reset_index(name="Quantidade")
)

fig_mensal = px.bar(
    dados_mensal,
    x="MES_ANO",
    y="Quantidade",
    color=COL_TIPO,
    barmode="group",
    text="Quantidade",
    title="📅 AM x AS por Mês",
    template="plotly_dark"
)

fig_mensal.update_traces(textposition="outside")
st.plotly_chart(fig_mensal, use_container_width=True)

# ======================================================
# EXPORTAÇÃO (VERSÃO DEFINITIVA)
# ======================================================
st.subheader("📤 Exportar Dados")

def gerar_excel(df):
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

c_exp1, c_exp2 = st.columns(2)

with c_exp1:
    st.download_button(
        "⬇️ Baixar CSV",
        data=df_filtro.to_csv(index=False).encode("utf-8"),
        file_name="IW58_Dashboard.csv",
        mime="text/csv"
    )

with c_exp2:
    st.download_button(
        "⬇️ Baixar Excel",
        data=gerar_excel(df_filtro),
        file_name="IW58_Dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# TABELA FINAL
# ======================================================
st.subheader("📋 Base de Dados")
st.dataframe(df_filtro, use_container_width=True, height=300)
