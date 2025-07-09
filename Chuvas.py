import streamlit as st
import pandas as pd
from unidecode import unidecode
import io

st.set_page_config(page_title="Organograma Diário", layout="wide")
st.title("📂 Sistema de Equipes - Importação e Visualização")

# ———————————————————————————
# 1. Mapeamento flexível de colunas
colunas_esperadas = {
    "data":        ["data"],
    "nome":        ["nome"],
    "funcao":      ["função", "funcao", "cargo"],
    "encarregado": ["encarregado", "responsavel", "líder"],
    "supervisor":  ["supervisor", "gestor", "coordenador"]
}

def mapear_colunas(df: pd.DataFrame) -> dict:
    mapeamento = {}
    atuais = [unidecode(c.lower().strip()) for c in df.columns]
    for chave, sin in colunas_esperadas.items():
        for i, col_norm in enumerate(atuais):
            if any(col_norm.startswith(s) for s in sin):
                mapeamento[chave] = df.columns[i]
                break
    return mapeamento

# ———————————————————————————
# 2. Geração do código DOT com clusters e layout LR
def gerar_dot_clusters(df: pd.DataFrame) -> str:
    dot  = 'digraph Organograma {\n'
    dot += '  rankdir=LR;\n'
    dot += '  compound=true;\n'
    dot += '  node [fontname="Helvetica", style=filled];\n\n'

    supervisors = df["supervisor"].unique().tolist()
    for idx, sup in enumerate(supervisors):
        dot += f'  subgraph cluster_{idx} {{\n'
        dot += f'    label="{sup}";\n'
        dot += f'    "{sup}" [shape=oval, fillcolor="#F5A9A9"];\n'

        df_sup = df[df["supervisor"] == sup]
        encarregados = df_sup["encarregado"].unique().tolist()
        for enc in encarregados:
            dot += f'    "{enc}" [shape=box, fillcolor="#F3F781"];\n'
            dot += f'    "{sup}" -> "{enc}" lhead="cluster_{idx}";\n'

            for _, row in df_sup[df_sup["encarregado"] == enc].iterrows():
                nome = row["nome"]
                func = row["funcao"]
                label = nome.replace('"','\\"') + "\\n" + func.replace('"','\\"')
                dot += f'    "{nome}" [shape=box, fillcolor="#A9D0F5", label="{label}"];\n'
                dot += f'    "{enc}" -> "{nome}" lhead="cluster_{idx}";\n'

        dot += '  }\n\n'

    dot += '}\n'
    return dot

# ———————————————————————————
# 3. Fluxo de UI
modo = st.sidebar.radio("📌 Menu", ["📥 Importar Planilha", "📊 Visualizar Organograma"])

if modo == "📥 Importar Planilha":
    st.subheader("📥 Importação de Equipes via Planilha")
    plan = st.file_uploader("Envie um .xlsx com: Data, Nome, Função, Encarregado, Supervisor", type=["xlsx"])
    if plan:
        df_raw = pd.read_excel(plan)
        m = mapear_colunas(df_raw)
        obrig = ["data","nome","funcao","encarregado","supervisor"]
        if not all(c in m for c in obrig):
            st.error("❌ A planilha precisa ter colunas que correspondam a: Data, Nome, Função, Encarregado e Supervisor.")
        else:
            # renomeia para padrão interno e padroniza data
            df = df_raw.rename(columns={v:k for k,v in m.items()})
            df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.success("✅ Planilha carregada com sucesso!")
            st.dataframe(df)
            st.session_state["df_equipes"] = df

elif modo == "📊 Visualizar Organograma":
    st.subheader("📊 Organograma por Data")
    if "df_equipes" not in st.session_state:
        st.warning("⚠️ Carregue uma planilha primeiro na aba 'Importar Planilha'.")
    else:
        df_tot = st.session_state["df_equipes"]
        datas  = sorted(df_tot["data"].unique(), reverse=True)
        data_sel = st.selectbox("Selecione a data:", datas)
        df_sel   = df_tot[df_tot["data"] == data_sel]

        if df_sel.empty:
            st.warning("⚠️ Nenhum registro para essa data.")
        else:
            st.markdown(f"### 👥 Organograma do dia {data_sel}")
            dot = gerar_dot_clusters(df_sel)
            st.graphviz_chart(dot, use_container_width=True)

            # botão de exportação Excel
            buffer = io.BytesIO()
            df_sel.to_excel(buffer, index=False, sheet_name="Equipe")
            buffer.seek(0)
            st.download_button(
                "📥 Exportar Excel",
                data=buffer,
                file_name=f"equipe_{data_sel.replace('/','-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
