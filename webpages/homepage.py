import streamlit as st
from utils import open_picture

st.set_page_config(
    page_title="Transcription Tool",
    page_icon="❤",
    layout="wide"
)

st.title("Welcome to the TBOG ❤ SEUN Audio Transcription Tool")
st.write("""🎙️ Transform your audio and YouTube video content into accurate, readable text in just a few clicks!
            our tool makes transcription fast, private, and effortless. 🚀""")
st.markdown(f"""
<img style="border: 2px solid powderblue" src="data:image/jpeg;base64,{open_picture("transcription_banner.jpg")}" 
width="80%"><br>""", unsafe_allow_html=True)

st.markdown("""
### 🌟 Key Features
- 🎯 **Fast and Accurate**: Uses advanced machine learning models for high-quality transcription.
- 🎧 **Multiple Input Formats**: Supports MP3, WAV, M4A, and OPUS files.
- 📺 **YouTube Support**: Paste a YouTube link to download and transcribe the audio directly.
- ✂️ **Chunk Splitting**: Automatically splits long audio into smaller parts for smoother processing.
- 💾 **Downloadable Output**: Receive your results as a structured ZIP file with individual text files per segment.
- 🔒 **Privacy-First**: All audio is processed within your session — your data is never shared.

---

### 🔄 How It Works

1. **Select Input**  
   Upload an audio file or provide a valid YouTube link.

2. **Processing**  
   The tool splits long audio into manageable chunks, then transcribes each segment using a speech recognition model.

3. **Download Results**  
   When processing completes, download the transcription as a ZIP file containing individual text files.

---

### 🚀 Getting Started

- Click the button to upload your audio or paste a YouTube link.
- Wait a few moments while the tool processes your input.
- Download your transcription once it’s ready!

---

### 💡 Pro Tips

- For best results, use high-quality audio.
- Ensure your YouTube video is not age-restricted or private.
- Large files may take longer — you’ll see progress as it transcribes.

---

Made with ❤️ for Tbog
""")
