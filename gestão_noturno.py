import pandas as pd
import streamlit as st
import plotly.express as px
from io import BytesIO

# ===============================
# Configuração inicial do Streamlit
# ===============================
st.set_page_config(page_title="Dashboard Tempo no Galpão", layout="wide")
st.title("📊 Dashboard de Tempo no Galpão por Pessoa")

# ===============================
# Regra de almoço
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
# Mapeamento para dia da semana em português
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
# Se o usuário enviou o arquivo
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
            raise ValueError("Colunas incorretas")

        # -------------------------------
        # Converter coluna Time para datetime
        # -------------------------------
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.dropna(subset=['Time'])

        # Criar colunas de Data e Dia da Semana
        df['Data'] = df['Time'].dt.date
        df['Dia da Semana'] = df['Time'].dt.day_name().map(dias_pt)

        resultados = []

        # ===============================
        # Processamento por pessoa e por dia
        # ===============================
        for pessoa, grupo_pessoa in df.groupby('Person'):
            for data, grupo in grupo_pessoa.groupby('Data'):
                grupo = grupo.sort_values('Time')

                # -------------------------------
                # Tempo total na empresa (primeiro e último registro)
                # -------------------------------
                tempo_total_empresa = (grupo['Time'].max() - grupo['Time'].min()).total_seconds() / 3600

                # -------------------------------
                # Filtra apenas registros de galpão
                # -------------------------------
                galpao = grupo[grupo['Access Point'].str.contains("galpao|galpão", case=False, na=False)].copy()
                if galpao.empty:
                    tempo_dentro = 0
                    tempo_fora_total = tempo_total_empresa
                    almoco_aplicado = "Não"
                else:
                    # -------------------------------
                    # Classifica cada ação como ENTRADA ou SAÍDA
                    # -------------------------------
                    galpao['Acao'] = galpao['Access Point'].apply(
                        lambda x: 'ENTRADA' if 'entrada' in x.lower()
                        else ('SAIDA' if 'saida' in x.lower() or 'saída' in x.lower() else None)
                    )

                    # -------------------------------
                    # Cria coluna Fim para calcular duração
                    # -------------------------------
                    galpao['Fim'] = galpao['Time'].shift(-1)
                    galpao['Duracao'] = (galpao['Fim'] - galpao['Time']).dt.total_seconds() / 3600

                    # -------------------------------
                    # Calcula tempo dentro e fora do galpão (interno)
                    # -------------------------------
                    tempo_dentro = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Duracao'].sum()
                    tempo_fora_interno = galpao.loc[galpao['Acao'] == 'SAIDA', 'Duracao'].sum()

                    # -------------------------------
                    # Tempo antes da primeira entrada e depois da última saída
                    # -------------------------------
                    primeira_entrada = galpao.loc[galpao['Acao'] == 'ENTRADA', 'Time'].min()
                    ultima_saida = galpao.loc[galpao['Acao'] == 'SAIDA', 'Time'].max()

                    tempo_antes_primeira = 0
                    tempo_depois_ultima = 0
                    if not pd.isna(primeira_entrada):
                        tempo_antes_primeira = (primeira_entrada - grupo['Time'].min()).total_seconds() / 3600
                    if not pd.isna(ultima_saida):
                        tempo_depois_ultima = (grupo['Time'].max() - ultima_saida).total_seconds() / 3600

                    # -------------------------------
                    # Soma total do tempo fora do galpão
                    # -------------------------------
                    tempo_fora_total = tempo_fora_interno + tempo_antes_primeira + tempo_depois_ultima

                    # -------------------------------
                    # Aplica a regra do almoço se necessário
                    # -------------------------------
                    if tempo_fora_total > tempo_almoco:
                        tempo_fora_total -= tempo_almoco
                        almoco_aplicado = "Sim"
                    else:
                        almoco_aplicado = "Não"

                # -------------------------------
                # Adiciona resultados no DataFrame final
                # -------------------------------
                resultados.append({
                    'Pessoa': pessoa,
                    'Data': data,
                    'Dia da Semana': grupo['Dia da Semana'].iloc[0],
                    'Tempo Total na Empresa (h)': round(tempo_total_empresa, 2),
                    'Tempo Dentro do Galpão (h)': round(tempo_dentro, 2),
                    'Tempo Fora do Galpão (h)': round(tempo_fora_total, 2),
                    'Almoço Aplicado': almoco_aplicado
                })

        # ===============================
        # Cria DataFrame final e converte horas para HH:MM
        # ===============================
        df_result = pd.DataFrame(resultados)
        df_result['Tempo Total na Empresa (HH:MM)'] = df_result['Tempo Total na Empresa (h)'].apply(formatar_horas)
        df_result['Tempo Dentro do Galpão (HH:MM)'] = df_result['Tempo Dentro do Galpão (h)'].apply(formatar_horas)
        df_result['Tempo Fora do Galpão (HH:MM)'] = df_result['Tempo Fora do Galpão (h)'].apply(formatar_horas)

        # ===============================
        # Filtro por pessoa com multiselect
        # ===============================
        opcoes_pessoas = sorted(df_result['Pessoa'].unique().tolist())
        pessoa_sel = st.multiselect(
            "Filtrar por pessoa (pode selecionar mais de uma, ou 'Todos'):", 
            options=["Todos"] + opcoes_pessoas, 
            default=["Todos"]
        )

        # ===============================
        # Lógica do filtro
        # ===============================
        if "Todos" in pessoa_sel:
            df_filtrado = df_result.copy()
        else:
            df_filtrado = df_result[df_result['Pessoa'].isin(pessoa_sel)]

        # ===============================
        # Gráfico: Ranking Tempo Fora
        # ===============================
        st.subheader("🏆 Ranking: Quem mais fica fora do galpão")
        df_rank_fora = df_filtrado.groupby('Pessoa')['Tempo Fora do Galpão (h)'].sum().reset_index()
        df_rank_fora = df_rank_fora.sort_values('Tempo Fora do Galpão (h)', ascending=False)
        fig_fora = px.bar(df_rank_fora, x='Pessoa', y='Tempo Fora do Galpão (h)', color='Pessoa',
                          title="Tempo Total Fora do Galpão", color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_fora, use_container_width=True)

        # ===============================
        # Gráfico: Ranking Tempo Dentro
        # ===============================
        st.subheader("🏆 Ranking: Quem mais fica dentro do galpão")
        df_rank_dentro = df_filtrado.groupby('Pessoa')['Tempo Dentro do Galpão (h)'].sum().reset_index()
        df_rank_dentro = df_rank_dentro.sort_values('Tempo Dentro do Galpão (h)', ascending=False)
        fig_dentro = px.bar(df_rank_dentro, x='Pessoa', y='Tempo Dentro do Galpão (h)', color='Pessoa',
                            title="Tempo Total Dentro do Galpão", color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_dentro, use_container_width=True)

        # ===============================
        # Gráfico: Dia da semana mais fora
        # ===============================
        st.subheader("📅 Dia da semana que a pessoa mais fica fora do galpão")
        if "Todos" not in pessoa_sel and len(pessoa_sel) == 1:
            pessoa_unica = pessoa_sel[0]
            df_dia = df_filtrado.groupby('Dia da Semana')['Tempo Fora do Galpão (h)'].sum().reset_index()
            df_dia = df_dia.sort_values('Tempo Fora do Galpão (h)', ascending=False)
            fig_dia = px.bar(df_dia, x='Dia da Semana', y='Tempo Fora do Galpão (h)',
                             title=f"Dias da Semana - {pessoa_unica} mais tempo fora",
                             color='Dia da Semana', color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_dia, use_container_width=True)

        # ===============================
        # Tabela detalhada
        # ===============================
        st.subheader("📋 Detalhamento diário")
        st.dataframe(df_filtrado)

        # ===============================
        # Download do Excel
        # ===============================
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

    except Exception as e:
        st.error("❌ Erro, anexe o relatório com colunas e formato correto.")
        st.caption(f"Detalhe técnico: {e}")

else:
    st.info("⬆️ Envie o arquivo CSV ou Excel para começar a análise.")
