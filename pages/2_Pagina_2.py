import streamlit as st

st.set_page_config(page_title="Página 2", layout="wide")

st.title("🧩 Página 2")

arquivos_enviados = st.file_uploader(
    "Envie um ou mais arquivos CSV",
    type="csv",
    accept_multiple_files=True,
    key="upload_pagina_2",
)

if not arquivos_enviados:
    st.info("Envie um ou mais arquivos CSV acima para começar.")
else:
    st.info("Upload recebido. Substitua este trecho pelo processamento desejado para este programa.")
    for arquivo in arquivos_enviados:
        st.write(f"📄 {arquivo.name} — {arquivo.size} bytes")
