import io
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

st.set_page_config(layout="wide")
st.title("📊 Gráficos de arquivos health")

with st.sidebar:
    st.header("Configurações")
    linhas_pular = st.number_input("Linhas de cabeçalho a pular", min_value=0, value=9, step=1)
    num_colunas_layout = st.number_input("Gráficos por linha", min_value=1, max_value=4, value=1, step=1)

arquivos_enviados = st.file_uploader(
    "Envie um ou mais arquivos CSV",
    type="csv",
    accept_multiple_files=True,
)


@st.cache_data(show_spinner=False)
def carregar_csv(conteudo_bytes: bytes, skiprows: int) -> pd.DataFrame:
    """Lê o CSV a partir dos bytes enviados, tentando combinações comuns de encoding/separador."""
    tentativas = [
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ";", "encoding": "utf-8"},
        {"sep": ",", "encoding": "latin1"},
        {"sep": ";", "encoding": "latin1"},
    ]
    ultimo_erro = None
    for opcoes in tentativas:
        try:
            df = pd.read_csv(io.BytesIO(conteudo_bytes), skiprows=skiprows, **opcoes)
            if df.shape[1] >= 4:
                return df
        except Exception as e:
            ultimo_erro = e
            continue
    if ultimo_erro:
        raise ultimo_erro
    raise ValueError("Não foi possível ler o arquivo com as combinações testadas.")


def preparar_dados(df: pd.DataFrame):
    """Seleciona 1ª e 4ª colunas, converte Y para numérico e ordena por X."""
    dados = df.iloc[:, [0, 3]].copy()
    col_x, col_y = dados.columns[0], dados.columns[1]

    if dados[col_y].dtype == object:
        dados[col_y] = (
            dados[col_y]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
    dados[col_y] = pd.to_numeric(dados[col_y], errors="coerce")

    try:
        dados[col_x] = pd.to_datetime(dados[col_x])
    except Exception:
        pass

    dados = dados.set_index(col_x).sort_index()
    return dados, col_x, col_y


def contar_valor(df: pd.DataFrame, valor: int) -> int:
    """Conta em quantas células da 4ª coluna (índice 3) o valor aparece."""
    if df.shape[1] < 4:
        return 0
    serie = df.iloc[:, 3]
    numerica = pd.to_numeric(serie, errors="coerce")
    return int((numerica == valor).sum())


def gerar_pdf(arquivos: list, skiprows: int) -> bytes:
    """Gera um PDF em A4 com 2 gráficos por página (um embaixo do outro).
    'arquivos' é uma lista de tuplas (nome_arquivo, conteudo_bytes)."""
    A4_LARGURA_POL, A4_ALTURA_POL = 8.27, 11.69
    GRAFICOS_POR_PAGINA = 2

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        for i in range(0, len(arquivos), GRAFICOS_POR_PAGINA):
            grupo = arquivos[i : i + GRAFICOS_POR_PAGINA]
            fig, axes = plt.subplots(
                GRAFICOS_POR_PAGINA, 1,
                figsize=(A4_LARGURA_POL, A4_ALTURA_POL),
            )

            for idx_ax, ax in enumerate(axes):
                if idx_ax >= len(grupo):
                    ax.axis("off")
                    continue

                nome_arquivo, conteudo_bytes = grupo[idx_ax]
                try:
                    df = carregar_csv(conteudo_bytes, skiprows)
                    if df.shape[1] < 4:
                        ax.text(0.5, 0.5, "Arquivo com menos de 4 colunas", ha="center")
                    else:
                        dados_filtrados, col_x, col_y = preparar_dados(df)
                        dados_filtrados.plot(ax=ax, legend=False)
                        ax.set_xlabel(col_x, fontsize=8)
                        ax.set_ylabel(col_y, fontsize=8)
                        ax.tick_params(labelsize=7)
                except Exception as e:
                    ax.text(0.5, 0.5, f"Erro: {e}", ha="center", wrap=True)

                ax.set_title(nome_arquivo, fontsize=10)

            fig.tight_layout(pad=3)
            pdf.savefig(fig)
            plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


VALOR_PROCURADO = 25201

if not arquivos_enviados:
    st.info("Envie um ou mais arquivos CSV acima para começar.")
else:
    # (nome_arquivo, bytes) para cada arquivo enviado
    arquivos_dados = [(arq.name, arq.getvalue()) for arq in arquivos_enviados]

    # --- Tabela resumo: contagem do valor 25201 por arquivo ---
    resumo = []
    for nome_arquivo, conteudo_bytes in arquivos_dados:
        try:
            df_resumo = carregar_csv(conteudo_bytes, linhas_pular)
            qtd = contar_valor(df_resumo, VALOR_PROCURADO)
        except Exception:
            qtd = None
        resumo.append({"arquivo": nome_arquivo, "uptime reset": qtd})

    st.subheader(f"🔎 Ocorrências do valor {VALOR_PROCURADO}")
    st.dataframe(pd.DataFrame(resumo), use_container_width=True)

    with st.spinner("Gerando PDF com os gráficos..."):
        pdf_bytes = gerar_pdf(arquivos_dados, linhas_pular)

    st.download_button(
        label="📥 Baixar gráficos em PDF",
        data=pdf_bytes,
        file_name="graficos_health.pdf",
        mime="application/pdf",
    )
    st.divider()

    for i in range(0, len(arquivos_dados), num_colunas_layout):
        grupo_arquivos = arquivos_dados[i : i + num_colunas_layout]
        cols = st.columns(num_colunas_layout)

        for idx, (nome_arquivo, conteudo_bytes) in enumerate(grupo_arquivos):
            with cols[idx]:
                st.subheader(f"📄 {nome_arquivo}")
                try:
                    df = carregar_csv(conteudo_bytes, linhas_pular)

                    if df.shape[1] < 4:
                        st.error("O arquivo possui menos de 4 colunas.")
                        continue

                    dados_filtrados, col_x, col_y = preparar_dados(df)

                    if dados_filtrados[col_y].isna().all():
                        st.error(f"Coluna '{col_y}' não pôde ser convertida para número.")
                        continue

                    st.line_chart(dados_filtrados)
                    st.caption(f"**X:** {col_x}  |  **Y:** {col_y}")

                except Exception as e:
                    st.error(f"Erro ao processar arquivo ({type(e).__name__}): {e}")
