import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Dashboard Notas – AM x AS",
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
st.title("📊 Dashboard Notas – AM x AS")

# ======================================================
# FUNÇÕES UTILITÁRIAS
# ======================================================
def achar_coluna(df, palavras):
    for coluna in df.columns:
        for palavra in palavras:
            if palavra in coluna:
                return coluna
    return None

def validar_estrutura(df):
    obrigatorias = {
        "ESTADO": ["ESTADO", "LOCALIDADE", "UF"],
        "RESULTADO": ["RESULTADO"],
        "TIPO": ["TIPO"],
        "DATA": ["DATA"]
    }

    erros = []
    for nome, alternativas in obrigatorias.items():
        if not achar_coluna(df, alternativas):
            erros.append(f"❌ Coluna obrigatória não encontrada: {nome}")

    if erros:
        st.error("Problemas encontrados na estrutura da base:")
        for e in erros:
            st.write(e)
        st.stop()

# ======================================================
# CACHE ROBUSTO + GOOGLE DRIVE
# ======================================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando base de dados...")
def carregar_base(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    raw = r.content
    head = raw[:300].lstrip().lower()

    # Se o Drive retornar HTML (permissão/link errado)
    if head.startswith(b"<!doctype html") or b"<html" in head:
        raise RuntimeError(
            "O link do Google Drive não está retornando o CSV.\n"
            "Verifique se o arquivo está compartilhado como:\n"
            "'Qualquer pessoa com o link → Visualizador'\n"
            "e se o link está no formato:\n"
            "https://drive.google.com/uc?id=SEU_ID"
        )

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=enc)
            df.columns = df.columns.str.upper().str.strip()
            return df
        except UnicodeDecodeError:
            continue

    # fallback final
    df = pd.read_csv(
        BytesIO(raw),
        sep=None,
        engine="python",
        encoding="utf-8",
        encoding_errors="replace"
    )
    df.columns = df.columns.str.upper().str.strip()

    st.warning(
        "⚠️ O arquivo não está em UTF-8. "
        "Caracteres inválidos foram substituídos."
    )
    return df

# ======================================================
# BOTÃO ATUALIZAR BASE
# ======================================================
if st.button("🔄 Atualizar base"):
    st.cache_data.clear()
    st.rerun()

# ======================================================
# CARREGAMENTO DA BASE
# ======================================================
URL_BASE = "https://drive.google.com/uc?id=1xg5D9tAqhy0DlX7uu6X8e2BsQku1KOs7"
df = carregar_base(URL_BASE)

# ======================================================
# VALIDAÇÃO DA BASE
# ======================================================
validar_estrutura(df)

# ======================================================
# IDENTIFICAÇÃO DAS COLUNAS
# ======================================================
COL_ESTADO = achar_coluna(df, ["ESTADO", "LOCALIDADE", "UF"])
COL_RESULTADO = achar_coluna(df, ["RESULTADO"])
COL_TIPO = achar_coluna(df, ["TIPO"])
COL_MOTIVO = achar_coluna(df, ["MOTIVO"])
COL_REGIONAL = achar_coluna(df, ["REGIONAL"])
COL_DATA = achar_coluna(df, ["DATA"])

# ======================================================
# TRATAMENTO DE DATA
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce")
df = df.dropna(subset=[COL_DATA])

df["MES"] = df[COL_DATA].dt.month
df["ANO"] = df[COL_DATA].dt.year
df["MES_ANO"] = df[COL_DATA].dt.strftime("%b/%Y")

# ======================================================
# FILTRO POR ESTADO
# ======================================================
st.subheader("📍 Localidade")

estados = sorted(df[COL_ESTADO].dropna().astype(str).unique().tolist())
estados = ["TOTAL"] + estados

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

cols = st.columns(len(estados))
for i, est in enumerate(estados):
    if cols[i].button(est):
        st.session_state.estado_sel = est

estado = st.session_state.estado_sel
df_filtro = df if estado == "TOTAL" else df[df[COL_ESTADO] == estado]

# ======================================================
# SEPARAÇÃO AM / AS
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
def donut_resultado(df_base, titulo):
    proc = df_base[COL_RESULTADO].str.contains("PROCEDENTE", na=False).sum()
    improc = df_base[COL_RESULTADO].str.contains("IMPROCEDENTE", na=False).sum()

    dados = pd.DataFrame({
        "Resultado": ["Procedente", "Improcedente"],
        "Quantidade": [proc, improc]
    })

    return px.pie(
        dados,
        names="Resultado",
        values="Quantidade",
        hole=0.6,
        title=titulo,
        template="plotly_dark"
    )

c1, c2 = st.columns(2)
c1.plotly_chart(donut_resultado(df_am, f"AM – {estado}"), use_container_width=True)
c2.plotly_chart(donut_resultado(df_as, f"AS – {estado}"), use_container_width=True)

# ======================================================
# MOTIVOS
# ======================================================
def grafico_motivos(df_base, titulo):
    if not COL_MOTIVO:
        return None

    dados = (
        df_base.groupby(COL_MOTIVO)
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

c3, c4 = st.columns(2)
c3.plotly_chart(grafico_motivos(df_am, f"Motivos AM – {estado}"), use_container_width=True)
c4.plotly_chart(grafico_motivos(df_as, f"Motivos AS – {estado}"), use_container_width=True)

# ======================================================
# IMPROCEDENTE POR REGIONAL
# ======================================================
def improcedente_regional(df_base, titulo):
    if not COL_REGIONAL:
        return None

    base = df_base[df_base[COL_RESULTADO].str.contains("IMPROCEDENTE", na=False)]
    dados = (
        base.groupby(COL_REGIONAL)
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )

    fig = px.bar(
        dados,
        x="Quantidade",
        y=COL_REGIONAL,
        orientation="h",
        text="Quantidade",
        title=titulo,
        template="plotly_dark"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig

c5, c6 = st.columns(2)
c5.plotly_chart(improcedente_regional(df_am, f"Improcedente Regional AM – {estado}"), use_container_width=True)
c6.plotly_chart(improcedente_regional(df_as, f"Improcedente Regional AS – {estado}"), use_container_width=True)

# ======================================================
# EVOLUÇÃO MENSAL
# ======================================================
def evolucao_mensal(df_base):
    dados = (
        df_base.groupby(["MES_ANO", COL_TIPO])
        .size()
        .reset_index(name="Quantidade")
        .sort_values("MES_ANO")
    )

    total_mes = dados.groupby("MES_ANO")["Quantidade"].transform("sum")
    dados["Percentual"] = (dados["Quantidade"] / total_mes * 100).round(1)
    dados["Label"] = dados["Quantidade"].astype(str) + " (" + dados["Percentual"].astype(str) + "%)"

    fig = px.bar(
        dados,
        x="MES_ANO",
        y="Quantidade",
        color=COL_TIPO,
        barmode="group",
        text="Label",
        title="📅 AM x AS por Mês",
        template="plotly_dark"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Mês", yaxis_title="Quantidade")
    re
