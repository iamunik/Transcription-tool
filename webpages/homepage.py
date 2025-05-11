import streamlit as st
from utils import open_picture

# Set page configuration
st.set_page_config(
    page_title="Transcription Tool",
    page_icon="🎙️",
    layout="wide"
)

# Header Section
st.title("Welcome to the TBOG ❤ SEUN VERY MUCH TRANSCRIPTION TOOL")
st.markdown("### 🎙️ Convert audio files or YouTube videos into text effortlessly! 🚀")
st.markdown(f"""
<img style="border: 2px solid powderblue" src="data:image/jpeg;base64,{open_picture("transcription_banner.jpg")}" width="60%"><br>
""", unsafe_allow_html=True)


# Overview Section
st.markdown("""
### 📝 Overview
This transcription tool allows you to:
- Extract text from audio files in formats like MP3, WAV, M4A, and OPUS.
- Download and transcribe audio from YouTube videos.
- Split large audio files into smaller chunks for efficient processing.
- Download transcriptions as a ZIP file.

---

### 🌟 Key Features
- **Fast and Accurate**: Powered by advanced machine learning models.
- **User-Friendly Interface**: Simple and intuitive design for seamless use.
- **Multiple Input Options**: Upload audio files or provide YouTube links.
- **Secure**: All processing is done locally, ensuring data privacy.

---

### 🔄 How It Works
1. Choose an input type: YouTube link or audio file upload.
2. Process the audio to generate text transcriptions.
3. Download the results in a convenient ZIP format.
""")
