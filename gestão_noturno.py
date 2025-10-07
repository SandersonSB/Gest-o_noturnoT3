import pandas as pd
import streamlit as st
from io import BytesIO
import plotly.express as px

# ===============================
# Configuração inicial do Streamlit
# ===============================
st.set_page_config(page_title="Dashboard Tempo no Galpão", layout="wide")
st.title("📊 Dashboard de Tempo no Galpão")

# ===============================
# Regra de almoço (1h20)
# ===============================
tempo_almoco = 1 + 20/60  # 1h20 em horas decimais

# ===============================
# Upload do arquivo CSV ou Excel
# ===============================
uploaded_file = st.file_uploader("📂 Envie o arquivo (.csv ou .xlsx)", type=["csv", "xlsx"])

# ===============================
# Função para converter horas decimais em HH:MM
# ===============================
def formatar_horas(horas_decimais):
    total_segundos = int(horas_decimais * 3600)
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    return f"{h:02d}:{m:02d}"

# ===============================
# Mapeamento de dia da semana
# ===============================
dias_pt = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# ===============================
# Processamento do arquivo
# ===============================
if uploaded_file:
    try:
        # -------------------------------
        # Ler arquivo
        # -------------------------------
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # -------------------------------
        # Verifica se as colunas obrigatórias existem
        # -------------------------------
        colunas_necessarias = {'Person', 'Time', 'Zone', 'Access Point'}
        if not colunas_necessarias.issubset(df.columns):
            raise ValueError("Erro: colunas incorretas")

        # -------------------------------
        # Converter coluna Time para datetime
        # -------------------------------
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.dropna(subset=['Time'])

        # Cria Data e Dia da Semana
        df['Data'] = df['Time'].dt.date
        df['Dia da Semana'] = df['Time'].dt.day_name().map(dias_pt)

        resultados = []

        # ===============================
        # Processamento por pessoa e dia
        # ===============================
        for pessoa, grupo_pessoa in df.groupby('Person'):
            for data, grupo in grupo_pessoa.groupby('Data'):
                grupo = grupo.sort_values('Time')

                # Tempo total na empresa
                tempo_total_empresa = (grupo['Time'].max() - grupo['Time'].min()).total_seconds() / 3600

                # Filtra registros do galpão
                galpao = grupo[grupo['Access Point'].str.contains("galpao|galpão", case=False, na=False)].copy()
                if galpao.empty:
                    tempo_dentro = 0
                    tempo_fora_total = tempo_total_empresa
                    almoco_aplicado = "Não"
                else:
                    galpao['Acao'] = galpao['Access Point'].apply(
                        lambda x: 'ENTRADA' if 'entrada' in x.lower()
                        else ('SAIDA' if 'saida' in x.lower() or 'saída' in x.lower() else None)
                    )
                    galpao['Fim'] = galpao['Time'].shift(-1)
                    galpao['Duracao'] = (galpao['Fim'] - galpao['Time']).dt.total_seconds() / 3600

                    tempo_dentro = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Duracao'].sum()
                    tempo_fora_interno = galpao.loc[galpao['Acao'] == 'SAIDA', 'Duracao'].sum()

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
                        almoco_aplicado = "Sim"
                    else:
                        almoco_aplicado = "Não"

                resultados.append({
                    'Pessoa': pessoa,
                    'Data': data,
                    'Dia da Semana': grupo['Dia da Semana'].iloc[0],
                    'Tempo Total na Empresa (h)': round(tempo_total_empresa, 2),
                    'Tempo Dentro do Galpão (h)': round(tempo_dentro, 2),
                    'Tempo Fora do Galpão (h)': round(tempo_fora_total, 2),
                    'Almoço Aplicado': almoco_aplicado
                })

        df_result = pd.DataFrame(resultados)
        df_result['Tempo Total na Empresa (HH:MM)'] = df_result['Tempo Total na Empresa (h)'].apply(formatar_horas)
        df_result['Tempo Dentro do Galpão (HH:MM)'] = df_result['Tempo Dentro do Galpão (h)'].apply(formatar_horas)
        df_result['Tempo Fora do Galpão (HH:MM)'] = df_result['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        # ===============================
        # Filtro multiseleção
        # ===============================
        opcoes_pessoas = sorted(df_result['Pessoa'].unique().tolist())
        pessoa_sel = st.multiselect(
            "Filtrar por pessoa (pode selecionar mais de uma, ou 'Todos'):", 
            options=["Todos"] + opcoes_pessoas, 
            default=["Todos"]
        )
        if "Todos" in pessoa_sel:
            df_filtrado = df_result.copy()
        else:
            df_filtrado = df_result[df_result['Pessoa'].isin(pessoa_sel)]

        # ===============================
        # Cria abas: Análise e Listas
        # ===============================
        tab1, tab2 = st.tabs(["📊 Análise de Tempo", "⚫⚪ Black/White List"])

        # ===============================
        # Aba 1: Análise de Tempo
        # ===============================
        with tab1:
            st.subheader("📈 Gráficos de Tempo no Galpão")

            # Ranking por tempo fora
            df_rank_fora = df_filtrado.groupby('Pessoa')['Tempo Fora do Galpão (h)'].sum().reset_index().sort_values('Tempo Fora do Galpão (h)', ascending=False)
            fig_rank_fora = px.bar(df_rank_fora, x='Pessoa', y='Tempo Fora do Galpão (h)',
                                   title="Ranking: Mais tempo fora do galpão", color='Tempo Fora do Galpão (h)', color_continuous_scale='Reds')
            st.plotly_chart(fig_rank_fora, use_container_width=True)

            # Ranking por tempo dentro
            df_rank_dentro = df_filtrado.groupby('Pessoa')['Tempo Dentro do Galpão (h)'].sum().reset_index().sort_values('Tempo Dentro do Galpão (h)', ascending=False)
            fig_rank_dentro = px.bar(df_rank_dentro, x='Pessoa', y='Tempo Dentro do Galpão (h)',
                                   title="Ranking: Mais tempo dentro do galpão", color='Tempo Dentro do Galpão (h)', color_continuous_scale='Greens')
            st.plotly_chart(fig_rank_dentro, use_container_width=True)

            # Dia da semana mais fora
            df_dia = df_filtrado.groupby(['Dia da Semana', 'Pessoa'])['Tempo Fora do Galpão (h)'].sum().reset_index()
            fig_dia = px.bar(df_dia, x='Dia da Semana', y='Tempo Fora do Galpão (h)', color='Pessoa', barmode='group',
                             title="Tempo fora do galpão por dia da semana", color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_dia, use_container_width=True)

            # Botão de download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='Resumo')
            buffer.seek(0)

            st.download_button(
                label="📥 Baixar Excel com horas convertidas",
                data=buffer,
                file_name="resultado_galpao_por_pessoa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ===============================
        # Aba 2: Black/White List
        # ===============================
        with tab2:
            media_fora = df_filtrado['Tempo Fora do Galpão (h)'].mean()
            media_dentro = df_filtrado['Tempo Dentro do Galpão (h)'].mean()

            black_candidates = df_filtrado.groupby('Pessoa')['Tempo Fora do Galpão (h)'].mean()
            white_candidates = df_filtrado.groupby('Pessoa')['Tempo Dentro do Galpão (h)'].mean()

            black_list = [p for p, t in black_candidates.items() if t > media_fora]
            white_list = [p for p, t in white_candidates.items() if t > media_dentro]
            black_list = [p for p in black_list if p not in white_list]

            st.subheader("⚫ Black List e ⚪ White List")
            st.write(f"Média de tempo fora do galpão: **{media_fora:.2f} h**")
            st.write(f"Média de tempo dentro do galpão: **{media_dentro:.2f} h**")
            st.write(f"⚫ Black List (mais tempo fora): {', '.join(black_list) if black_list else 'Nenhuma'}")
            st.write(f"⚪ White List (mais tempo dentro): {', '.join(white_list) if white_list else 'Nenhuma'}")

    except Exception as e:
        st.error("❌ Erro, anexe o relatório com colunas e formato correto.")
        st.caption(f"Detalhe técnico: {e}")

else:
    st.info("⬆️ Envie o arquivo CSV ou Excel para começar a análise.")
