# app.py
import os
import shutil
import streamlit as st
from load_whisper import load_and_save_model
from utils import (
    create_zip_file,
    split_audio,
    transcribe_audio_files,
    handle_youtube_link,
    handle_audio_upload,
)

# Constants
TEMP_DIR = "debug_temp_dir"
MODEL_DIR = "whisper_models"

ffmpeg_dir = os.path.join(os.path.dirname(__file__), "bin")
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    st.set_page_config(page_title="Transcription Tool", layout="wide")
    st.title("TBOG LOVES SEUN VERY MUCH TRANSCRIPTION TOOL")

    # Load the model once
    model = load_and_save_model(model_dir=MODEL_DIR)

    tabs = ["YouTube Link", "Upload Audio"]
    tab = st.sidebar.radio("Select Input Type", tabs)

    if tab == "YouTube Link":
        youtube_url = st.text_input("Enter YouTube Video URL", "")
        if st.button("Download and Transcribe"):
            if youtube_url:
                with st.spinner("Downloading and Transcribing..."):
                    audio_path = handle_youtube_link(youtube_url, TEMP_DIR)
                    if audio_path and split_audio(audio_path, TEMP_DIR):
                        split_audio_folder = os.path.join(TEMP_DIR, "split_audios")
                        total_chunks = len([f for f in os.listdir(split_audio_folder) if f.endswith(".mp3")])

                        if total_chunks > 0:
                            progress = st.progress(0)
                            transcribe_audio_files(model, split_audio_folder, TEMP_DIR, progress, total_chunks)

                            zip_path = create_zip_file(TEMP_DIR, "transcription_output")
                            if os.path.exists(zip_path):
                                st.success("Transcription completed successfully!")
                                with open(zip_path, "rb") as f:
                                    st.download_button("Download Transcription ZIP", f,
                                                       file_name="transcription_output.zip")
                            else:
                                st.error("Failed to create ZIP file.")
                        else:
                            st.error("No audio chunks were generated.")
                        shutil.rmtree(TEMP_DIR)

    elif tab == "Upload Audio":
        st.markdown("**Tip:** Upload audio files in formats like MP3, WAV, or M4A.")
        uploaded_files = st.file_uploader("Upload Audio Files", type=["mp3", "wav", "opus", "m4a"],
                                          accept_multiple_files=True)

        if uploaded_files and st.button("Upload and Transcribe"):
            with st.spinner("Transcribing..."):
                progress = st.progress(0)
                total_chunks = 0

                combined_transcription_dir = os.path.join(TEMP_DIR, "combined_transcriptions")
                os.makedirs(combined_transcription_dir, exist_ok=True)

                # Calculate total chunks across all files
                for file in uploaded_files:
                    file_type = file.name.split(".")[-1]
                    audio_path = handle_audio_upload(file, TEMP_DIR, file_type)
                    if audio_path and split_audio(audio_path, TEMP_DIR):
                        split_audio_folder = os.path.join(TEMP_DIR, "split_audios")
                        total_chunks += len([f for f in os.listdir(split_audio_folder) if f.endswith(".mp3")])

                if total_chunks > 0:
                    processed_chunks = 0
                    for idx, file in enumerate(uploaded_files):
                        file_type = file.name.split(".")[-1]
                        audio_path = handle_audio_upload(file, TEMP_DIR, file_type)

                        if audio_path and split_audio(audio_path, TEMP_DIR):
                            split_audio_folder = os.path.join(TEMP_DIR, "split_audios")
                            for chunk_idx, chunk_file in enumerate(sorted(os.listdir(split_audio_folder))):
                                if chunk_file.endswith(".mp3"):
                                    audio_chunk_path = os.path.join(split_audio_folder, chunk_file)
                                    output_path = os.path.join(
                                        combined_transcription_dir,
                                        f"{file.name.replace(f'.{file_type}', '')}_chunk_{chunk_idx + 1}.txt"
                                    )
                                    try:
                                        result = model.transcribe(audio_chunk_path)
                                        with open(output_path, "w", encoding="utf-8") as f:
                                            f.write(result["text"])
                                    except Exception as e:
                                        st.error(f"Error transcribing chunk {chunk_file}: {e}")
                                        continue

                                    # Increment processed chunks and update progress
                                    processed_chunks += 1
                                    progress.progress(processed_chunks / total_chunks)
                        else:
                            st.error(f"Failed to process file {file.name}.")

                    # Create a single ZIP file for all transcriptions
                    zip_path = create_zip_file(combined_transcription_dir, "all_transcriptions")
                    shutil.rmtree(TEMP_DIR)

                    if os.path.exists(zip_path):
                        with open(zip_path, "rb") as f:
                            st.download_button(
                                "Download All Transcriptions",
                                f,
                                file_name="all_transcriptions.zip"
                            )
                    else:
                        st.error("Failed to create ZIP file for all transcriptions.")
                else:
                    st.error("No audio chunks were generated. Please check the uploaded files.")

    with st.expander("FAQ"):
        st.write("**Q: What file formats are supported?**")
        st.write("A: Supported formats include MP3, WAV, OPUS, and M4A.")


if __name__ == "__main__":
    main()