import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re
from io import BytesIO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(page_title="Dashboard Notas – AM x AS", layout="wide")

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
        "ESTADO/UF": ["ESTADO", "LOCALIDADE", "UF"],
        "RESULTADO": ["RESULTADO"],
        "TIPO": ["TIPO"],
        "DATA": ["DATA"],
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

def _extrair_sheet_id(url: str) -> str | None:
    # https://docs.google.com/spreadsheets/d/<ID>/edit...
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _extrair_drive_id(url: str) -> str | None:
    # suporta ...uc?id=<ID> ou .../file/d/<ID>/view
    m = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def _normalizar_para_csv(url: str) -> str:
    """
    Se for Google Sheets -> converte para export CSV.
    Se for Drive file -> mantém como download direto (uc?id=).
    """
    sheet_id = _extrair_sheet_id(url)
    if sheet_id:
        # gid=0 (primeira aba). Se você tiver outra aba, troque o gid.
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

    drive_id = _extrair_drive_id(url)
    if drive_id:
        return f"https://drive.google.com/uc?id={drive_id}"

    return url  # fallback

# ======================================================
# CACHE ROBUSTO + LEITURA
# ======================================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando base de dados...")
def carregar_base(url_original: str) -> tuple[pd.DataFrame, dict]:
    url = _normalizar_para_csv(url_original)

    r = requests.get(url, timeout=45)
    r.raise_for_status()

    raw = r.content
    info = {
        "url_usada": url,
        "status": r.status_code,
        "content_type": r.headers.get("Content-Type", ""),
        "bytes": len(raw),
    }

    head = raw[:400].lstrip().lower()

    # Se vier HTML, não é CSV (permissão/link errado ou não exportou)
    if head.startswith(b"<!doctype html") or b"<html" in head:
        raise RuntimeError(
            "A URL não retornou CSV (retornou HTML). "
            "Se for Google Sheets, use link da planilha (eu converto). "
            "Se for Drive, garanta compartilhamento 'Qualquer pessoa com o link – Visualizador'."
        )

    # tenta encodings comuns
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    last_exc = None
    for enc in encodings:
        try:
            df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=enc)
            df.columns = df.columns.str.upper().str.strip()
            return df, info
        except UnicodeDecodeError as e:
            last_exc = e
            continue

    # fallback final
    try:
        df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding="utf-8", encoding_errors="replace")
        df.columns = df.columns.str.upper().str.strip()
        info["encoding_fallback"] = "utf-8 replace"
        return df, info
    except Exception as e:
        raise RuntimeError(f"Falha ao ler CSV. Último erro: {last_exc or e}")

# ======================================================
# BOTÃO ATUALIZAR BASE
# ======================================================
if st.button("🔄 Atualizar base"):
    st.cache_data.clear()
    st.rerun()

# ======================================================
# FONTE
# ======================================================
# Pode ser link do Drive OU link da planilha Google Sheets (qualquer um)
URL_BASE = "https://drive.google.com/uc?id=1NteTwRrAnnpOCVZH6mlassTzeWKsOdYY"
df, meta = carregar_base(URL_BASE)

# ======================================================
# DIAGNÓSTICO (mostra por que vinha 100)
# ======================================================
with st.expander("🧪 Diagnóstico da Base"):
    st.write("URL usada:", meta["url_usada"])
    st.write("Content-Type:", meta["content_type"])
    st.write("Tamanho (bytes):", meta["bytes"])
    st.write("Linhas lidas:", len(df))
    st.write("Colunas:", df.columns.tolist()[:30])

# ======================================================
# VALIDAÇÃO
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
# TRATAMENTO DE DATA (não derruba linhas)
# ======================================================
df[COL_DATA] = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=True)
df["MES"] = df[COL_DATA].dt.month
df["ANO"] = df[COL_DATA].dt.year
df["MES_ANO"] = df[COL_DATA].dt.strftime("%b/%Y")

# ======================================================
# FILTRO POR ESTADO (grid pra não quebrar)
# ======================================================
st.subheader("📍 Localidade")

estados = sorted(df[COL_ESTADO].dropna().astype(str).unique().tolist())
estados = ["TOTAL"] + estados

if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "TOTAL"

per_row = 8
for start in range(0, len(estados), per_row):
    row = st.columns(min(per_row, len(estados) - start))
    for i, est in enumerate(estados[start:start + per_row]):
        if row[i].button(est):
            st.session_state.estado_sel = est

estado = st.session_state.estado_sel
df_filtro = df if estado == "TOTAL" else df[df[COL_ESTADO].astype(str) == estado]

# ======================================================
# SEPARAÇÃO AM / AS
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
# DONUT RESULTADO
# ======================================================
def donut_resultado(df_base, titulo):
    proc = df_base[COL_RESULTADO].astype(str).str.contains("PROCEDENTE", na=False).sum()
    improc = df_base[COL_RESULTADO].astype(str).str.contains("IMPROCEDENTE", na=False).sum()

    dados = pd.DataFrame({"Resultado": ["Procedente", "Improcedente"], "Quantidade": [proc, improc]})

    return px.pie(
        dados, names="Resultado", values="Quantidade",
        hole=0.6, title=titulo, template="plotly_dark"
    )

c1, c2 = st.columns(2)
c1.plotly_chart(donut_resultado(df_am, f"AM – {estado}"), use_container_width=True)
c2.plotly_chart(donut_resultado(df_as, f"AS – {estado}"), use_container_width=True)

# ======================================================
# MOTIVOS (BARRAS)
# ======================================================
def grafico_motivos(df_base, titulo):
    if not COL_MOTIVO:
        return None

    dados = (
        df_base.groupby(COL_MOTIVO).size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )
    if dados.empty:
        return None

    dados["Percentual"] = (dados["Quantidade"] / dados["Quantidade"].sum() * 100).round(1)
    dados["Label"] = dados["Quantidade"].astype(str) + " (" + dados["Percentual"].astype(str) + "%)"

    fig = px.bar(
        dados, x="Quantidade", y=COL_MOTIVO, orientation="h",
        text="Label", title=titulo, template="plotly_dark"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig

c3, c4 = st.columns(2)
fig_m_am = grafico_motivos(df_am, f"Motivos AM – {estado}")
fig_m_as = grafico_motivos(df_as, f"Motivos AS – {estado}")

c3.plotly_chart(fig_m_am, use_container_width=True) if fig_m_am is not None else c3.info("Sem dados de motivos (AM).")
c4.plotly_chart(fig_m_as, use_container_width=True) if fig_m_as is not None else c4.info("Sem dados de motivos (AS).")

# ======================================================
# IMPROCEDENTE POR REGIONAL
# ======================================================
def improcedente_regional(df_base, titulo):
    if not COL_REGIONAL:
        return None

    base = df_base[df_base[COL_RESULTADO].astype(str).str.contains("IMPROCEDENTE", na=False)]
    if base.empty:
        return None

    dados = (
        base.groupby(COL_REGIONAL).size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade")
    )

    fig = px.bar(
        dados, x="Quantidade", y=COL_REGIONAL, orientation="h",
        text="Quantidade", title=titulo, template="plotly_dark"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig

c5, c6 = st.columns(2)
fig_r_am = improcedente_regional(df_am, f"Improcedente Regional AM – {estado}")
fig_r_as = improcedente_regional(df_as, f"Improcedente Regional AS – {estado}")

c5.plotly_chart(fig_r_am, use_container_width=True) if fig_r_am is not None else c5.info("Sem improcedência (AM) por regional.")
c6.plotly_chart(fig_r_as, use_container_width=True) if fig_r_as is not None else c6.info("Sem improcedência (AS) por regional.")

# ======================================================
# EVOLUÇÃO MENSAL (só com DATA válida)
# ======================================================
def evolucao_mensal(df_base):
    base = df_base.dropna(subset=[COL_DATA]).copy()
    if base.empty:
        return None

    base["MES_ANO"] = base[COL_DATA].dt.strftime("%b/%Y")

    dados = (
        base.groupby(["MES_ANO", COL_TIPO]).size()
        .reset_index(name="Quantidade")
        .sort_values("MES_ANO")
    )
    if dados.empty:
        return None

    total_mes = dados.groupby("MES_ANO")["Quantidade"].transform("sum")
    dados["Percentual"] = (dados["Quantidade"] / total_mes * 100).round(1)
    dados["Label"] = dados["Quantidade"].astype(str) + " (" + dados["Percentual"].astype(str) + "%)"

    fig = px.bar(
        dados, x="MES_ANO", y="Quantidade", color=COL_TIPO,
        barmode="group", text="Label",
        title="📅 AM x AS por Mês", template="plotly_dark"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Mês", yaxis_title="Quantidade")
    return fig

st.subheader("📅 Evolução Mensal")
fig_mensal = evolucao_mensal(df_filtro)
st.plotly_chart(fig_mensal, use_container_width=True) if fig_mensal is not None else st.info("Sem dados para evolução mensal (DATA vazia/ inválida).")

# ======================================================
# EXPORTAÇÃO
# ======================================================
st.subheader("📤 Exportar Dados")
st.download_button(
    label="⬇️ Baixar CSV",
    data=df_filtro.to_csv(index=False).encode("utf-8"),
    file_name="IW58_Dashboard.csv",
    mime="text/csv"
)
