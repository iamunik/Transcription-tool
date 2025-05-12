# app.py
import os
import shutil
import streamlit as st
from load_whisper import load_and_save_model
from utils import (
    create_zip_file,
    split_audio,
    handle_youtube_link,
    handle_audio_upload,
    process_and_transcribe_chunks
)
import uuid

# Constants
TEMP_DIR = "debug_temp_dir"
MODEL_DIR = "whisper_models"

# Ensuring that directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    st.set_page_config(page_title="Transcription Tool", layout="wide")
    st.title("TBOG LOVES SEUN VERY MUCH TRANSCRIPTION TOOL")

    # Generate a unique session ID and create a session-specific temp directory
    session_id = str(uuid.uuid4())
    session_temp_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_temp_dir, exist_ok=True)

    # Load the model once
    model = load_and_save_model(model_dir=MODEL_DIR)

    tabs = ["YouTube Link", "Upload Audio"]
    tab = st.sidebar.radio("Select Input Type", tabs)

    try:
        if tab == "YouTube Link":
            youtube_url = st.text_input("Enter YouTube Video URL", "")
            if st.button("Download and Transcribe"):
                if youtube_url:
                    with st.spinner("Downloading and Transcribing..."):
                        audio_path = handle_youtube_link(youtube_url, session_temp_dir)
                        if audio_path and split_audio(audio_path, session_temp_dir):
                            split_audio_folder = os.path.join(session_temp_dir, "split_audios")
                            total_chunks = len([f for f in os.listdir(split_audio_folder) if f.endswith(".mp3")])

                            if total_chunks > 0:
                                progress = st.progress(0)
                                transcription_dir = process_and_transcribe_chunks(
                                    model, split_audio_folder, session_temp_dir, progress, total_chunks
                                )

                                zip_path = create_zip_file(transcription_dir, "transcription_output")
                                if os.path.exists(zip_path):
                                    st.success("Transcription completed successfully!")
                                    with open(zip_path, "rb") as f:
                                        st.download_button("Download Transcription ZIP", f,
                                                           file_name="transcription_output.zip")
                                else:
                                    st.error("Failed to create ZIP file.")
                            else:
                                st.error("No audio chunks were generated.")
                            shutil.rmtree(session_temp_dir)

        elif tab == "Upload Audio":
            st.markdown("**Tip:** Upload audio files in formats like MP3, WAV, or M4A.")
            uploaded_files = st.file_uploader("Upload Audio Files", type=["mp3", "wav", "opus", "m4a"],
                                              accept_multiple_files=True)

            if uploaded_files and st.button("Upload and Transcribe"):
                with st.spinner("Transcribing..."):
                    progress = st.progress(0)
                    total_chunks = 0

                    combined_transcription_dir = os.path.join(session_temp_dir, "combined_transcriptions")
                    os.makedirs(combined_transcription_dir, exist_ok=True)

                    # Calculate total chunks across all files
                    for file in uploaded_files:
                        file_type = file.name.split(".")[-1]
                        audio_path = handle_audio_upload(file, session_temp_dir, file_type)
                        if audio_path and split_audio(audio_path, session_temp_dir):
                            split_audio_folder = os.path.join(session_temp_dir, "split_audios")
                            total_chunks += len([f for f in os.listdir(split_audio_folder) if f.endswith(".mp3")])

                    if total_chunks > 0:
                        for file in uploaded_files:
                            file_type = file.name.split(".")[-1]
                            audio_path = handle_audio_upload(file, session_temp_dir, file_type)

                            if audio_path and split_audio(audio_path, session_temp_dir):
                                split_audio_folder = os.path.join(session_temp_dir, "split_audios")
                                transcription_dir = process_and_transcribe_chunks(
                                    model, split_audio_folder, combined_transcription_dir, progress, total_chunks
                                )

                        # Create a single ZIP file for all transcriptions
                        zip_path = create_zip_file(combined_transcription_dir, "all_transcriptions")
                        shutil.rmtree(session_temp_dir)

                        if os.path.exists(zip_path):
                            with open(zip_path, "rb") as f:
                                st.download_button("Download All Transcriptions", f, file_name="all_transcriptions.zip")
                        else:
                            st.error("Failed to create ZIP file for all transcriptions.")
                    else:
                        st.error("No audio chunks were generated. Please check the uploaded files.")
    finally:
        # Ensure cleanup
        if os.path.exists(session_temp_dir):
            shutil.rmtree(session_temp_dir)

    with st.expander("FAQ"):
        st.write("**Q: What file formats are supported?**")
        st.write("A: Supported formats include MP3, WAV, OPUS, and M4A.")


if __name__ == "__main__":
    main()
