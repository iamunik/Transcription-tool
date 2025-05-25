import os
import shutil
import subprocess
import zipfile
import streamlit as st
import base64
import stat

def open_picture(image_name):
    """
    Open and encode an image in base64 format.
    """
    cwd = os.path.dirname(__file__)
    image_path = os.path.join(cwd, "image", image_name)
    image_path = os.path.abspath(image_path)
    with open(image_path, "rb") as file:
        images = base64.b64encode(file.read()).decode()
    return images

def create_zip_file(folder_path: str, zip_name: str, output_dir: str = ".") -> str:
    """
    Create a ZIP file from a folder.
    """
    zip_path = os.path.join(output_dir, f"{zip_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    return zip_path

def split_audio(input_file, output_dir, chunk_duration=300):
    """
    Split an audio file into 5-minute chunks using ffmpeg.
    """
    split_audio_dir = os.path.join(output_dir, "split_audios")
    os.makedirs(split_audio_dir, exist_ok=True)
    ffmpeg_path = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg")
    try:
        st_mode = os.stat(ffmpeg_path).st_mode
        os.chmod(ffmpeg_path, st_mode | stat.S_IEXEC)
    except Exception as e:
        st.error(f"Could not set execute permission on ffmpeg: {e}")
        return False
    command = [
        ffmpeg_path, "-i", input_file, "-f", "segment", "-segment_time", str(chunk_duration),
        "-c", "libmp3lame", "-threads", "1",
        os.path.join(split_audio_dir, "split_audio_%03d.mp3")
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
    except subprocess.CalledProcessError as e:
        st.error(f"Error splitting audio: {e}")
        st.error(f"FFmpeg error output: {e.stderr}")
        return False
    return True

def compress_audio(input_file, output_file, bitrate="48k"):
    """
    Compress the audio file to reduce its size using ffmpeg.
    """
    ffmpeg_path = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg")
    command = [
        ffmpeg_path, "-i", input_file, "-b:a", bitrate, "-threads", "1", output_file
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
    except subprocess.CalledProcessError as e:
        st.error(f"Error compressing audio: {e.stderr}")
        return None
    return output_file

def handle_youtube_link(youtube_url, temp_dir):
    """
    Download audio from a YouTube link using yt-dlp.
    """
    if not youtube_url.startswith("https://www.youtube.com"):
        st.error("Invalid YouTube URL. Please provide a valid YouTube link.")
        return None
    temp_audio_path = os.path.join(temp_dir, "video_audio.m4a")
    try:
        command = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "m4a",
            "--audio-quality", "0",
            "-o", temp_audio_path,
            "-R", "3",
            "--no-playlist",
            youtube_url
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not os.path.exists(temp_audio_path):
            st.error("Failed to download audio. File not found.")
            return None
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to download audio from YouTube: {e.stderr}")
        return None
    return temp_audio_path

def handle_audio_upload(uploaded_file, temp_dir, file_type):
    """
    Save an uploaded audio file to a temporary directory.
    """
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

def process_and_transcribe_chunks(model, split_audio_folder, output_folder, progress, total_chunks):
    """
    Transcribe audio chunks and save all results into a single file with headers.
    """
    transcription_dir = os.path.join(output_folder, "transcriptions")
    os.makedirs(transcription_dir, exist_ok=True)
    output_file = os.path.join(transcription_dir, "full_transcript.txt")
    processed_chunks = 0
    with open(output_file, "w", encoding="utf-8") as out_f:
        for chunk_idx, chunk_file in enumerate(sorted(os.listdir(split_audio_folder))):
            if chunk_file.endswith(".mp3"):
                audio_chunk_path = os.path.join(split_audio_folder, chunk_file)
                compressed_chunk_path = os.path.join(split_audio_folder, f"compressed_{chunk_file}")
                compress_audio(audio_chunk_path, compressed_chunk_path)
                try:
                    result = model.transcribe(compressed_chunk_path)
                    start_min = chunk_idx * 5
                    end_min = (chunk_idx + 1) * 5
                    out_f.write(f"\n--- Chunk {chunk_idx+1} ({start_min}-{end_min} min) ---\n")
                    out_f.write(result["text"] + "\n")
                except Exception as e:
                    st.error(f"Error transcribing chunk {chunk_file}: {e}")
                    continue
                try:
                    os.remove(compressed_chunk_path)
                except Exception:
                    pass
                try:
                    os.remove(audio_chunk_path)
                except Exception:
                    pass
                processed_chunks += 1
                progress.progress(processed_chunks / total_chunks)
    try:
        shutil.rmtree(split_audio_folder, ignore_errors=True)
    except Exception:
        pass
    return transcription_dir

def process_audio_input(input_type, input_data, model, session_temp_dir):
    """
    Process audio input (YouTube link or uploaded file) and handle transcription.
    Dynamically updates the status message to show only the current step.
    Compresses audio before splitting, deletes temp files ASAP, and profiles the process.
    """
    status = st.empty()  # Placeholder for dynamic status
    if input_type == "YouTube":
        status.info("Downloading audio from YouTube...")
        audio_path = handle_youtube_link(input_data, session_temp_dir)
        if audio_path:
            status.info("Download complete. Compressing audio...")
        else:
            status.empty()
            return None
    else:
        status.info("Uploading audio file...")
        file_type = input_data.name.split(".")[-1]
        audio_path = handle_audio_upload(input_data, session_temp_dir, file_type)
        if audio_path:
            status.info("Upload complete. Compressing audio...")
        else:
            status.empty()
            return None
    # Compress audio before splitting
    if audio_path:
        compressed_path = os.path.join(session_temp_dir, "compressed_input.mp3")
        compress_audio(audio_path, compressed_path, bitrate="48k")
        try:
            os.remove(audio_path)
        except Exception:
            pass
        audio_path = compressed_path
        status.info("Compression complete. Splitting audio...")
    if audio_path:
        if split_audio(audio_path, session_temp_dir, chunk_duration=300):
            try:
                os.remove(audio_path)
            except Exception:
                pass
            status.info("Audio splitting complete. Preparing for transcription...")
            split_audio_folder = os.path.join(session_temp_dir, "split_audios")
            total_chunks = len([f for f in os.listdir(split_audio_folder) if f.endswith(".mp3")])
            if total_chunks > 0:
                status.info("Starting transcription...")
                progress = st.progress(0)
                transcription_dir = process_and_transcribe_chunks(
                    model, split_audio_folder, session_temp_dir, progress, total_chunks
                )
                status.success("Transcription complete!")
                return transcription_dir
            else:
                status.error("No audio chunks were generated.")
        else:
            status.error("Failed to split audio.")
        status.empty()
        return None
