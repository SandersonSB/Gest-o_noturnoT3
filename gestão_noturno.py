import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO

st.set_page_config(page_title="Ranking Tempo Fora do Galpão", layout="wide")
st.title("📊 Ranking de Tempo Fora do Galpão")

# ================================
# Função utilitária: formata horas decimais em HH:MM
# ================================
def formatar_horas(horas_decimais):
    total_segundos = int(horas_decimais * 3600)
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    return f"{h:02d}:{m:02d}"

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
            if "portaria" in ap:
                if "entrada" in ap:
                    return "ENTRADA_PORTARIA"
                elif "saida" in ap or "saída" in ap:
                    return "SAIDA_PORTARIA"
            elif "galpao" in ap or "galpão" in ap:
                if "entrada" in ap:
                    return "ENTRADA_GALPAO"
                elif "saida" in ap or "saída" in ap:
                    return "SAIDA_GALPAO"
            else:
                return "OUTRO"

        df['Evento'] = df['Access Point'].apply(detectar_evento)

        # ================================
        # 3️⃣ Calcular Tempo Fora por pessoa
        # ================================
        tempo_fora_lista = []

        for pessoa, grupo in df.groupby('Person'):
            grupo = grupo.sort_values('Time')
            total_horas = 0
            inicio_fora = None
            dentro_empresa = False

            for _, row in grupo.iterrows():
                ev = row['Evento']

                if ev == "ENTRADA_PORTARIA":
                    dentro_empresa = True
                elif ev == "ENTRADA_GALPAO" and inicio_fora:
                    delta = row['Time'] - inicio_fora
                    total_horas += delta.total_seconds() / 3600
                    inicio_fora = None
                elif ev == "SAIDA_GALPAO" and dentro_empresa:
                    inicio_fora = row['Time']
                elif ev == "SAIDA_PORTARIA":
                    dentro_empresa = False
                    inicio_fora = None

            # Descontar almoço fixo (1h20 por dia)
            dias = grupo['Time'].dt.date.nunique()
            desconto = dias * (1 + 20/60)
            total_horas = max(0, total_horas - desconto)

            tempo_fora_lista.append({'Person': pessoa, 'Tempo Fora (h)': total_horas})

        df_tempo_fora = pd.DataFrame(tempo_fora_lista)
        df_tempo_fora['Tempo Fora (HH:MM)'] = df_tempo_fora['Tempo Fora (h)'].apply(formatar_horas)
        df_tempo_fora = df_tempo_fora.sort_values('Tempo Fora (h)', ascending=False)

        # ================================
        # 4️⃣ Gráfico de ranking (barra)
        # ================================
        st.subheader("🏆 Ranking - Quem mais ficou fora do galpão")
        fig_bar = px.bar(
            df_tempo_fora,
            x='Person',
            y='Tempo Fora (h)',
            text='Tempo Fora (HH:MM)',
            color='Tempo Fora (h)',
            color_continuous_scale='Reds'
        )
        fig_bar.update_traces(textposition='outside')
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
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hover_data=['Tempo Fora (HH:MM)']
        )
        fig_pizza.update_traces(text=df_tempo_fora['Tempo Fora (HH:MM)'])
        st.plotly_chart(fig_pizza, use_container_width=True)

        # ================================
        # 6️⃣ Gráfico interativo por pessoa: tempo fora por dia da semana
        # ================================
        st.subheader("📊 Tempo Fora por Dia da Semana")
        pessoa_selecionada = st.selectbox("Selecione uma pessoa:", df_tempo_fora['Person'])

        grupo_pessoa = df[df['Person'] == pessoa_selecionada].sort_values('Time')
        stack = []
        tempos_por_dia = []

        dentro_empresa = False
        inicio_fora = None
        for _, row in grupo_pessoa.iterrows():
            ev = row['Evento']
            if ev == "ENTRADA_PORTARIA":
                dentro_empresa = True
            elif ev == "ENTRADA_GALPAO" and inicio_fora:
                delta = row['Time'] - inicio_fora
                tempos_por_dia.append({'Dia': inicio_fora.date(), 'Horas Fora': delta.total_seconds()/3600})
                inicio_fora = None
            elif ev == "SAIDA_GALPAO" and dentro_empresa:
                inicio_fora = row['Time']
            elif ev == "SAIDA_PORTARIA":
                dentro_empresa = False
                inicio_fora = None

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

            df_dias_agg = df_dias.groupby('Dia da Semana', as_index=False)['Horas Fora'].sum()
            df_dias_agg['Tempo Fora (HH:MM)'] = df_dias_agg['Horas Fora'].apply(formatar_horas)

            ordem_dias = ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado','Domingo']
            df_dias_agg['Dia da Semana'] = pd.Categorical(df_dias_agg['Dia da Semana'], categories=ordem_dias, ordered=True)
            df_dias_agg = df_dias_agg.sort_values('Dia da Semana')

            fig_dia_semana = px.bar(
                df_dias_agg,
                x='Dia da Semana',
                y='Horas Fora',
                text='Tempo Fora (HH:MM)',
                color='Horas Fora',
                color_continuous_scale='Blues'
            )
            fig_dia_semana.update_traces(textposition='outside')
            fig_dia_semana.update_layout(yaxis_title="Horas Fora", xaxis_title="Dia da Semana")
            st.plotly_chart(fig_dia_semana, use_container_width=True)
        else:
            st.info("Não há registros suficientes de saída/entrada para calcular o tempo fora desta pessoa.")

        # ================================
        # 7️⃣ Tabela resumida
        # ================================
        st.subheader("📋 Tempo Fora detalhado por pessoa")
        st.dataframe(df_tempo_fora[['Person','Tempo Fora (HH:MM)']].reset_index(drop=True))

        # ================================
        # 8️⃣ DataFrame detalhado por pessoa, data e dia da semana
        # ================================
        detalhes_lista = []

        for pessoa, grupo in df.groupby('Person'):
            grupo = grupo.sort_values('Time')
            dentro_empresa = False
            inicio_fora = None

            for _, row in grupo.iterrows():
                ev = row['Evento']
                if ev == "ENTRADA_PORTARIA":
                    dentro_empresa = True
                elif ev == "ENTRADA_GALPAO" and inicio_fora:
                    delta = row['Time'] - inicio_fora
                    detalhes_lista.append({
                        "Person": pessoa,
                        "Data": inicio_fora.date(),
                        "Dia da Semana": inicio_fora.strftime("%A"),
                        "Início Fora": inicio_fora,
                        "Fim Fora": row['Time'],
                        "Horas Fora": delta.total_seconds() / 3600
                    })
                    inicio_fora = None
                elif ev == "SAIDA_GALPAO" and dentro_empresa:
                    inicio_fora = row['Time']
                elif ev == "SAIDA_PORTARIA":
                    dentro_empresa = False
                    inicio_fora = None

        df_detalhado = pd.DataFrame(detalhes_lista)

        dias_pt = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        df_detalhado['Dia da Semana'] = df_detalhado['Dia da Semana'].map(dias_pt)

        st.subheader("📑 Detalhamento - Intervalos fora do galpão")
        st.dataframe(df_detalhado)

        # Botão de download em Excel
        buffer = BytesIO()
        df_detalhado.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        st.download_button(
            label="📥 Baixar detalhamento em Excel",
            data=buffer,
            file_name="tempo_fora_detalhado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

else:
    st.info("⬆️ Por favor, envie o arquivo Excel ou CSV para começar a análise.")
