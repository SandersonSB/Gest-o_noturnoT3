import pandas as pd
import streamlit as st
from io import BytesIO

# ==========================================
# Configuração Streamlit
# ==========================================
st.set_page_config(page_title="Análise de Tempo - Galpão", layout="wide")
st.title("📊 Validação de Tempo no Galpão por Pessoa")

# Regra de almoço: 1h20min
tempo_almoco = 1 + 20/60  # 1.333 horas

# Upload do arquivo
uploaded_file = st.file_uploader("📂 Envie o arquivo (.csv ou .xlsx)", type=["csv", "xlsx"])

# Função para formatar horas decimais em HH:MM
def formatar_horas(horas_decimais):
    total_segundos = int(horas_decimais * 3600)
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    return f"{h:02d}:{m:02d}"

if uploaded_file:
    try:
        # Leitura do arquivo
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Verificação das colunas obrigatórias
        colunas_necessarias = {'Person', 'Time', 'Zone', 'Access Point'}
        if not colunas_necessarias.issubset(df.columns):
            raise ValueError("Colunas incorretas")

        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.dropna(subset=['Time'])
        df['Data'] = df['Time'].dt.date
        df['Dia da Semana'] = df['Time'].dt.day_name(locale='pt_BR')  # Nome do dia em português

        resultados = []

        # Agrupar por pessoa e por dia
        for pessoa, grupo_pessoa in df.groupby('Person'):
            for data, grupo in grupo_pessoa.groupby('Data'):
                grupo = grupo.sort_values('Time')

                # Tempo total na empresa (primeiro e último registro)
                tempo_total_empresa = (grupo['Time'].max() - grupo['Time'].min()).total_seconds() / 3600

                # Filtra apenas registros de galpão
                galpao = grupo[grupo['Access Point'].str.contains("galpao|galpão", case=False, na=False)].copy()
                if galpao.empty:
                    tempo_dentro = 0
                    tempo_fora_total = tempo_total_empresa
                else:
                    # Classifica ENTRADA ou SAÍDA
                    galpao['Acao'] = galpao['Access Point'].apply(
                        lambda x: 'ENTRADA' if 'entrada' in x.lower()
                        else ('SAIDA' if 'saida' in x.lower() or 'saída' in x.lower() else None)
                    )
                    galpao['Fim'] = galpao['Time'].shift(-1)
                    galpao['Duracao'] = (galpao['Fim'] - galpao['Time']).dt.total_seconds() / 3600

                    # Soma tempo dentro e fora do galpão
                    tempo_dentro = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Duracao'].sum()
                    tempo_fora_interno = galpao.loc[galpao['Acao'] == 'SAIDA', 'Duracao'].sum()

                    # Tempo antes da primeira entrada e depois da última saída
                    primeira_entrada = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Time'].min()
                    ultima_saida = galpao.loc[galpao['Acao'] == 'SAIDA', 'Time'].max()

                    tempo_antes_primeira = 0
                    tempo_depois_ultima = 0
                    if not pd.isna(primeira_entrada):
                        tempo_antes_primeira = (primeira_entrada - grupo['Time'].min()).total_seconds() / 3600
                    if not pd.isna(ultima_saida):
                        tempo_depois_ultima = (grupo['Time'].max() - ultima_saida).total_seconds() / 3600

                    tempo_fora_total = tempo_fora_interno + tempo_antes_primeira + tempo_depois_ultima
                    if tempo_fora_total > tempo_almoco:
                        tempo_fora_total -= tempo_almoco

                resultados.append({
                    'Pessoa': pessoa,
                    'Data': data,
                    'Dia da Semana': grupo['Dia da Semana'].iloc[0],
                    'Tempo Total na Empresa (h)': round(tempo_total_empresa, 2),
                    'Tempo Dentro do Galpão (h)': round(tempo_dentro, 2),
                    'Tempo Fora do Galpão (h)': round(tempo_fora_total, 2)
                })

        # Cria DataFrame final
        df_result = pd.DataFrame(resultados)

        # Adiciona colunas já em HH:MM
        df_result['Tempo Total na Empresa (HH:MM)'] = df_result['Tempo Total na Empresa (h)'].apply(formatar_horas)
        df_result['Tempo Dentro do Galpão (HH:MM)'] = df_result['Tempo Dentro do Galpão (h)'].apply(formatar_horas)
        df_result['Tempo Fora do Galpão (HH:MM)'] = df_result['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        # Exporta para Excel
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_result.to_excel(writer, index=False, sheet_name='Resumo')
        buffer.seek(0)

        st.success("✅ Processamento concluído!")
        st.download_button(
            label="📥 Baixar Excel com horas convertidas",
            data=buffer,
            file_name="resultado_galpao_por_pessoa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.dataframe(df_result)

    except Exception as e:
        st.error("❌ Erro, anexe o relatório com colunas e formato correto.")
        st.caption(f"Detalhe técnico: {e}")
else:
    st.info("⬆️ Envie o arquivo CSV ou Excel para começar a análise.")
