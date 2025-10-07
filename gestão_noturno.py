import sys
import subprocess

# Garante que o xlsxwriter está instalado (caso não esteja)
subprocess.run([sys.executable, "-m", "pip", "install", "xlsxwriter"])

import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import timedelta

# ================================
# CONFIGURAÇÃO STREAMLIT
# ================================
st.set_page_config(page_title="Validador de Tempo no Galpão", layout="centered")
st.title("📊 Validador de Tempo no Galpão")

# Upload do arquivo
uploaded_file = st.file_uploader("Envie o arquivo de logs (.csv)", type=["csv"])

if uploaded_file:
    # ================================
    # 1. Carregamento e Conversão
    # ================================
    df = pd.read_csv(uploaded_file)
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time']).sort_values('Time')

    # Garante que Zone e Access Point existam
    if not all(col in df.columns for col in ['Zone', 'Access Point']):
        st.error("As colunas 'Zone' e 'Access Point' são obrigatórias.")
        st.stop()

    # ================================
    # 2. Tempo Total na Empresa
    # ================================
    tempo_total_empresa = df['Time'].max() - df['Time'].min()

    # ================================
    # 3. Filtragem e Classificação
    # ================================
    galpao_df = df[df['Access Point'].str.contains('Galpao|Galpão', case=False, na=False)].copy()

    def classificar_acao(ap):
        ap = str(ap).lower()
        if "entrada" in ap:
            return "ENTRADA"
        elif "saida" in ap or "saída" in ap:
            return "SAIDA"
        return None

    galpao_df['Acao'] = galpao_df['Access Point'].apply(classificar_acao)
    galpao_df = galpao_df.dropna(subset=['Acao'])

    # ================================
    # 4. Cálculo de Intervalos
    # ================================
    galpao_df['Fim'] = galpao_df['Time'].shift(-1)
    galpao_df['Duracao'] = galpao_df['Fim'] - galpao_df['Time']

    # ================================
    # 5. Resultados por Dia
    # ================================
    galpao_df['Data'] = galpao_df['Time'].dt.date
    resultados = []

    for data, grupo in galpao_df.groupby('Data'):
        tempo_dentro = grupo.loc[grupo['Acao'] == 'ENTRADA', 'Duracao'].sum()
        tempo_fora_interno = grupo.loc[grupo['Acao'] == 'SAIDA', 'Duracao'].sum()

        # Ajusta o tempo fora (almoço)
        if tempo_fora_interno > timedelta(hours=1, minutes=20):
            tempo_fora_total = tempo_fora_interno - timedelta(hours=1, minutes=20)
        else:
            tempo_fora_total = tempo_fora_interno

        resultados.append({
            'Data': data,
            'Tempo Dentro Galpão (h)': round(tempo_dentro.total_seconds() / 3600, 2),
            'Tempo Fora Galpão (h)': round(tempo_fora_total.total_seconds() / 3600, 2),
            'Tempo Fora Original (h)': round(tempo_fora_interno.total_seconds() / 3600, 2),
            'Almoço Ajustado?': 'Sim' if tempo_fora_interno > timedelta(hours=1, minutes=20) else 'Não'
        })

    df_resultado = pd.DataFrame(resultados)

    # ================================
    # 6. Exportar Excel
    # ================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_resultado.to_excel(writer, index=False, sheet_name='Resumo')
    output.seek(0)

    st.success("✅ Análise concluída com sucesso!")
    st.download_button(
        label="📥 Baixar Resultado em Excel",
        data=output,
        file_name='tempo_galpao_validado.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    st.dataframe(df_resultado)
