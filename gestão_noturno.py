import pandas as pd
import streamlit as st
from io import BytesIO

# ================================
# Funções auxiliares
# ================================

def hours_to_hhmm(hours_float):
    """Converte horas (float) para string 'HH:MM'."""
    if pd.isna(hours_float):
        return ""
    total_seconds = int(round(hours_float * 3600))
    if total_seconds < 0:
        total_seconds = 0
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"

def classify_action(ap_text):
    """Classifica o Access Point do galpão em ENTRADA / SAIDA."""
    s = str(ap_text).lower()
    if 'entrada' in s:
        return 'ENTRADA'
    if 'saida' in s or 'saída' in s:
        return 'SAIDA'
    return None

def analyze_logs(df):
    """
    Calcula tempos dentro e fora do galpão (por pessoa e por dia),
    aplicando ajuste de 1h20 caso tempo fora > 1h20.
    Gera também o detalhamento dos intervalos.
    """
    df = df.copy()
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time'])
    df['Data'] = df['Time'].dt.date

    group_cols = []
    if 'Person' in df.columns:
        group_cols.append('Person')
    group_cols.append('Data')

    resultados = []
    detalhes = []

    for grp_values, grupo in df.groupby(group_cols):
        if isinstance(grp_values, tuple):
            key = dict(zip(group_cols, grp_values))
        else:
            key = {group_cols[0]: grp_values}

        time_min = grupo['Time'].min()
        time_max = grupo['Time'].max()
        tempo_empresa_h = (time_max - time_min).total_seconds() / 3600.0 if pd.notna(time_min) and pd.notna(time_max) else 0.0

        # Filtrar galpão
        mask_galpao = grupo['Access Point'].astype(str).str.contains('galp', case=False, na=False)
        gal = grupo.loc[mask_galpao].copy()

        if gal.empty:
            resultados.append({
                **key,
                'Tempo_Empresa_HH:MM': hours_to_hhmm(tempo_empresa_h),
                'Tempo_Dentro_HH:MM': hours_to_hhmm(0.0),
                'Tempo_Fora_Total_HH:MM': hours_to_hhmm(tempo_empresa_h),
                'Tempo_Fora_Ajustado_HH:MM': hours_to_hhmm(tempo_empresa_h - 1.333 if tempo_empresa_h > 1.333 else tempo_empresa_h),
                'Descontou_Almoco': 'SIM' if tempo_empresa_h > 1.333 else 'NÃO'
            })
            continue

        # Classificação
        gal['Acao'] = gal['Access Point'].apply(classify_action)
        gal = gal.sort_values('Time').reset_index(drop=True)
        gal['Fim'] = gal['Time'].shift(-1)
        gal['Duracao_h'] = (gal['Fim'] - gal['Time']).dt.total_seconds() / 3600.0

        tempo_dentro_h = gal.loc[gal['Acao']=='ENTRADA', 'Duracao_h'].sum()
        tempo_fora_interno_h = gal.loc[gal['Acao']=='SAIDA', 'Duracao_h'].sum()

        entradas = gal[gal['Acao']=='ENTRADA']
        saidas = gal[gal['Acao']=='SAIDA']

        tempo_before_first_h = 0.0
        tempo_after_last_h = 0.0

        if not entradas.empty:
            primeira_entrada = entradas['Time'].iloc[0]
            if primeira_entrada > time_min:
                tempo_before_first_h = (primeira_entrada - time_min).total_seconds() / 3600.0

        if not saidas.empty:
            ultima_saida = saidas['Time'].iloc[-1]
            if time_max > ultima_saida:
                tempo_after_last_h = (time_max - ultima_saida).total_seconds() / 3600.0

        # Caso último evento seja ENTRADA e sem SAIDA
        if gal.iloc[-1]['Acao'] == 'ENTRADA':
            extra_inside = (time_max - gal.iloc[-1]['Time']).total_seconds() / 3600.0
            tempo_dentro_h += max(0, extra_inside)

        tempo_fora_total_h = tempo_fora_interno_h + tempo_before_first_h + tempo_after_last_h

        # Ajuste de almoço (1h20 = 1.333h)
        tempo_fora_ajustado_h = tempo_fora_total_h
        descontou = 'NÃO'
        if tempo_fora_total_h > 1.333:
            tempo_fora_ajustado_h -= 1.333
            descontou = 'SIM'

        resultados.append({
            **key,
            'Tempo_Empresa_HH:MM': hours_to_hhmm(tempo_empresa_h),
            'Tempo_Dentro_HH:MM': hours_to_hhmm(tempo_dentro_h),
            'Tempo_Fora_Total_HH:MM': hours_to_hhmm(tempo_fora_total_h),
            'Tempo_Fora_Ajustado_HH:MM': hours_to_hhmm(tempo_fora_ajustado_h),
            'Descontou_Almoco': descontou
        })

        # Detalhamento
        for _, row in gal.iterrows():
            detalhes.append({
                **key,
                'Horario_Inicio': row['Time'],
                'Horario_Fim': row['Fim'],
                'Acao': row['Acao'],
                'Duracao_h': row['Duracao_h'],
                'Duracao_HH:MM': hours_to_hhmm(row['Duracao_h']),
                'Tipo_Tempo': 'DENTRO' if row['Acao'] == 'ENTRADA' else 'FORA'
            })

        # Adiciona também os intervalos externos
        if tempo_before_first_h > 0:
            detalhes.append({
                **key,
                'Horario_Inicio': time_min,
                'Horario_Fim': primeira_entrada,
                'Acao': 'ANTES PRIMEIRA ENTRADA',
                'Duracao_h': tempo_before_first_h,
                'Duracao_HH:MM': hours_to_hhmm(tempo_before_first_h),
                'Tipo_Tempo': 'FORA'
            })
        if tempo_after_last_h > 0:
            detalhes.append({
                **key,
                'Horario_Inicio': ultima_saida,
                'Horario_Fim': time_max,
                'Acao': 'APOS ULTIMA SAIDA',
                'Duracao_h': tempo_after_last_h,
                'Duracao_HH:MM': hours_to_hhmm(tempo_after_last_h),
                'Tipo_Tempo': 'FORA'
            })

    df_resumo = pd.DataFrame(resultados)
    df_detalhes = pd.DataFrame(detalhes)

    return df_resumo, df_detalhes

# ================================
# INTERFACE STREAMLIT
# ================================

st.title("📊 Validação de Tempo no Galpão (com Almoço de 1h20)")
st.write("Envie seu arquivo de logs (CSV ou Excel) contendo as colunas **Time**, **Access Point**, e opcionalmente **Person**.")

arquivo = st.file_uploader("📂 Carregar arquivo de logs", type=['csv', 'xlsx'])

if arquivo:
    if arquivo.name.endswith('.csv'):
        df = pd.read_csv(arquivo)
    else:
        df = pd.read_excel(arquivo)

    st.success("✅ Arquivo carregado com sucesso!")

    df_resumo, df_detalhes = analyze_logs(df)

    st.subheader("📋 Resumo Diário (por Pessoa e Data)")
    st.dataframe(df_resumo)

    st.subheader("🕓 Detalhamento de Intervalos")
    st.dataframe(df_detalhes.head(30))

    # Exportar para Excel (duas abas)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_resumo.to_excel(writer, index=False, sheet_name='Resumo_Diario')
        df_detalhes.to_excel(writer, index=False, sheet_name='Detalhamento_Intervalos')
    output.seek(0)

    st.download_button(
        label="📥 Baixar Excel Completo (Resumo + Detalhes)",
        data=output,
        file_name="validacao_tempo_galpao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
