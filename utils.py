# utils.py
import os
import subprocess
import zipfile
import streamlit as st
import os
import base64


def open_picture(image_name):
    cwd = os.path.dirname(__file__)
    image_path = os.path.join(cwd, "image", image_name)
    image_path = os.path.abspath(image_path)
    file = open(image_path, "rb")
    images = base64.b64encode(file.read()).decode()
    return images


def create_zip_file(folder_path: str, zip_name: str) -> str:
    zip_path = f"{zip_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    return zip_path


# utils.py
def split_audio(input_file, output_dir, chunk_duration=30 * 60):
    split_audio_dir = os.path.join(output_dir, "split_audios")
    os.makedirs(split_audio_dir, exist_ok=True)

    # Use the bundled ffmpeg binary
    ffmpeg_path = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg")
    command = [
        ffmpeg_path, "-i", input_file, "-f", "segment", "-segment_time", str(chunk_duration),
        "-c", "libmp3lame", os.path.join(split_audio_dir, "split_audio_%03d.mp3")
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
    except subprocess.CalledProcessError as e:
        st.error(f"Error splitting audio: {e}")
        st.error(f"FFmpeg error output: {e.stderr}")
        return False
    return True


def transcribe_audio_files(model, audio_folder, output_folder, progress, total_chunks):
    transcription_dir = os.path.join(output_folder, "transcriptions")
    os.makedirs(transcription_dir, exist_ok=True)

    processed_chunks = 0
    for i, filename in enumerate(sorted(os.listdir(audio_folder))):
        if filename.endswith(".mp3"):
            audio_path = os.path.join(audio_folder, filename)
            output_path = os.path.join(transcription_dir, f"{filename.replace('.mp3', '.txt')}")
            try:
                result = model.transcribe(audio_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result["text"])
            except Exception as e:
                st.error(f"Error transcribing file {filename}: {e}")
            finally:
                processed_chunks += 1
                progress.progress(processed_chunks / total_chunks)


def handle_youtube_link(youtube_url, temp_dir):
    if not youtube_url.startswith("https://www.youtube.com"):
        st.error("Invalid YouTube URL.")
        return None

    temp_audio_path = os.path.join(temp_dir, "video_audio.m4a")
    try:
        command = ["yt-dlp", "-x", "--audio-format", "m4a", "-o", temp_audio_path, youtube_url]
        subprocess.run(command, check=True)
        if not os.path.exists(temp_audio_path):
            st.error("Failed to download audio. File not found.")
            return None
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to download audio from YouTube: {e}")
        return None

    return temp_audio_path


def handle_audio_upload(uploaded_file, temp_dir, file_type):
    if uploaded_file is None or uploaded_file.size == 0:
        st.error("Invalid file upload.")
        return None

    temp_audio_path = os.path.join(temp_dir, f"uploaded_audio.{file_type}")
    try:
        with open(temp_audio_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        st.error(f"Failed to save uploaded file: {e}")
        return None

    return temp_audio_path