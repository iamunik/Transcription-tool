# 🧠 Audio Transcription Tool

A powerful and privacy-conscious transcription tool built with **Streamlit** and **OpenAI Whisper**, designed to extract text from audio files or YouTube videos with ease. Ideal for podcasts, interviews, lectures, and more.

---

## 🚀 Features

- 🎧 Transcribe audio files in MP3, WAV, M4A, OPUS formats
- 📺 Extract and transcribe audio from YouTube links
- ✂️ Automatically split long audio files for smooth processing
- 💬 Uses locally stored **OpenAI Whisper** base model for transcription
- 🧰 Built with Python, Streamlit, `ffmpeg`, and `yt-dlp`
- 🔐 Privacy-first: all processing is handled on-device/server

---

## 📂 Project Structure

```
/bin/
  └── ffmpeg                  
/image/                      
/temp/                        
/webpages/
  ├── app.py                  
  └── homepage.py             

pagination.py                 # Main entry point (Streamlit app)
utils.py                      # Core utility functions (splitting, downloading, etc.)
load_whisper.py               # Whisper model loader 
requirements.txt              # Python dependencies
```

---

## 🛠 Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/iamunik/transcription-tool.git
   cd transcription-tool
   ```

2. **Create a virtual environment** (optional but recommended)  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**  
   ```bash
   streamlit run pagination.py
   ```

---

## 📦 Deployment

Deployed via **[Streamlit Cloud](https://streamlit.io/cloud)**.

- `ffmpeg` is bundled under `/bin/ffmpeg` and made executable at runtime.
- No external API keys or secrets are required.
- Temporary files are stored in `/temp/` during the session and discarded automatically.

---

## 🧠 Model

- Uses `faster-whisper` (base) model for transcription.
- Model is stored locally — no API call is made to OpenAI.
- Whisper is loaded through `load_whisper.py`.

---

## 📌 Roadmap

- ✅ YouTube audio transcription
- ✅ Audio chunking with `ffmpeg`
- ✅ Download transcriptions as ZIP
- ⏳ Add support for other social media platforms (TikTok, Instagram)
- ⏳ Improve transcription speed and parallelism
- ⏳ Transition to a full web framework (e.g., FastAPI + React or Flask)

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repo
2. Create a new branch (`feature/improve-speed`)
3. Commit and push your changes
4. Open a pull request

Please ensure your code is clean and documented.

---

## 📃 License

MIT License — feel free to use, modify, and share.

---

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io)
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org)

---