import io
import math
import re
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
st.title("Análise de Leituras - Tiltímetros, scan = 2 minutos")

# Campo para inserção manual do número de dias abrangidos pela leitura.
# Usado para estimar a quantidade total de leituras esperadas (considerando
# amostragem a cada 2 minutos) e, a partir daí, calcular a % de células
# vazias na tabela de métricas de resumo.
n_dias = st.number_input("Nº de dias para o cálculo da disponibilidade", min_value=1, step=1, value=1)
n_dias = int(n_dias)
quantidade_minutos = n_dias * 24 * 60
metade_minutos = quantidade_minutos / 2

# Campo Interativo para Arrastar e Soltar o Arquivo
uploaded_file = st.file_uploader(
    "Arraste e solte o seu arquivo de origem aqui (.dat ou .csv)",
    type=["dat", "csv"]
)

# O script só executa se houver um arquivo carregado pelo usuário
if uploaded_file is not None:
    try:
        # Lendo o arquivo diretamente do buffer do Streamlit
        df1 = pd.read_csv(uploaded_file, skiprows=1)
        df2 = df1.drop(columns=['RECORD'], errors='ignore')

        # Converte TIMESTAMP para datetime e filtra leituras a cada 2 minutos.
        # Pressupõe que a base original registra leituras com resolução de
        # 1 em 1 minuto; se a granularidade de origem for diferente, o
        # critério de filtragem abaixo precisa ser ajustado.
        df2['TIMESTAMP'] = pd.to_datetime(df2['TIMESTAMP'])
        df_filtered = df2[df2['TIMESTAMP'].dt.minute % 2 == 0].copy()

        # Identifica todas as colunas de dados (ignorando a coluna de tempo TIMESTAMP)
        all_data_cols = [col for col in df_filtered.columns if col != 'TIMESTAMP']

        # Identifica pares X/Y a partir do nome da coluna.
        # Ex: 'XaxisVariation-92740-V1-TM-10A' e 'YaxisVariation-92740-V1-TM-10A'
        # formam um par pela chave comum 'Variation-92740-V1-TM-10A'.
        # Colunas iniciadas por outra letra (ex: 'Zaxis...') são ignoradas.
        padrao_xy = re.compile(r'^([XY])axis(.*)$', re.IGNORECASE)

        grupos_xy = {}
        for col in all_data_cols:
            m = padrao_xy.match(col)
            if m:
                eixo = m.group(1).upper()
                chave = m.group(2)
                grupos_xy.setdefault(chave, {})[eixo] = col

        # Só forma o par se existirem as duas colunas (X e Y) para a mesma chave.
        # Regra de Omissão: descarta o par apenas se AMBAS as colunas estiverem vazias.
        pares_xy = []
        for chave, eixos in grupos_xy.items():
            col_x = eixos.get('X')
            col_y = eixos.get('Y')
            if not col_x or not col_y:
                continue

            x_vazia = df_filtered[col_x].isna().all()
            y_vazia = df_filtered[col_y].isna().all()

            if not (x_vazia and y_vazia):
                pares_xy.append((chave, col_x, col_y))

        num_rows_plotly = len(pares_xy)

        if num_rows_plotly == 0:
            st.warning("Nenhum par X/Y válido encontrado. Verifique se as colunas seguem o padrão 'Xaxis...' / 'Yaxis...'.")
        else:
            # ==================================================================
            # 2. METRICAS DE RESUMO NA TELA (COLUNAS X E Y)
            # ==================================================================
            st.subheader("📊 Métricas de Resumo (Colunas X/Y)")

            resumo_data = []
            for chave, col_x, col_y in pares_xy:
                for eixo, col in (('X', col_x), ('Y', col_y)):
                    if not df_filtered[col].isna().all():
                        v_min = df_filtered[col].min()
                        v_max = df_filtered[col].max()
                        diff = v_max - v_min
                        # Ausência de leituras = esperado (com base nos dias informados) menos
                        # leituras realmente presentes e válidas nessa coluna. Isso cobre tanto
                        # células vazias (NaN) em linhas existentes quanto timestamps inteiros
                        # que nem chegaram a existir no arquivo.
                        qtd_presente = df_filtered[col].notna().sum()
                        qtd_ausente = max(metade_minutos - qtd_presente, 0)
                        perc_em_branco = (qtd_ausente / metade_minutos * 100) if metade_minutos > 0 else 0

                        resumo_data.append({
                            "Variável": col,
                            "Eixo": eixo,
                            "Valor Mínimo": v_min,
                            "Valor Máximo": v_max,
                            "Diferença": diff,
                            "% Células em Branco": perc_em_branco
                        })

            df_resumo = pd.DataFrame(resumo_data)

            if not df_resumo.empty:
                # Exibe a tabela formatada no painel web
                df_estilizado = df_resumo.style.format({
                    "Valor Mínimo": "{:.2f}",
                    "Valor Máximo": "{:.2f}",
                    "Diferença": "{:.2f}",
                    "% Células em Branco": "{:.1f}%"
                })
                st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma coluna X/Y com dados válidos para exibir no resumo.")

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
                estilo_resumo_html = df_resumo.style.format({
                    "Valor Mínimo": "{:.2f}",
                    "Valor Máximo": "{:.2f}",
                    "Diferença": "{:.2f}",
                    "% Células em Branco": "{:.1f}%"
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
<h2 style="font-family: Arial, sans-serif;">Relatório Técnico - Resumo Estatístico (X/Y)</h2>
{estilo_resumo_html.to_html()}
</body>
</html>"""

                st.download_button(
                    label="📥 Baixar Resumo Estatístico (HTML)",
                    data=resumo_html.encode('utf-8'),
                    file_name='tm_resumo.html',
                    mime="text/html",
                    key="download_html_resumo"
                )

            # ==================================================================
            # 2.2 COMPILAÇÃO DO RELATÓRIO PDF (A4 - GRÁFICOS X/Y, 2 LINHAS POR PAR)
            # ==================================================================
            pdf_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:
                plots_per_page = 8
                pdf_rows, pdf_cols = 4, 2
                total_pages_graphs = math.ceil(len(pares_xy) / plots_per_page)

                for page_num in range(total_pages_graphs):
                    fig_mpl, axes = plt.subplots(pdf_rows, pdf_cols, figsize=(a4_w, a4_h))
                    plt.subplots_adjust(hspace=0.5, wspace=0.3, top=0.92, bottom=0.05, left=0.1, right=0.9)
                    fig_mpl.suptitle(f"Relatório Técnico - Gráficos X/Y (Pág. {page_num + 1})", fontsize=12, fontweight='bold')
                    axes_flat = axes.flatten()

                    for plot_idx in range(plots_per_page):
                        global_idx = (page_num * plots_per_page) + plot_idx
                        ax = axes_flat[plot_idx]

                        if global_idx < len(pares_xy):
                            chave, col_x, col_y = pares_xy[global_idx]
                            x_tem_dados = not df_filtered[col_x].isna().all()
                            y_tem_dados = not df_filtered[col_y].isna().all()

                            if x_tem_dados or y_tem_dados:
                                if x_tem_dados:
                                    ax.plot(df_filtered['TIMESTAMP'], df_filtered[col_x], marker='o', markersize=2, color='tab:blue', linewidth=1, label='X')
                                if y_tem_dados:
                                    ax.plot(df_filtered['TIMESTAMP'], df_filtered[col_y], marker='o', markersize=2, color='tab:red', linewidth=1, label='Y')
                                ax.set_title(chave, fontsize=7, fontweight='semibold')
                                ax.grid(True, linestyle='--', alpha=0.5)
                                # Omitir marcações do eixo X (Datas) no PDF
                                ax.get_xaxis().set_visible(False)
                                ax.tick_params(axis='y', labelsize=7)
                                ax.legend(fontsize=6, loc='upper right')
                            else:
                                ax.set_title(f"{chave} (Sem Dados)", fontsize=7, color='gray', fontstyle='italic')
                                ax.grid(True, linestyle=':', alpha=0.3)
                                ax.get_xaxis().set_visible(False)
                                ax.get_yaxis().set_visible(False)
                        else:
                            ax.axis('off')

                    pdf.savefig(fig_mpl, dpi=300)
                    plt.close(fig_mpl)

            pdf_buffer.seek(0)
            st.download_button(
                label="📥 Baixar Relatório PDF de Gráficos",
                data=pdf_buffer,
                file_name='tm_graficos.pdf',
                mime="application/pdf",
                key="download_pdf"
            )

            # ==================================================================
            # 3. DASHBOARD INTERATIVO NA TELA (STREAMLIT/PLOTLY) - 2 LINHAS POR PAR
            # ==================================================================
            st.subheader("📈 Visualização Interativa")

            subplot_titles = [chave for chave, _, _ in pares_xy]

            fig = make_subplots(
                rows=num_rows_plotly,
                cols=1,
                subplot_titles=subplot_titles,
                shared_xaxes=True
            )

            for idx, (chave, col_x, col_y) in enumerate(pares_xy):
                row_num = idx + 1
                if not df_filtered[col_x].isna().all():
                    fig.add_trace(
                        go.Scatter(
                            x=df_filtered['TIMESTAMP'], y=df_filtered[col_x], mode='lines+markers',
                            name='X', legendgroup='X', line=dict(color='royalblue'),
                            showlegend=(idx == 0)
                        ),
                        row=row_num, col=1
                    )
                if not df_filtered[col_y].isna().all():
                    fig.add_trace(
                        go.Scatter(
                            x=df_filtered['TIMESTAMP'], y=df_filtered[col_y], mode='lines+markers',
                            name='Y', legendgroup='Y', line=dict(color='firebrick'),
                            showlegend=(idx == 0)
                        ),
                        row=row_num, col=1
                    )

            altura_dinamica = max(600, num_rows_plotly * 300)
            fig.update_layout(height=altura_dinamica, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo enviado: {e}")
else:
    st.info("Aguardando o upload do arquivo para gerar as métricas, gráficos e relatórios.")
