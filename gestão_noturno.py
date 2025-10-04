import pandas as pd
import plotly.express as px
import streamlit as st

# ================================
# 1️⃣ Upload e Validação do arquivo
# ================================
st.title("📊 Análise de Tempo Fora do Galpão")

uploaded_file = st.file_uploader("📂 Envie a planilha de entrada/saída", type=["xlsx"])

# Definir colunas obrigatórias
colunas_esperadas = {"Person", "Data", "Tempo Fora (h)"}

if uploaded_file is not None:
    try:
        df_resultado = pd.read_excel(uploaded_file)

        # Validação das colunas
        colunas_arquivo = set(df_resultado.columns)
        if colunas_arquivo != colunas_esperadas:
            st.error(
                f"❌ Arquivo inválido!\n\n"
                f"Colunas esperadas: {colunas_esperadas}\n"
                f"Colunas encontradas: {colunas_arquivo}"
            )
            st.stop()

        # Converter Data para datetime
        df_resultado["Data"] = pd.to_datetime(df_resultado["Data"])
        df_resultado["Dia da Semana"] = df_resultado["Data"].dt.day_name(locale="pt_BR")

        # ================================
        # 2️⃣ Ranking geral (todas as pessoas)
        # ================================
        df_ranking = (
            df_resultado.groupby("Person", as_index=False)["Tempo Fora (h)"]
            .sum()
            .sort_values(by="Tempo Fora (h)", ascending=False)
        )

        st.subheader("🏆 Ranking - Quem mais fica fora do galpão")
        fig_rank = px.bar(
            df_ranking,
            x="Person",
            y="Tempo Fora (h)",
            text="Tempo Fora (h)",
            color="Tempo Fora (h)",
            color_continuous_scale="Reds",
        )
        fig_rank.update_traces(texttemplate='%{text:.2f}h', textposition="outside")
        fig_rank.update_layout(yaxis_title="Horas Fora", xaxis_title="Pessoa")
        st.plotly_chart(fig_rank, use_container_width=True)

        # ================================
        # 3️⃣ Detalhe por dia da semana (filtrando uma pessoa)
        # ================================
        st.subheader("📊 Detalhe - Tempo fora por dia da semana")

        pessoa_selecionada = st.selectbox("Selecione uma pessoa:", df_ranking["Person"].unique())

        df_detalhe_semana = (
            df_resultado[df_resultado["Person"] == pessoa_selecionada]
            .groupby("Dia da Semana", as_index=False)["Tempo Fora (h)"]
            .sum()
            .sort_values(by="Tempo Fora (h)", ascending=False)
        )

        fig_semana = px.bar(
            df_detalhe_semana,
            x="Dia da Semana",
            y="Tempo Fora (h)",
            text="Tempo Fora (h)",
            color="Tempo Fora (h)",
            color_continuous_scale="Blues",
        )
        fig_semana.update_traces(texttemplate='%{text:.2f}h', textposition="outside")
        fig_semana.update_layout(yaxis_title="Horas Fora", xaxis_title="Dia da Semana")
        st.plotly_chart(fig_semana, use_container_width=True)

        # ================================
        # 4️⃣ (Extra) Visão geral por pessoa x dia da semana
        # ================================
        st.subheader("📊 Comparativo - Todas as pessoas por dia da semana")

        df_semana_todos = (
            df_resultado.groupby(["Person", "Dia da Semana"], as_index=False)["Tempo Fora (h)"]
            .sum()
        )

        fig_semana_todos = px.bar(
            df_semana_todos,
            x="Dia da Semana",
            y="Tempo Fora (h)",
            color="Person",
            barmode="group",
            text="Tempo Fora (h)"
        )
        fig_semana_todos.update_traces(texttemplate='%{text:.1f}h', textposition="outside")
        fig_semana_todos.update_layout(yaxis_title="Horas Fora", xaxis_title="Dia da Semana")
        st.plotly_chart(fig_semana_todos, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("⬆️ Por favor, envie o arquivo Excel para começar a análise.")
