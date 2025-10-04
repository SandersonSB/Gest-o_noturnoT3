import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Ranking Tempo Fora do Galpão", layout="wide")
st.title("📊 Ranking de Tempo Fora do Galpão")

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

        # ================================
        # 2️⃣ Detectar evento real baseado em Access Point
        # ================================
        def detectar_evento(access_point):
            ap = str(access_point).lower()
            if 'entrada' in ap:
                return 'ENTRADA'
            elif 'saida' in ap or 'saída' in ap:
                return 'SAIDA'
            else:
                return 'DESCONHECIDO'

        df['Evento'] = df['Access Point'].apply(detectar_evento)

        # Filtrar apenas entradas e saídas válidas
        df = df[df['Evento'].isin(['ENTRADA','SAIDA'])]

        if df.empty:
            st.warning("⚠️ Nenhuma entrada ou saída válida detectada no arquivo.")
            st.stop()

        # ================================
        # 3️⃣ Calcular Tempo Fora por pessoa
        # ================================
        tempo_fora_lista = []

        for pessoa, grupo in df.groupby('Person'):
            grupo = grupo.sort_values('Time')
            stack = []
            total_horas = 0
            for _, row in grupo.iterrows():
                if row['Evento'] == 'SAIDA':
                    stack.append(row['Time'])
                elif row['Evento'] == 'ENTRADA' and stack:
                    saida = stack.pop()
                    delta = row['Time'] - saida
                    total_horas += delta.total_seconds() / 3600
            tempo_fora_lista.append({'Person': pessoa, 'Tempo Fora (h)': total_horas})

        df_tempo_fora = pd.DataFrame(tempo_fora_lista)
        df_tempo_fora = df_tempo_fora.sort_values('Tempo Fora (h)', ascending=False)

        # ================================
        # 4️⃣ Gráfico de ranking (barra)
        # ================================
        st.subheader("🏆 Ranking - Quem mais ficou fora do galpão")
        fig_bar = px.bar(
            df_tempo_fora,
            x='Person',
            y='Tempo Fora (h)',
            text='Tempo Fora (h)',
            color='Tempo Fora (h)',
            color_continuous_scale='Reds'
        )
        fig_bar.update_traces(texttemplate='%{text:.2f}h', textposition='outside')
        fig_bar.update_layout(yaxis_title="Horas Fora", xaxis_title="Pessoa")
        st.plotly_chart(fig_bar, use_container_width=True)

        # ================================
        # 5️⃣ Gráfico de pizza
        # ================================
        st.subheader("📊 Participação no Tempo Fora")
        fig_pizza = px.pie(
            df_tempo_fora,
            names='Person',
            values='Tempo Fora (h)',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

        # ================================
        # 6️⃣ Gráfico interativo por pessoa: tempo fora por dia da semana
        # ================================
        st.subheader("📊 Tempo Fora por Dia da Semana")
        pessoa_selecionada = st.selectbox("Selecione uma pessoa:", df_tempo_fora['Person'])

        # Filtrar registros da pessoa
        grupo_pessoa = df[df['Person'] == pessoa_selecionada].sort_values('Time')
        stack = []
        tempos_por_dia = []

        for _, row in grupo_pessoa.iterrows():
            if row['Evento'] == 'SAIDA':
                stack.append(row['Time'])
            elif row['Evento'] == 'ENTRADA' and stack:
                saida = stack.pop()
                delta = row['Time'] - saida
                tempos_por_dia.append({'Dia': saida.date(), 'Horas Fora': delta.total_seconds()/3600})

        if tempos_por_dia:
            df_dias = pd.DataFrame(tempos_por_dia)
            df_dias['Dia da Semana'] = pd.to_datetime(df_dias['Dia']).dt.day_name()
            dias_pt = {
                'Monday': 'Segunda-feira',
                'Tuesday': 'Terça-feira',
                'Wednesday': 'Quarta-feira',
                'Thursday': 'Quinta-feira',
                'Friday': 'Sexta-feira',
                'Saturday': 'Sábado',
                'Sunday': 'Domingo'
            }
            df_dias['Dia da Semana'] = df_dias['Dia da Semana'].map(dias_pt)

            # Agrupar por dia da semana
            df_dias_agg = df_dias.groupby('Dia da Semana', as_index=False)['Horas Fora'].sum()

            # Gráfico de barras
            fig_dia_semana = px.bar(
                df_dias_agg,
                x='Dia da Semana',
                y='Horas Fora',
                text='Horas Fora',
                color='Horas Fora',
                color_continuous_scale='Blues'
            )
            fig_dia_semana.update_traces(texttemplate='%{text:.2f}h', textposition='outside')
            fig_dia_semana.update_layout(yaxis_title="Horas Fora", xaxis_title="Dia da Semana")
            st.plotly_chart(fig_dia_semana, use_container_width=True)
        else:
            st.info("Não há registros suficientes de saída/entrada para calcular o tempo fora desta pessoa.")

        # ================================
        # 7️⃣ Tabela detalhada (opcional)
        # ================================
        st.subheader("📋 Tempo Fora detalhado por pessoa")
        st.dataframe(df_tempo_fora.reset_index(drop=True))

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

else:
    st.info("⬆️ Por favor, envie o arquivo Excel ou CSV para começar a análise.")
