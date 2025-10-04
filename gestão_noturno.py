import pandas as pd
import plotly.express as px
import streamlit as st

st.title("📊 Análise de Tempo Fora do Galpão")

uploaded_file = st.file_uploader("📂 Envie a planilha de entrada/saída", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Detecta se é Excel ou CSV
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Converter Time para datetime
        df['Time'] = pd.to_datetime(df['Time'])

        # Ordenar por pessoa e horário
        df = df.sort_values(['Person', 'Time'])

        # Filtrar apenas eventos de Entrada e Saída
        df = df[df['Entered/Exited Status'].isin(['Entered', 'Exited'])]

        # Criar coluna Data
        df['Data'] = df['Time'].dt.date

        # Calcular Tempo Fora (h)
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

        # Adicionar Data fictícia (não é usada no ranking geral, mas o código espera)
        df_resultado['Data'] = pd.Timestamp.today()

        # Agora seu código de análise funciona normalmente
        df_resultado["Dia da Semana"] = pd.to_datetime(df_resultado["Data"]).dt.day_name(locale="pt_BR")

        # Ranking geral
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

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("⬆️ Por favor, envie o arquivo Excel ou CSV para começar a análise.")
