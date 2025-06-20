import streamlit as st
from admin import show_admin
from live import show_live
from ranking import show_ranking
from giudice import show_giudice

# ✅ Questa deve essere la PRIMA istruzione Streamlit
st.set_page_config(page_title="GymPoints", layout="wide")

params = st.query_params
admin_code = params.get("admin", "")
giudice_code = params.get("giudice", "")

if giudice_code:
    show_giudice()
elif admin_code == "1234":
    show_admin()
else:
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Vai a:", ["Live Gara", "Classifica Generale"])
    if page == "Live Gara":
        show_live()
    elif page == "Classifica Generale":
        show_ranking()
