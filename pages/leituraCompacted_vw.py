import io
import math
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from matplotlib.backends.backend_pdf import PdfPages
from plotly.subplots import make_subplots

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(layout="wide")
st.title("Análise de Leituras - Corda Vibrante")

# Campo Interativo para Arrastar e Soltar o Arquivo
uploaded_file = st.file_uploader(
    "Arraste e solte o seu arquivo de origem aqui (.dat ou .csv)",
    type=["dat", "csv"]
)

# Quantidade de dias usada como referência para calcular a disponibilidade
quantidade_dias = st.number_input(
    "Quantidade de dias (referência para cálculo de disponibilidade)",
    min_value=1,
    value=30,
    step=1
)
CICLOS_POR_DIA = 6  # leituras a cada 4 horas: 01h, 05h, 09h, 13h, 17h, 21h

# O script só executa se houver um arquivo carregado pelo usuário
if uploaded_file is not None:
    try:
        # Lendo o arquivo diretamente do buffer do Streamlit
        df1 = pd.read_csv(uploaded_file, skiprows=1)
        df2 = df1.drop(columns=['RECORD'], errors='ignore')

        # Filtragem de horários específicos (de 4 em 4 horas)
        df_filtered = df2[df2['TIMESTAMP'].str.contains('01:00|05:00|09:00|13:00|17:00|21:00', na=False)].copy()

        # Identifica todas as colunas de dados (ignorando a coluna de tempo TIMESTAMP)
        all_data_cols = [col for col in df_filtered.columns if col != 'TIMESTAMP']

        # Mapeamento de pares consecutivos originais (Coluna Ímpar e Coluna Par seguinte)
        pares_consecutivos = []
        for idx in range(0, len(all_data_cols), 2):
            col_impar = all_data_cols[idx]
            col_par = all_data_cols[idx + 1] if (idx + 1) < len(all_data_cols) else None
            pares_consecutivos.append((col_impar, col_par))

        # Regra de Omissão: Remove o par APENAS se ambas as colunas consecutivas estiverem vazias
        pares_validos = []
        for c_impar, c_par in pares_consecutivos:
            impar_vazia = df_filtered[c_impar].isna().all()
            par_vazia = df_filtered[c_par].isna().all() if c_par else True

            if not (impar_vazia and par_vazia):
                pares_validos.append((c_impar, c_par))

        num_rows_plotly = len(pares_validos)

        if num_rows_plotly == 0:
            st.warning("Nenhum dado válido encontrado. Todos os pares de colunas consecutivas estão vazios.")
        else:
            # ==================================================================
            # 2. METRICAS DE RESUMO NA TELA (APENAS COLUNAS ÍMPARES)
            # ==================================================================
            st.subheader("📊 Métricas de Resumo (Corda Vibrante)")

            ciclos_esperados = quantidade_dias * CICLOS_POR_DIA

            resumo_data = []
            for c_impar, _ in pares_validos:
                if c_impar and not df_filtered[c_impar].isna().all():
                    v_min = df_filtered[c_impar].min()
                    v_max = df_filtered[c_impar].max()
                    diff = v_max - v_min
                    qtd_valida = df_filtered[c_impar].notna().sum()
                    disponibilidade = (qtd_valida / ciclos_esperados * 100) if ciclos_esperados > 0 else 0

                    resumo_data.append({
                        "Variável Ímpar": c_impar,
                        "Valor Mínimo": v_min,
                        "Valor Máximo": v_max,
                        "Diferença": diff,
                        "Disponibilidade (%)": disponibilidade
                    })

            df_resumo = pd.DataFrame(resumo_data)

            if not df_resumo.empty:
                # Exibe a tabela formatada no painel web
                df_estilizado = df_resumo.style.format({
                    "Valor Mínimo": "{:.2f}",
                    "Valor Máximo": "{:.2f}",
                    "Diferença": "{:.2f}",
                    "Disponibilidade (%)": "{:.1f}%"
                })
                st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma coluna ímpar com dados válidos para exibir no resumo.")

            excel_buffer = io.BytesIO()
            df_filtered.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            st.download_button(
                label="📥 Baixar Dados Filtrados (Excel)",
                data=excel_buffer,
                file_name='vw.xlsx',
                key="download_excel"
            )

            # ==================================================================
            # 2.1 RESUMO ESTATÍSTICO PARA DOWNLOAD (ARQUIVO HTML SEPARADO)
            # ==================================================================
            a4_w, a4_h = 8.27, 11.69

            if not df_resumo.empty:
                # Reaproveita a mesma formatação usada na tabela exibida na tela
                estilo_resumo_html = df_resumo.style.format({
                    "Valor Mínimo": "{:.2f}",
                    "Valor Máximo": "{:.2f}",
                    "Diferença": "{:.2f}",
                    "Disponibilidade (%)": "{:.1f}%"
                }).set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', '#4f81bd'),
                        ('color', 'white'),
                        ('padding', '8px'),
                        ('text-align', 'center')
                    ]},
                    {'selector': 'td', 'props': [
                        ('padding', '8px'),
                        ('text-align', 'center'),
                        ('border', '1px solid #ddd')
                    ]}
                ]).set_table_attributes('style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;"') \
                  .hide(axis='index')

                resumo_html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Relatório Técnico - Resumo Estatístico</title>
</head>
<body>
<h2 style="font-family: Arial, sans-serif;">Relatório Técnico - Resumo Estatístico (Ímpares)</h2>
{estilo_resumo_html.to_html()}
</body>
</html>"""

                st.download_button(
                    label="📥 Baixar Resumo Estatístico (HTML)",
                    data=resumo_html.encode('utf-8'),
                    file_name='vw_resumo.html',
                    mime="text/html",
                    key="download_html_resumo"
                )

            # ==================================================================
            # 2.2 COMPILAÇÃO DO RELATÓRIO PDF (A4 - APENAS GRÁFICOS)
            # ==================================================================
            pdf_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:
                # --------------------------------------------------------------
                # PDF: Grid de Gráficos (Compactado em 4x2 = 8 por folha)
                # --------------------------------------------------------------
                colunas_totais_pdf = []
                for c_impar, c_par in pares_validos:
                    colunas_totais_pdf.append((c_impar, False if df_filtered[c_impar].isna().all() else True))
                    if c_par:
                        colunas_totais_pdf.append((c_par, False if df_filtered[c_par].isna().all() else True))
                    else:
                        colunas_totais_pdf.append((None, False))

                plots_per_page = 8
                pdf_rows, pdf_cols = 4, 2
                total_pages_graphs = math.ceil(len(colunas_totais_pdf) / plots_per_page)

                for page_num in range(total_pages_graphs):
                    fig_mpl, axes = plt.subplots(pdf_rows, pdf_cols, figsize=(a4_w, a4_h))
                    plt.subplots_adjust(hspace=0.5, wspace=0.3, top=0.92, bottom=0.05, left=0.1, right=0.9)
                    fig_mpl.suptitle(f"Relatório Técnico - Gráficos (Pág. {page_num + 1})", fontsize=12, fontweight='bold')
                    axes_flat = axes.flatten()

                    for plot_idx in range(plots_per_page):
                        global_idx = (page_num * plots_per_page) + plot_idx
                        ax = axes_flat[plot_idx]

                        if global_idx < len(colunas_totais_pdf):
                            col_name, tem_dados = colunas_totais_pdf[global_idx]

                            if col_name and tem_dados:
                                ax.plot(df_filtered['TIMESTAMP'], df_filtered[col_name], marker='o', markersize=3, color='tab:blue', linewidth=1)
                                ax.set_title(col_name, fontsize=8, fontweight='semibold')
                                ax.grid(True, linestyle='--', alpha=0.5)
                                # Omitir legendas e marcações do eixo X (Datas) no PDF
                                ax.get_xaxis().set_visible(False)
                                ax.tick_params(axis='y', labelsize=8)
                            elif col_name and not tem_dados:
                                ax.set_title(f"{col_name} (Sem Dados)", fontsize=8, color='gray', fontstyle='italic')
                                ax.grid(True, linestyle=':', alpha=0.3)
                                ax.get_xaxis().set_visible(False)
                                ax.get_yaxis().set_visible(False)
                            else:
                                ax.axis('off')
                        else:
                            ax.axis('off')

                    pdf.savefig(fig_mpl, dpi=300)
                    plt.close(fig_mpl)

            pdf_buffer.seek(0)
            st.download_button(
                label="📥 Baixar Relatório PDF de Gráficos",
                data=pdf_buffer,
                file_name='vw_graficos.pdf',
                mime="application/pdf",
                key="download_pdf"
            )

            # ==================================================================
            # 3. DASHBOARD INTERATIVO NA TELA (STREAMLIT/PLOTLY)
            # ==================================================================
            st.subheader("📈 Visualização Interativa")

            subplot_titles = []
            for c_impar, c_par in pares_validos:
                subplot_titles.extend([c_impar, c_par if c_par else ""])

            fig = make_subplots(
                rows=num_rows_plotly,
                cols=2,
                subplot_titles=subplot_titles,
                shared_xaxes=True
            )

            for idx, (c_impar, c_par) in enumerate(pares_validos):
                row_num = idx + 1
                if not df_filtered[c_impar].isna().all():
                    fig.add_trace(
                        go.Scatter(x=df_filtered['TIMESTAMP'], y=df_filtered[c_impar], mode='lines+markers', name=c_impar),
                        row=row_num, col=1
                    )
                if c_par and not df_filtered[c_par].isna().all():
                    fig.add_trace(
                        go.Scatter(x=df_filtered['TIMESTAMP'], y=df_filtered[c_par], mode='lines+markers', name=c_par),
                        row=row_num, col=2
                    )

            altura_dinamica = max(600, num_rows_plotly * 300)
            fig.update_layout(height=altura_dinamica, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo enviado: {e}")
else:
    st.info("Aguardando o upload do arquivo para gerar as métricas, gráficos e relatórios.")
