import streamlit as st

st.set_page_config(page_title="Painel de Ferramentas", layout="wide")

st.title("🏠 Painel de Ferramentas")
st.write("Selecione uma das opções abaixo:")

st.page_link("pages/leituraCompacted_vw.py", label="📊 Gráficos de arquivo csv (Corda Vibrante)", icon="📊")
st.page_link("pages/lerCompacted_tm.py", label="🧩 Gráficos de arquivo csv (Tiltímetros)", icon="🧩")
