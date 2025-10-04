import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Análise de Tempo Fora do Galpão", layout="wide")

st.title("📊 Análise de Tempo Fora do Galpão")

# ================================
# 1️⃣ Upload do arquivo CSV ou Excel
# ================================
uploaded_file = st.file_uploader("📂 Envie a planilha de entrada/saída", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Leitura do arquivo
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Converter coluna Time para datetime
        df['Time'] = pd.to_datetime(df['Time'])

        # Filtrar apenas eventos de Entrada e Saída
        df = df[df['Entered/Exited Status'].isin(['Entered', 'Exited'])]

        # Ordenar por Pessoa e Horário
        df = df.sort_values(['Person', 'Time'])

        # Calcular Tempo Fora (h) por pessoa
        tempo_fora = []

        for pessoa, grupo in df.groupby('Person'):
            total_horas = 0
            stack = []
            for _, row in grupo.iterrows():
                if row['Entered/Exited Status'] == 'Exited':
                    stack.append(row['Time'])
                elif row['Entered/Exited Status'] == 'Entered' and stack:
                    saida = stack.pop()
                    delta = row['Time'] - saida
                    total_horas += delta.total_seconds() / 3600
            tempo_fora.append({'Person': pessoa, 'Tempo Fora (h)': total_horas})

        df_resultado = pd.DataFrame(tempo_fora)

        # Adicionar Data fictícia (para compatibilidade com seus gráficos por dia da semana)
        df_resultado['Data'] = pd.Timestamp.today()

        # Criar coluna Dia da Semana em português
        dias_pt = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        df_resultado["Dia da Semana"] = df_resultado["Data"].dt.day_name().map(dias_pt)

        # ================================
        # 2️⃣ Ranking geral (todas as pessoas)
        # ================================
        df_ranking = df_resultado.sort_values('Tempo Fora (h)', ascending=False)

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
        # 4️⃣ Comparativo - Todas as pessoas por dia da semana
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
    st.info("⬆️ Por favor, envie o arquivo Excel ou CSV para começar a análise.")
