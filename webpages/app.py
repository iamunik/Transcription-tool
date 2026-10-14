import os
import shutil
import streamlit as st
from load_whisper import load_and_save_model
from utils import process_audio_input, create_zip_file
import tempfile
import time

MODEL_DIR = "whisper_models"
os.makedirs(MODEL_DIR, exist_ok=True)


def show_saved_result(tab_key, button_label):
    """
    Shows the last finished result for a tab.

    The ZIP bytes live in st.session_state, so the success message and download
    button survive the rerun Streamlit triggers when the download button is clicked.
    """
    result = st.session_state["results"].get(tab_key)
    if result:
        st.success("Transcription completed successfully!")
        st.download_button(
            button_label,
            result["data"],
            file_name=result["file_name"],
            key=f"download_{tab_key}",
        )


def main():
    st.set_page_config(page_title="Transcription Tool",
                       page_icon="🎙️",
                       layout="wide")
    st.title("TRANSCRIPTION TOOL")

    model = load_and_save_model(model_dir=MODEL_DIR)
    tabs = ["YouTube Link", "Upload Audio"]
    tab = st.sidebar.radio("Select Input Type", tabs)

    if "results" not in st.session_state:
        st.session_state["results"] = {}
    results = st.session_state["results"]

    if tab == "YouTube Link":
        youtube_url = st.text_input("Enter YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")
        if st.button("Download and Transcribe"):
            results.pop(tab, None)
            # ignore_cleanup_errors avoids Windows "file in use" errors when the temp folder is removed
            with tempfile.TemporaryDirectory(prefix="session_", ignore_cleanup_errors=True) as session_temp_dir:
                with st.spinner("Processing YouTube link..."):
                    transcription_dir = process_audio_input("YouTube", youtube_url, model, session_temp_dir)
                    if transcription_dir:
                        zip_path = create_zip_file(transcription_dir, "transcription_output", session_temp_dir)
                        if os.path.exists(zip_path):
                            with open(zip_path, "rb") as f:
                                results[tab] = {"data": f.read(), "file_name": "transcription_output.zip"}
                        else:
                            st.error("Failed to create ZIP file.")
        show_saved_result(tab, "Download Transcription ZIP")

    else:
        uploaded_files = st.file_uploader("Upload Audio Files", type=["mp3", "wav", "opus", "m4a"],
                                          accept_multiple_files=True)
        if uploaded_files and st.button("Upload and Transcribe"):
            results.pop(tab, None)
            with tempfile.TemporaryDirectory(prefix="session_", ignore_cleanup_errors=True) as session_temp_dir:
                with st.spinner("Processing uploaded files..."):
                    combined_transcription_dir = os.path.join(session_temp_dir, "combined_transcriptions")
                    os.makedirs(combined_transcription_dir, exist_ok=True)

                    for i, file in enumerate(uploaded_files, start=1):
                        # Each file gets its own working folder so transcripts never overwrite each other
                        file_dir = os.path.join(session_temp_dir, f"file_{i}")
                        os.makedirs(file_dir, exist_ok=True)

                        transcription_dir = process_audio_input("Upload", file, model, file_dir)
                        if transcription_dir:
                            base_name = os.path.splitext(file.name)[0]
                            shutil.move(
                                os.path.join(transcription_dir, "full_transcript.txt"),
                                os.path.join(combined_transcription_dir, f"{i:02d}_{base_name}.txt"),
                            )

                    if os.listdir(combined_transcription_dir):
                        zip_path = create_zip_file(combined_transcription_dir, "all_transcriptions", session_temp_dir)
                        if os.path.exists(zip_path):
                            with open(zip_path, "rb") as f:
                                results[tab] = {"data": f.read(), "file_name": "all_transcriptions.zip"}
                        else:
                            st.error("Failed to create ZIP file.")
                    else:
                        st.error("No transcriptions found.")
        show_saved_result(tab, "Download All Transcriptions")


if __name__ == "__main__":
    start = time.time()
    main()
    end = time.time()
    print(f"{end - start:.1f} seconds")