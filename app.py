import streamlit as st
import pandas as pd
import plotly.express as px

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Dashboard IW58",
    layout="wide"
)

st.title("📊 Dashboard IW58 – AM x AS")

# ======================================================
# LINK DO CSV NO GOOGLE DRIVE (LINK DIRETO)
# ======================================================
URL_BASE = "https://drive.google.com/uc?id=1WzXQVd7nwMKv02I2DLPNuMh4wK7bKQVO"

# ======================================================
# FUNÇÃO PARA IDENTIFICAR COLUNAS AUTOMATICAMENTE
# ======================================================
def achar_coluna(df, palavras):
    for coluna in df.columns:
        for palavra in palavras:
            if palavra in coluna:
                return coluna
    return None

# ======================================================
# CARREGAMENTO DA BASE (COMPATÍVEL COM STREAMLIT CLOUD)
# ======================================================
@st.cache_data
def carregar_base():
    df = pd.read_csv(
        URL_BASE,
        sep=None,
        engine="python",
        encoding="utf-8-sig"
    )
    df.columns = df.columns.str.upper().str.strip()
    return df

df = carregar_base()

# ======================================================
# IDENTIFICAÇÃO DAS COLUNAS
# ======================================================
COL_ESTADO = achar_coluna(df, ["ESTADO", "UF", "LOCALIDADE"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO = achar_coluna(df, ["TIPO"])
COL_MOTIVO = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL = achar_coluna(df, ["REGIONAL"])
COL_DATA = achar_coluna(df, ["DATA"])

if not COL_ESTADO or not COL_RESULTADO or not COL_TIPO or not COL_DATA:
    st.error("❌ Colunas obrigatórias não encontradas na base.")
    st.stop()

# ======================================================
# TRATAMENTO DE DATA
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce")
df["MES_ANO"] = df[COL_DATA].dt.strftime("%m/%Y")

# ======================================================
# BOTÕES DE ESTADO
# ======================================================
st.subheader("📍 Estado")

estados = sorted(df[COL_ESTADO].dropna().unique().tolist())
estados = ["TOTAL"] + estados

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

cols = st.columns(len(estados))

for i, est in enumerate(estados):
    if cols[i].button(est):
        st.session_state.estado_sel = est

estado_selecionado = st.session_state.estado_sel

# ======================================================
# FILTRO POR ESTADO
# ======================================================
if estado_selecionado == "TOTAL":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df[COL_ESTADO] == estado_selecionado]

# ======================================================
# SEPARAÇÃO AM / AS
# ======================================================
df_am = df_filtrado[df_filtrado[COL_TIPO].str.contains("AM", na=False)]
df_as = df_filtrado[df_filtrado[COL_TIPO].str.contains("AS", na=False)]

# ======================================================
# KPIs
# ======================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Total Geral", len(df_filtrado))
with c2:
    st.metric("Total AM", len(df_am))
with c3:
    st.metric("Total AS", len(df_as))

# ======================================================
# FUNÇÃO – DONUT PROCEDENTE x IMPROCEDENTE
# ======================================================
def grafico_resultado(df_base, titulo):
    proc = df_base[COL_RESULTADO].str.contains("PROCEDENTE", na=False).sum()
    improc = df_base[COL_RESULTADO].str.contains("IMPROCEDENTE", na=False).sum()

    dados = pd.DataFrame({
        "Resultado": ["Procedente", "Improcedente"],
        "Quantidade": [proc, improc]
    })

    fig = px.pie(
        dados,
        names="Resultado",
        values="Quantidade",
        hole=0.6,
        title=titulo,
        template="plotly_dark"
    )

    fig.update_traces(textinfo="percent+value")
    return fig

# ======================================================
# DONUTS
# ======================================================
c4, c5 = st.columns(2)

with c4:
    st.plotly_chart(
        grafico_resultado(df_am, f"AM – {estado_selecionado}"),
        use_container_width=True
    )

with c5:
    st.plotly_chart(
        grafico_resultado(df_as, f"AS – {estado_selecionado}"),
        use_container_width=True
    )

# ======================================================
# FUNÇÃO – MOTIVOS
# ======================================================
def grafico_motivos(df_base, titulo):
    if not COL_MOTIVO:
        return None

    dados = (
        df_base
        .groupby(COL_MOTIVO)
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )

    dados["Percentual"] = (dados["Quantidade"] / dados["Quantidade"].sum() * 100).round(1)
    dados["Label"] = dados["Quantidade"].astype(str) + " (" + dados["Percentual"].astype(str) + "%)"

    fig = px.bar(
        dados,
        x="Quantidade",
        y=COL_MOTIVO,
        orientation="h",
        text="Label",
        title=titulo,
        template="plotly_dark"
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig

# ======================================================
# MOTIVOS
# ======================================================
c6, c7 = st.columns(2)

with c6:
    fig = grafico_motivos(df_am, f"Motivos – AM ({estado_selecionado})")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

with c7:
    fig = grafico_motivos(df_as, f"Motivos – AS ({estado_selecionado})")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ======================================================
# FUNÇÃO – AM x AS POR MÊS (VALOR + %)
# ======================================================
def grafico_am_as_mensal(df_base):
    dados = (
        df_base
        .groupby(["MES_ANO", COL_TIPO])
        .size()
        .reset_index(name="Quantidade")
    )

    total_mes = (
        dados
        .groupby("MES_ANO")["Quantidade"]
        .sum()
        .reset_index(name="TOTAL_MES")
    )

    dados = dados.merge(total_mes, on="MES_ANO")
    dados["Percentual"] = (dados["Quantidade"] / dados["TOTAL_MES"] * 100).round(1)
    dados["Label"] = dados["Quantidade"].astype(str) + " (" + dados["Percentual"].astype(str) + "%)"

    fig = px.bar(
        dados,
        x="MES_ANO",
        y="Quantidade",
        color=COL_TIPO,
        barmode="group",
        text="Label",
        title="AM x AS por Mês",
        template="plotly_dark"
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Quantidade",
        uniformtext_minsize=8,
        uniformtext_mode="hide"
    )

    return fig

# ======================================================
# EVOLUÇÃO MENSAL
# ======================================================
st.subheader("📅 Evolução Mensal")

st.plotly_chart(
    grafico_am_as_mensal(df_filtrado),
    use_container_width=True
)

# ======================================================
# BASE FINAL
# ======================================================
st.subheader("📋 Base de Dados")
st.dataframe(df_filtrado, use_container_width=True, height=300)
