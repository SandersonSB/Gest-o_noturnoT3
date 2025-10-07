# ==========================================
# Importação das bibliotecas necessárias
# ==========================================
import sys
import subprocess
import pandas as pd
import streamlit as st
from io import BytesIO

# ==========================================
# Instala automaticamente o pacote 'xlsxwriter'
# (usado para gerar o arquivo Excel no final)
# ==========================================
subprocess.run([sys.executable, "-m", "pip", "install", "xlsxwriter"], stdout=subprocess.DEVNULL)

# ==========================================
# Configuração inicial do aplicativo Streamlit
# ==========================================
st.set_page_config(page_title="Análise de Tempo - Galpão", layout="wide")
st.title("📊 Análise de Tempo - Validação por Dia")

# ==========================================
# Define a regra de almoço (1 hora e 20 minutos)
# ==========================================
tempo_almoco = 1 + 20/60  # transforma 1h20min em 1.333 horas

# ==========================================
# Área de upload do arquivo de logs
# Aceita tanto .csv quanto .xlsx (Excel)
# ==========================================
uploaded_file = st.file_uploader("📂 Envie o arquivo (.csv ou .xlsx)", type=["csv", "xlsx"])

# Só executa o cálculo se o arquivo for enviado
if uploaded_file:
    try:
        # ==========================================
        # 1️⃣ - Leitura do arquivo enviado
        # ==========================================
        # Detecta o tipo de arquivo (CSV ou Excel) e lê corretamente
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # ==========================================
        # 2️⃣ - Validação básica de colunas obrigatórias
        # ==========================================
        # O arquivo precisa ter essas colunas exatas
        colunas_necessarias = {'Time', 'Zone', 'Access Point'}
        if not colunas_necessarias.issubset(df.columns):
            raise ValueError("Colunas incorretas")  # Força o erro se estiver diferente

        # ==========================================
        # 3️⃣ - Ajuste e limpeza da coluna de tempo
        # ==========================================
        # Converte a coluna 'Time' em formato de data/hora
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.dropna(subset=['Time'])  # remove linhas com datas inválidas

        # Cria uma nova coluna apenas com a data (sem hora)
        df['Data'] = df['Time'].dt.date

        # Lista onde serão guardados os resultados por dia
        resultados = []

        # ==========================================
        # 4️⃣ - Lógica principal do cálculo
        # ==========================================
        # Agrupa os registros por dia
        for data, grupo in df.groupby('Data'):
            # Ordena os registros por horário
            grupo = grupo.sort_values('Time')

            # ------------------------------
            # Calcula quanto tempo a pessoa ficou na empresa naquele dia
            # (pega o primeiro horário e o último)
            # ------------------------------
            tempo_total_empresa = (grupo['Time'].max() - grupo['Time'].min()).total_seconds() / 3600

            # ------------------------------
            # Filtra apenas os acessos relacionados ao "Galpão"
            # ------------------------------
            galpao = grupo[grupo['Access Point'].str.contains("galpao|galpão", case=False, na=False)].copy()

            # Se não tiver nenhum registro de galpão, considera que ficou fora o tempo todo
            if galpao.empty:
                tempo_dentro = 0
                tempo_fora_total = tempo_total_empresa
            else:
                # ------------------------------
                # Cria uma coluna "Acao" dizendo se foi ENTRADA ou SAÍDA
                # ------------------------------
                galpao['Acao'] = galpao['Access Point'].apply(
                    lambda x: 'ENTRADA' if 'entrada' in x.lower()
                    else ('SAIDA' if 'saida' in x.lower() or 'saída' in x.lower() else None)
                )

                # ------------------------------
                # Cria uma coluna "Fim" que é o próximo evento da linha
                # (usado pra calcular o tempo entre uma ação e outra)
                # ------------------------------
                galpao['Fim'] = galpao['Time'].shift(-1)

                # ------------------------------
                # Calcula a duração entre cada evento e o próximo
                # ------------------------------
                galpao['Duracao'] = (galpao['Fim'] - galpao['Time']).dt.total_seconds() / 3600

                # ------------------------------
                # Soma o tempo dentro do galpão (entradas)
                # ------------------------------
                tempo_dentro = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Duracao'].sum()

                # ------------------------------
                # Soma o tempo fora "interno" (entre uma saída e próxima entrada)
                # ------------------------------
                tempo_fora_interno = galpao.loc[galpao['Acao'] == 'SAIDA', 'Duracao'].sum()

                # ------------------------------
                # Calcula o tempo ANTES da primeira entrada no galpão
                # e o tempo DEPOIS da última saída
                # ------------------------------
                primeira_entrada = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Time'].min()
                ultima_saida = galpao.loc[galpao['Acao'] == 'SAIDA', 'Time'].max()

                tempo_antes_primeira = 0
                tempo_depois_ultima = 0

                # Se tiver entrada, calcula quanto tempo ficou na empresa antes de entrar no galpão
                if not pd.isna(primeira_entrada):
                    tempo_antes_primeira = (primeira_entrada - grupo['Time'].min()).total_seconds() / 3600

                # Se tiver saída, calcula quanto tempo ficou na empresa depois de sair do galpão
                if not pd.isna(ultima_saida):
                    tempo_depois_ultima = (grupo['Time'].max() - ultima_saida).total_seconds() / 3600

                # ------------------------------
                # Tempo fora total = tempo fora interno + antes + depois
                # ------------------------------
                tempo_fora_total = tempo_fora_interno + tempo_antes_primeira + tempo_depois_ultima

                # ------------------------------
                # Aplica a regra de almoço:
                # se o tempo fora for maior que 1h20, subtrai esse valor
                # ------------------------------
                if tempo_fora_total > tempo_almoco:
                    tempo_fora_total -= tempo_almoco

            # Guarda os resultados de cada dia
            resultados.append({
                'Data': data,
                'Tempo Total na Empresa (h)': round(tempo_total_empresa, 2),
                'Tempo Dentro do Galpão (h)': round(tempo_dentro, 2),
                'Tempo Fora do Galpão (h)': round(tempo_fora_total, 2)
            })

        # ==========================================
        # 5️⃣ - Gera um arquivo Excel com os resultados
        # ==========================================
        df_result = pd.DataFrame(resultados)

        # Cria um arquivo em memória (sem salvar no disco)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_result.to_excel(writer, index=False, sheet_name='Resultados')
        buffer.seek(0)

        # Mostra mensagem de sucesso e botão pra baixar
        st.success("✅ Processamento concluído com sucesso!")
        st.download_button(
            label="📥 Baixar Resultado (Excel)",
            data=buffer,
            file_name="resultado_tempo_galpao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ==========================================
    # 6️⃣ - Mensagem de erro amigável
    # ==========================================
    except Exception as e:
        st.error("❌ Erro, anexe o relatório com colunas e formato correto.")
        st.caption(f"Detalhe técnico: {e}")

# Se nenhum arquivo foi enviado ainda, mostra instrução na tela
else:
    st.info("⬆️ Envie o arquivo CSV ou Excel para começar a análise.")
