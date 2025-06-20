import os
import shutil
import streamlit as st
from load_whisper import load_and_save_model
from utils import process_audio_input, create_zip_file
import tempfile
import time

MODEL_DIR = "whisper_models"
os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    st.set_page_config(page_title="Transcription Tool",
                       page_icon="🎙️",
                       layout="wide")
    st.title("TRANSCRIPTION TOOL")

    model = load_and_save_model(model_dir=MODEL_DIR)
    tabs = ["YouTube Link", "Upload Audio"]
    tab = st.sidebar.radio("Select Input Type", tabs)

    with tempfile.TemporaryDirectory(prefix="session_") as session_temp_dir:
        try:
            if tab == "YouTube Link":
                youtube_url = st.text_input("Enter YouTube Video URL", placeholder="https://www.youtube.com/watchOG")
                if st.button("Download and Transcribe"):
                    with st.spinner("Processing YouTube link..."):
                        transcription_dir = process_audio_input("YouTube", youtube_url, model, session_temp_dir)
                        if transcription_dir:
                            zip_path = create_zip_file(transcription_dir, "transcription_output", session_temp_dir)
                            if os.path.exists(zip_path):
                                st.success("Transcription completed successfully!")
                                with open(zip_path, "rb") as f:
                                    st.download_button("Download Transcription ZIP", f, file_name="transcription_output.zip")
                            else:
                                st.error("Failed to create ZIP file.")

            elif tab == "Upload Audio":
                uploaded_files = st.file_uploader("Upload Audio Files", type=["mp3", "wav", "opus", "m4a"],
                                                  accept_multiple_files=True)
                if uploaded_files and st.button("Upload and Transcribe"):
                    with st.spinner("Processing uploaded files..."):
                        combined_transcription_dir = os.path.join(session_temp_dir, "combined_transcriptions")
                        os.makedirs(combined_transcription_dir, exist_ok=True)

                        for file in uploaded_files:
                            transcription_dir = process_audio_input("Upload", file, model, session_temp_dir)
                            if transcription_dir:
                                for f in os.listdir(transcription_dir):
                                    shutil.move(os.path.join(transcription_dir, f), combined_transcription_dir)

                        if os.listdir(combined_transcription_dir):
                            zip_path = create_zip_file(combined_transcription_dir, "all_transcriptions", session_temp_dir)
                            if os.path.exists(zip_path):
                                st.success("Transcription completed successfully!")
                                with open(zip_path, "rb") as f:
                                    st.download_button("Download All Transcriptions", f, file_name="all_transcriptions.zip")
                            else:
                                st.error("Failed to create ZIP file.")
                        else:
                            st.error("No transcriptions found.")
        finally:
            # No need to manually clean up, TemporaryDirectory handles it
            pass

if __name__ == "__main__":
    start = time.time()
    main()
    end = time.time()
    print(start-end, "seconds")