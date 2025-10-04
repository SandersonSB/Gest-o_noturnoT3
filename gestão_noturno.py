import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Análise de Entradas e Saídas do Galpão", layout="wide")
st.title("📊 Análise de Entradas e Saídas do Galpão")

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

        # Converter Time para datetime
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')

        # Padronizar coluna Entered/Exited Status
        df['Entered/Exited Status'] = df['Entered/Exited Status'].astype(str).str.strip().str.upper()

        # Detectar possíveis valores de entrada e saída
        entrada_vals = ['IN', 'ENTRADA', 'ENTERED']
        saida_vals = ['OUT', 'SAIDA', 'SAÍDA', 'EXITED']

        has_entradas = df['Entered/Exited Status'].isin(entrada_vals).any()
        has_saidas = df['Entered/Exited Status'].isin(saida_vals).any()

        if not has_entradas:
            st.warning("⚠️ Nenhuma entrada detectada no arquivo.")
            st.stop()

        # ================================
        # 2️⃣ Calcular Tempo Fora se houver saídas
        # ================================
        df_resultado = pd.DataFrame()

        if has_saidas:
            tempo_fora = []

            # Substituir valores para padronizar
            df['Status_Normalizado'] = df['Entered/Exited Status'].apply(
                lambda x: 'SAIDA' if x in saida_vals else ('ENTRADA' if x in entrada_vals else x)
            )

            for pessoa, grupo in df.groupby('Person'):
                total_horas = 0
                stack = []
                for _, row in grupo.sort_values('Time').iterrows():
                    if row['Status_Normalizado'] == 'SAIDA':
                        stack.append(row['Time'])
                    elif row['Status_Normalizado'] == 'ENTRADA' and stack:
                        saida = stack.pop()
                        delta = row['Time'] - saida
                        total_horas += delta.total_seconds() / 3600
                tempo_fora.append({'Person': pessoa, 'Tempo Fora (h)': total_horas})

            df_resultado = pd.DataFrame(tempo_fora, columns=['Person', 'Tempo Fora (h)'])
            st.subheader("🏆 Ranking - Quem mais ficou fora do galpão")
            df_ranking = df_resultado.sort_values('Tempo Fora (h)', ascending=False)
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
            # Gráfico de Tempo Fora por Dia da Semana real
            # ================================
            df_saidas = df[df['Status_Normalizado'] == 'SAIDA'].copy()
            df_saidas['Dia da Semana'] = df_saidas['Time'].dt.day_name()
            dias_pt = {
                'Monday': 'Segunda-feira',
                'Tuesday': 'Terça-feira',
                'Wednesday': 'Quarta-feira',
                'Thursday': 'Quinta-feira',
                'Friday': 'Sexta-feira',
                'Saturday': 'Sábado',
                'Sunday': 'Domingo'
            }
            df_saidas['Dia da Semana'] = df_saidas['Dia da Semana'].map(dias_pt)

            df_semana_todos = df_saidas.groupby(['Person', 'Dia da Semana'], as_index=False).size().rename(columns={'size':'Saídas'})
            fig_semana_todos = px.bar(
                df_semana_todos,
                x="Dia da Semana",
                y="Saídas",
                color="Person",
                barmode="group",
                text="Saídas"
            )
            fig_semana_todos.update_traces(texttemplate='%{text}', textposition="outside")
            fig_semana_todos.update_layout(yaxis_title="Saídas", xaxis_title="Dia da Semana")
            st.subheader("📊 Saídas por pessoa por dia da semana")
            st.plotly_chart(fig_semana_todos, use_container_width=True)

        # ================================
        # 3️⃣ Relatório de entradas (sempre)
        # ================================
        st.subheader("📊 Entradas por pessoa")
        df_entradas = df[df['Entered/Exited Status'].isin(entrada_vals)]
        df_entradas['Dia da Semana'] = df_entradas['Time'].dt.day_name().map(dias_pt)
        entradas_por_pessoa = df_entradas.groupby(['Person','Dia da Semana'], as_index=False).size().rename(columns={'size':'Quantidade de Entradas'})

        fig_entradas = px.bar(
            entradas_por_pessoa,
            x='Dia da Semana',
            y='Quantidade de Entradas',
            color='Person',
            barmode='group',
            text='Quantidade de Entradas'
        )
        fig_entradas.update_traces(texttemplate='%{text}', textposition='outside')
        fig_entradas.update_layout(yaxis_title="Entradas", xaxis_title="Dia da Semana")
        st.plotly_chart(fig_entradas, use_container_width=True)

        # Mostrar horários de entrada detalhados
        st.subheader("🕒 Horários de entrada")
        pessoa_selecionada = st.selectbox("Selecione uma pessoa para ver horários de entrada:", df['Person'].unique())
        horarios = df_entradas[df_entradas['Person'] == pessoa_selecionada][['Time']].sort_values('Time')
        st.dataframe(horarios)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("⬆️ Por favor, envie o arquivo Excel ou CSV para começar a análise.")
