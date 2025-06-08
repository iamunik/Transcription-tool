import os
import shutil
import subprocess
import zipfile
import streamlit as st
import base64
import stat
import tempfile
import gc


def open_picture(image_name):
    """
    Loads an image file from the `image` subdirectory, encodes it in base64, and returns the encoded string.

    Args:
        image_name (str): The filename of the image to load.

    Returns:
        str: The base64-encoded string of the image file contents.
    """
    cwd = os.path.dirname(__file__)
    image_path = os.path.join(cwd, "image", image_name)
    image_path = os.path.abspath(image_path)
    with open(image_path, "rb") as file:
        images = base64.b64encode(file.read()).decode()
    return images


def create_zip_file(folder_path: str, zip_name: str, output_dir: str = ".") -> str:
    """
    Creates a zip archive from the contents of a specified folder.

    Args:
        folder_path (str): Path to the folder whose contents will be zipped.
        zip_name (str): Name for the resulting zip file (without extension).
        output_dir (str, optional): Directory where the zip file will be saved. Defaults to current directory.

    Returns:
        str: The path to the created zip file.

    The function walks through all files and subfolders in `folder_path`, adds them to a zip archive,
    and preserves the folder structure relative to `folder_path`. The resulting zip file is saved in `output_dir`.
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
    Splits an audio file into smaller chunks of a specified duration using FFmpeg.

    Args:
        input_file (str): Path to the input audio file.
        output_dir (str): Directory where the split audio chunks will be saved.
        chunk_duration (int, optional): Duration of each chunk in seconds. Defaults to 300 (5 minutes).

    Returns:
        bool: True if splitting was successful, False otherwise.

    The function creates a subdirectory for split audio files, ensures FFmpeg is executable,
    and uses FFmpeg to segment the audio. Errors are reported via Streamlit.
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
        Compresses an audio file to a specified bitrate using FFmpeg.

        Args:
            input_file (str): Path to the input audio file.
            output_file (str): Path where the compressed audio will be saved.
            bitrate (str, optional): Target audio bitrate (e.g., "48k"). Defaults to "48k".

        Returns:
            str or None: Path to the compressed audio file if successful, otherwise None.

        The function ensures FFmpeg is executable, runs the compression command, and checks for errors.
        """
    ffmpeg_path = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg")
    command = [
        ffmpeg_path, "-i", input_file, "-b:a", bitrate, "-threads", "1", output_file
    ]
    try:
        st_mode = os.stat(ffmpeg_path).st_mode
        os.chmod(ffmpeg_path, st_mode | stat.S_IEXEC)
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
    except subprocess.CalledProcessError as e:
        st.error(f"Error compressing audio: {e.stderr}")
        return None
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        st.error(f"Compression failed: {output_file} is empty or missing.")
        return None
    return output_file


def handle_youtube_link(youtube_url, temp_dir):
    """
    Downloads audio from a YouTube URL using yt-dlp and saves it as an m4a file in the specified temporary directory.

    Args:
        youtube_url (str): The YouTube video URL to download audio from.
        temp_dir (str): The directory where the downloaded audio file will be saved.

    Returns:
        str or None: The path to the downloaded audio file if successful, otherwise None.

    The function validates the YouTube URL, attempts to download the audio, and handles errors via Streamlit.
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
        Saves an uploaded audio file to a temporary directory with the specified file type.

        Args:
            uploaded_file: The uploaded file object from Streamlit.
            temp_dir (str): Directory where the temporary file will be saved.
            file_type (str): The file extension/type (e.g., 'mp3', 'wav').

        Returns:
            str or None: Path to the saved temporary audio file, or None if upload is invalid.
    """
    if uploaded_file is None or uploaded_file.size == 0:
        st.error("Invalid file upload.")
        return None
    with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=f".{file_type}") as temp_audio:
        temp_audio.write(uploaded_file.getbuffer())
        temp_audio_path = temp_audio.name
    return temp_audio_path


def process_and_transcribe_chunks(model, split_audio_folder, output_folder, progress, total_chunks):
    """
    Processes and transcribes audio chunks in a specified folder using a given model.

    Args:
        model: The transcription model to use for transcribing audio chunks.
        split_audio_folder (str): Path to the folder containing split audio chunk files.
        output_folder (str): Directory where the transcription results will be saved.
        progress: Streamlit progress bar object for updating progress.
        total_chunks (int): Total number of audio chunks to process.

    Returns:
        str: Path to the directory containing the full transcription file.
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
                compressed = compress_audio(audio_chunk_path, compressed_chunk_path)
                if not compressed:
                    st.warning(f"Skipping chunk due to compression failure: {chunk_file}")
                    continue
                try:
                    segments, info = model.transcribe(compressed_chunk_path)
                    text = "".join([segment.text for segment in segments])
                    start_min = chunk_idx * 5
                    end_min = (chunk_idx + 1) * 5
                    out_f.write(f"\n--- Chunk {chunk_idx + 1} ({start_min}-{end_min} min) ---\n")
                    out_f.write(text + "\n")
                except Exception as e:
                    st.error(f"Error transcribing chunk {chunk_file}: {e}")
                    continue
                finally:
                    # Clean up memory and files
                    try:
                        os.remove(compressed_chunk_path)
                    except Exception:
                        pass
                    try:
                        os.remove(audio_chunk_path)
                    except Exception:
                        pass
                    del compressed_chunk_path, audio_chunk_path, compressed
                    gc.collect()
                processed_chunks += 1
                progress.progress(processed_chunks / total_chunks)
    try:
        shutil.rmtree(split_audio_folder, ignore_errors=True)
        gc.collect()
    except Exception:
        pass
    return transcription_dir


def process_audio_input(input_type, input_data, model, session_temp_dir):
    """
        Handles audio input from either a YouTube link or an uploaded file, processes it (download/upload, compress, split), and transcribes the audio using the provided model.

        Args:
            input_type (str): Type of input, either "YouTube" or "Upload".
            input_data: The YouTube URL (str) or uploaded file object.
            model: The transcription model to use.
            session_temp_dir (str): Directory for storing temporary files during processing.

        Returns:
            str or None: Path to the directory containing the transcription results, or None if processing fails.
    """
    status = st.empty()
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
    if audio_path:
        compressed_path = os.path.join(session_temp_dir, "compressed_input.mp3")
        compressed = compress_audio(audio_path, compressed_path, bitrate="48k")
        try:
            os.remove(audio_path)
        except Exception:
            pass
        del audio_path
        gc.collect()
        if not compressed:
            status.error("Audio compression failed. Please try another file.")
            status.empty()
            return None
        audio_path = compressed_path
        status.info("Compression complete. Splitting audio...")
    if audio_path:
        if split_audio(audio_path, session_temp_dir, chunk_duration=300):
            try:
                os.remove(audio_path)
            except Exception:
                pass
            del audio_path
            gc.collect()
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
