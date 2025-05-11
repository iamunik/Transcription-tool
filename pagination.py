import streamlit as st


# Page Navigation
homepage = st.Page("webpages/homepage.py", title="About Project", icon=":material/info:")
delivery_page = st.Page("webpages/app.py", title="Transcription", icon=":material/local_hospital:")

pg = st.navigation([homepage, delivery_page,])

pg.run()
