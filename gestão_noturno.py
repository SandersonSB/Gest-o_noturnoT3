import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO

# ================================
# CONFIGURAÇÃO INICIAL DO APP
# ================================
st.set_page_config(page_title="Análise de Tempo - Galpão", layout="wide")
st.title("📊 Análise de Tempo Dentro e Fora do Galpão")

# ================================
# Função auxiliar: formatar horas em HH:MM
# ================================
def formatar_horas(horas_decimais):
    total_segundos = int(horas_decimais * 3600)
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    return f"{h:02d}:{m:02d}"

# ================================
# Configuração de almoço
# ================================
tempo_almoco = 1 + 20/60  # 1h20 = 1 + 20/60 horas

# ================================
# Upload do arquivo
# ================================
uploaded_file = st.file_uploader("📂 Envie o arquivo Excel ou CSV", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Ler o arquivo
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Converter Time para datetime
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')

        # ================================
        # Detectar tipo de evento
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
        # Cálculo do tempo por pessoa e dia
        # ================================
        resultados = []

        for pessoa, grupo_pessoa in df.groupby('Person'):
            grupo_pessoa = grupo_pessoa.sort_values('Time')
            grupo_pessoa['Data'] = grupo_pessoa['Time'].dt.date

            for data, grupo_dia in grupo_pessoa.groupby('Data'):
                grupo_dia = grupo_dia.sort_values('Time')

                # --- Tempo total na empresa (portaria)
                entradas_portaria = grupo_dia[grupo_dia['Evento'] == 'ENTRADA_PORTARIA']['Time']
                saidas_portaria = grupo_dia[grupo_dia['Evento'] == 'SAIDA_PORTARIA']['Time']
                if not entradas_portaria.empty and not saidas_portaria.empty:
                    entrada_portaria = entradas_portaria.iloc[0]
                    saida_portaria = saidas_portaria.iloc[-1]
                    tempo_empresa = (saida_portaria - entrada_portaria).total_seconds() / 3600
                else:
                    tempo_empresa = 0

                # --- Tempo dentro do galpão
                entradas_galpao = grupo_dia[grupo_dia['Evento'] == 'ENTRADA_GALPAO']['Time'].tolist()
                saidas_galpao = grupo_dia[grupo_dia['Evento'] == 'SAIDA_GALPAO']['Time'].tolist()

                tempo_galpao = 0
                for ent, sai in zip(entradas_galpao, saidas_galpao):
                    if ent is not None and sai is not None and sai > ent:
                        delta = (sai - ent).total_seconds() / 3600
                        tempo_galpao += delta

                # --- Tempo fora do galpão (somando todos os intervalos entre saída e próxima entrada)
                tempo_fora = 0
                entradas_galpao.sort()
                saidas_galpao.sort()
                for i in range(len(saidas_galpao)):
                    sai = saidas_galpao[i]
                    if i + 1 < len(entradas_galpao):
                        proxima_ent = entradas_galpao[i + 1]
                        if proxima_ent > sai:
                            delta = (proxima_ent - sai).total_seconds() / 3600
                            tempo_fora += delta
                # Subtrai almoço apenas uma vez no final do dia
                tempo_fora = max(0, tempo_fora - tempo_almoco)

                resultados.append({
                    'Pessoa': pessoa,
                    'Data': data,
                    'Tempo na Empresa (h)': tempo_empresa,
                    'Tempo no Galpão (h)': tempo_galpao,
                    'Tempo Fora do Galpão (h)': tempo_fora
                })

        df_result = pd.DataFrame(resultados)

        # ================================
        # Limpeza e resumo por pessoa
        # ================================
        df_validos = df_result[df_result['Tempo na Empresa (h)'] > 0].copy()

        df_resumo = df_validos.groupby('Pessoa', as_index=False)[
            ['Tempo na Empresa (h)', 'Tempo no Galpão (h)', 'Tempo Fora do Galpão (h)']
        ].sum()

        # Adiciona colunas em HH:MM
        df_result['Tempo na Empresa (HH:MM)'] = df_result['Tempo na Empresa (h)'].apply(formatar_horas)
        df_result['Tempo no Galpão (HH:MM)'] = df_result['Tempo no Galpão (h)'].apply(formatar_horas)
        df_result['Tempo Fora (HH:MM)'] = df_result['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        # ================================
        # 1️⃣ Ranking de Tempo Fora do Galpão
        # ================================
        st.subheader("🏆 Ranking - Tempo Dentro e Fora do Galpão")

        df_rank = df_resumo.sort_values('Tempo Fora do Galpão (h)', ascending=False)
        df_rank['Tempo Dentro (HH:MM)'] = df_rank['Tempo no Galpão (h)'].apply(formatar_horas)
        df_rank['Tempo Fora (HH:MM)'] = df_rank['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        fig_bar = px.bar(
            df_rank,
            x='Pessoa',
            y=['Tempo no Galpão (h)', 'Tempo Fora do Galpão (h)'],
            barmode='stack',
            title="Tempo Total Dentro vs Fora do Galpão",
            labels={"value": "Horas", "variable": "Categoria"},
            color_discrete_sequence=['#4CAF50', '#F44336']
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ================================
        # 2️⃣ Pizza de proporção total
        # ================================
        st.subheader("📊 Proporção Geral - Dentro vs Fora do Galpão")

        total_dentro = df_resumo['Tempo no Galpão (h)'].sum()
        total_fora = df_resumo['Tempo Fora do Galpão (h)'].sum()

        df_pizza = pd.DataFrame({
            'Categoria': ['Dentro do Galpão', 'Fora do Galpão'],
            'Horas': [total_dentro, total_fora]
        })

        fig_pizza = px.pie(
            df_pizza,
            names='Categoria',
            values='Horas',
            color='Categoria',
            color_discrete_sequence=['#4CAF50', '#F44336'],
            hole=0.4
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

        # ================================
        # 3️⃣ Gráfico diário por pessoa
        # ================================
        st.subheader("📅 Tempo por Dia - Selecione uma pessoa")
        pessoa_sel = st.selectbox("Escolha o nome:", df_validos['Pessoa'].unique())

        df_pessoa = df_validos[df_validos['Pessoa'] == pessoa_sel]
        df_pessoa['Tempo na Empresa (HH:MM)'] = df_pessoa['Tempo na Empresa (h)'].apply(formatar_horas)
        df_pessoa['Tempo no Galpão (HH:MM)'] = df_pessoa['Tempo no Galpão (h)'].apply(formatar_horas)
        df_pessoa['Tempo Fora (HH:MM)'] = df_pessoa['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        fig_dia = px.bar(
            df_pessoa,
            x='Data',
            y=['Tempo no Galpão (h)', 'Tempo Fora do Galpão (h)'],
            barmode='stack',
            color_discrete_sequence=['#4CAF50', '#F44336'],
            labels={"value": "Horas", "variable": "Categoria"},
            title=f"Tempo Diário de {pessoa_sel}"
        )
        st.plotly_chart(fig_dia, use_container_width=True)

        # ================================
        # 4️⃣ Tabelas
        # ================================
        st.subheader("📋 Resumo por Pessoa")
        st.dataframe(df_resumo.style.format({
            'Tempo na Empresa (h)': '{:.2f}',
            'Tempo no Galpão (h)': '{:.2f}',
            'Tempo Fora do Galpão (h)': '{:.2f}'
        }))

        st.subheader("📑 Detalhamento por Dia")
        st.dataframe(df_validos)

        # ================================
        # 5️⃣ Baixar detalhamento
        # ================================
        buffer = BytesIO()
        df_validos.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        st.download_button(
            label="📥 Baixar Detalhamento (Excel)",
            data=buffer,
            file_name="tempo_detalhado_galpao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # ================================
        # 6️⃣ Inconsistências
        # ================================
        inconsistencias = []
        for pessoa, grupo in df.groupby('Person'):
            grupo['Data'] = grupo['Time'].dt.date
            for data, g in grupo.groupby('Data'):
                eventos = g['Evento'].unique().tolist()
                if 'ENTRADA_PORTARIA' not in eventos or 'SAIDA_PORTARIA' not in eventos:
                    inconsistencias.append({'Pessoa': pessoa, 'Data': data, 'Eventos Encontrados': eventos})

        df_inconsistencias = pd.DataFrame(inconsistencias)
        if not df_inconsistencias.empty:
            st.subheader("⚠️ Dias com Dados Incompletos (sem entrada ou saída na portaria)")
            st.dataframe(df_inconsistencias)

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")

else:
    st.info("⬆️ Envie o arquivo Excel ou CSV para começar a análise.")
