import pandas as pd
import streamlit as st
from io import BytesIO

# ================================
# CONFIGURAÇÃO BÁSICA
# ================================
st.set_page_config(page_title="Validação - Tempo no Galpão", layout="wide")
st.title("📊 Validação de Tempo por Dia")

# ================================
# Função auxiliar
# ================================
def formatar_horas(horas_decimais):
    total_segundos = int(horas_decimais * 3600)
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    return f"{h:02d}:{m:02d}"

tempo_almoco = 1 + 20/60  # 1h20

# ================================
# Upload do arquivo
# ================================
uploaded_file = st.file_uploader("📂 Envie o arquivo Excel ou CSV", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # ================================
        # Leitura do arquivo
        # ================================
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')

        # ================================
        # Detectar tipo de evento
        # ================================
        def detectar_evento(ap):
            ap = str(ap).lower()
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
            return "OUTRO"

        df['Evento'] = df['Access Point'].apply(detectar_evento)
        df = df.sort_values(['Person', 'Time'])

        resultados = []

        # ================================
        # Loop por pessoa e dia
        # ================================
        for pessoa, g_pessoa in df.groupby('Person'):
            g_pessoa['Data'] = g_pessoa['Time'].dt.date

            for data, g_dia in g_pessoa.groupby('Data'):
                g_dia = g_dia.sort_values('Time')

                entradas_port = g_dia[g_dia['Evento'] == 'ENTRADA_PORTARIA']['Time'].tolist()
                saidas_port = g_dia[g_dia['Evento'] == 'SAIDA_PORTARIA']['Time'].tolist()
                entradas_galpao = g_dia[g_dia['Evento'] == 'ENTRADA_GALPAO']['Time'].tolist()
                saidas_galpao = g_dia[g_dia['Evento'] == 'SAIDA_GALPAO']['Time'].tolist()

                # Tempo total na empresa
                if entradas_port and saidas_port:
                    entrada_empresa = entradas_port[0]
                    saida_empresa = saidas_port[-1]
                    tempo_empresa = (saida_empresa - entrada_empresa).total_seconds() / 3600
                else:
                    tempo_empresa = 0

                # Tempo dentro do galpão
                tempo_galpao = 0
                for ent, sai in zip(entradas_galpao, saidas_galpao):
                    if sai > ent:
                        tempo_galpao += (sai - ent).total_seconds() / 3600

                # Tempo fora do galpão
                tempo_fora = 0

                # Entre entrada portaria e 1ª entrada galpão
                if entradas_port and entradas_galpao:
                    delta = (entradas_galpao[0] - entradas_port[0]).total_seconds() / 3600
                    if delta > 0:
                        tempo_fora += delta

                # Entre cada saída e próxima entrada do galpão
                for sai, prox_ent in zip(saidas_galpao, entradas_galpao[1:]):
                    if prox_ent > sai:
                        tempo_fora += (prox_ent - sai).total_seconds() / 3600

                # Entre última saída galpão e saída portaria
                if saidas_galpao and saidas_port:
                    delta = (saidas_port[-1] - saidas_galpao[-1]).total_seconds() / 3600
                    if delta > 0:
                        tempo_fora += delta

                # Subtrai almoço se tiver tempo suficiente fora
                if tempo_fora > tempo_almoco:
                    tempo_fora -= tempo_almoco

                resultados.append({
                    'Pessoa': pessoa,
                    'Data': data,
                    'Tempo na Empresa (h)': round(tempo_empresa, 2),
                    'Tempo no Galpão (h)': round(tempo_galpao, 2),
                    'Tempo Fora do Galpão (h)': round(tempo_fora, 2),
                    'Tempo na Empresa (HH:MM)': formatar_horas(tempo_empresa),
                    'Tempo no Galpão (HH:MM)': formatar_horas(tempo_galpao),
                    'Tempo Fora (HH:MM)': formatar_horas(tempo_fora)
                })

        df_result = pd.DataFrame(resultados)

        # ================================
        # Exibir tabela final
        # ================================
        st.subheader("📋 Resultados Diários Calculados")
        st.dataframe(df_result)

        # ================================
        # Download Excel
        # ================================
        buffer = BytesIO()
        df_result.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        st.download_button(
            label="📥 Baixar Resultados em Excel",
            data=buffer,
            file_name="validacao_tempo_galpao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")

else:
    st.info("⬆️ Envie o arquivo Excel ou CSV para começar a análise.")
