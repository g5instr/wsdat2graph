import streamlit as st

st.set_page_config(page_title="Conversor de arquivos CSV WS", layout="wide")

st.title("🏠 Conversor de arquivos CSV WS")
st.write("Selecione uma das opções abaixo:")

st.page_link("pages/leituraCompacted_vw.py", label="Gráficos de arquivo csv (Corda Vibrante - 4 horas)")
st.page_link("pages/lerCompacted_tm.py", label="Gráficos de arquivo csv (Tiltímetros - 2 minutos)")
