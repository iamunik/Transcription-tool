import streamlit as st

ffmpeg_dir = os.path.join(os.path.dirname(__file__), "bin")
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Page Navigation
homepage = st.Page("webpages/homepage.py", title="About Project", icon=":material/info:")
delivery_page = st.Page("webpages/app.py", title="Transcription", icon=":material/local_hospital:")

pg = st.navigation([homepage, delivery_page,])

pg.run()
