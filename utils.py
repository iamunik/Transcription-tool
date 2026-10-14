import os
import glob
import shutil
import subprocess
import sys
import zipfile
import streamlit as st
import base64
import stat
import tempfile
import gc
import re


# ---------------------------------------------------------------------------
# Settings (edit these to tune behaviour)
# ---------------------------------------------------------------------------

# Length of each audio chunk in seconds. Smaller chunks use less memory.
CHUNK_SECONDS = 300

# Set to a language code such as "en" if you know it. None = auto-detect.
TRANSCRIBE_LANGUAGE = None

# Names / terms likely to appear in the audio. Helps with proper nouns and jargon.
# Example: "Citadel Global Community Church, LYF, Lagos"
INITIAL_PROMPT = None

# Evens out volume before transcription. Helps quiet recordings.
NORMALIZE_VOLUME = False

# Write [HH:MM:SS] timestamps in front of each line of the transcript.
INCLUDE_TIMESTAMPS = True


# ---------------------------------------------------------------------------
# FFmpeg / Deno locations
# ---------------------------------------------------------------------------

def _resolve_ffmpeg_path():
    """
    Returns the path to the FFmpeg binary.

    Order of preference:
      1. Bundled binary in ./bin (ffmpeg.exe on Windows, ffmpeg elsewhere)
      2. An ffmpeg found on the system PATH (e.g. installed via packages.txt on Streamlit)
      3. The bare name "ffmpeg" (lets the OS try to resolve it)
    """
    bin_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    bundled = os.path.join(os.path.dirname(__file__), "bin", bin_name)
    if os.path.exists(bundled):
        return bundled
    return shutil.which("ffmpeg") or "ffmpeg"


# Single source of truth for FFmpeg. All functions below use this.
ffmpeg_path = _resolve_ffmpeg_path()


def _find_deno():
    """
    Locates the Deno JavaScript runtime that yt-dlp needs for YouTube.

    Returns:
        str or None: Full path to deno, or None if it could not be found.

    Looks on PATH, then next to the Python interpreter (where `pip install deno`
    puts it, including on Streamlit Cloud), then in the Windows WinGet folder
    (an app launched from an IDE can hold a stale PATH).
    """
    found = shutil.which("deno")
    if found:
        return found

    candidate = os.path.join(os.path.dirname(sys.executable),
                             "deno.exe" if sys.platform == "win32" else "deno")
    if os.path.isfile(candidate):
        return candidate

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            packages = os.path.join(local, "Microsoft", "WinGet", "Packages")
            if os.path.isdir(packages):
                for root, _dirs, files in os.walk(packages):
                    if "deno.exe" in files:
                        return os.path.join(root, "deno.exe")
    return None


def _ensure_executable(path):
    """
    Makes sure a binary has the execute bit set (needed on Linux/macOS hosts).
    Does nothing on Windows or if the file is not a local path.
    """
    if sys.platform == "win32" or not os.path.isfile(path):
        return
    st_mode = os.stat(path).st_mode
    os.chmod(path, st_mode | stat.S_IEXEC)


def _write_cookies_file(temp_dir):
    """
    Writes YouTube cookies from Streamlit secrets (key: YOUTUBE_COOKIES) to a temp file.

    Returns:
        str or None: Path to the cookies file, or None if no cookies are configured.

    Cookies are optional. They are only needed if YouTube blocks the server with
    "Sign in to confirm you're not a bot". Never commit a cookies file to GitHub.
    """
    try:
        cookies = st.secrets.get("YOUTUBE_COOKIES")
    except Exception:
        cookies = None
    if not cookies:
        return None
    path = os.path.join(temp_dir, "yt_cookies.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(cookies)
    return path


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def is_youtube_link(url):
    """
    Checks if the provided URL is a valid YouTube link.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is a valid YouTube link, False otherwise.
    """
    pattern = r"(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/"
    return re.match(pattern, url) is not None


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


def _format_timestamp(seconds):
    """Formats seconds as HH:MM:SS."""
    seconds = int(max(seconds, 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ---------------------------------------------------------------------------
# Audio input: YouTube download and file upload
# ---------------------------------------------------------------------------

def handle_youtube_link(youtube_url, temp_dir):
    """
    Downloads the best available audio stream from a YouTube URL using yt-dlp.

    Args:
        youtube_url (str): The YouTube video URL to download audio from.
        temp_dir (str): The directory where the downloaded audio file will be saved.

    Returns:
        str or None: The path to the downloaded audio file if successful, otherwise None.

    Notes:
        - The audio is saved as-is (no re-encoding), which is faster and avoids quality loss.
          It is converted once, later, by convert_to_wav().
        - Live streams that are still running are skipped, because yt-dlp would keep
          recording until the stream ends.
        - YouTube requires a JavaScript runtime (Deno) plus yt-dlp's challenge solver script,
          handled here with --js-runtimes and --remote-components.
        - If YouTube blocks the server, optional cookies can be supplied through the
          YOUTUBE_COOKIES Streamlit secret.
        - Keep yt-dlp up to date (unpinned `yt-dlp[default]` in requirements.txt).
    """
    if not is_youtube_link(youtube_url):
        st.error("Invalid YouTube URL. Please provide a valid YouTube link.")
        return None

    progress_bar = st.progress(0)
    log_box = st.empty()
    log_lines = []

    try:
        # Run yt-dlp through the current interpreter so it always uses the
        # same virtual environment (and version) as the app.
        command = [
            sys.executable, "-m", "yt_dlp",
            "--remote-components", "ejs:github",
            "-f", "bestaudio/best",
            "-o", os.path.join(temp_dir, "video_audio.%(ext)s"),
            "--match-filter", "!is_live",
            "-R", "3",
            "--extractor-retries", "3",
            "--socket-timeout", "60",
            "--no-playlist",
            "--ffmpeg-location", ffmpeg_path,
            "--newline",
            "--progress",
        ]

        deno_path = _find_deno()
        if deno_path:
            command += ["--js-runtimes", f"deno:{deno_path}"]

        cookies_path = _write_cookies_file(temp_dir)
        if cookies_path:
            command += ["--cookies", cookies_path]

        command.append(youtube_url)

        # stderr is merged into stdout so errors are captured and no pipe can fill up and hang.
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in process.stdout:
            log_lines.append(line)
            clean = line.strip()
            if clean:
                log_box.caption(clean[:150])  # shows what yt-dlp is doing right now
            if "[download]" in line:
                match = re.search(r"(\d+(?:\.\d+)?)%", line)
                if match:
                    try:
                        progress_bar.progress(min(float(match.group(1)) / 100, 1.0))
                    except ValueError:
                        pass

        process.wait()

        if process.returncode != 0:
            st.error("Failed to download audio from YouTube")
            st.code("".join(log_lines[-15:]))
            return None

        downloaded = [
            p for p in glob.glob(os.path.join(temp_dir, "video_audio.*"))
            if not p.endswith((".part", ".ytdl"))
        ]
        if not downloaded:
            if any("does not pass filter" in line for line in log_lines):
                st.error("This looks like a live stream that is still running. "
                         "Try again once the stream has ended and YouTube has finished processing it.")
            else:
                st.error("Failed to download audio. File not found.")
                st.code("".join(log_lines[-15:]))
            return None

        progress_bar.progress(1.0)
        return downloaded[0]

    except Exception as e:
        st.error(f"Failed to download audio from YouTube: {str(e)}")
        if log_lines:
            st.code("".join(log_lines[-15:]))
        return None
    finally:
        progress_bar.empty()
        log_box.empty()


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


# ---------------------------------------------------------------------------
# Conversion, splitting and transcription
# ---------------------------------------------------------------------------

def convert_to_wav(input_file, output_file, normalize=NORMALIZE_VOLUME):
    """
    Converts any audio file to 16 kHz mono WAV in a single step.

    Args:
        input_file (str): Path to the input audio file (any format FFmpeg can read).
        output_file (str): Path where the WAV file will be saved.
        normalize (bool, optional): Apply loudness normalisation. Defaults to NORMALIZE_VOLUME.

    Returns:
        str or None: Path to the WAV file if successful, otherwise None.

    16 kHz mono is what Whisper uses internally, so nothing useful is lost.
    WAV is uncompressed, so later splitting does not degrade quality.
    """
    command = [ffmpeg_path, "-y", "-i", input_file, "-vn", "-ac", "1", "-ar", "16000"]
    if normalize:
        command += ["-af", "loudnorm"]
    command += ["-c:a", "pcm_s16le", output_file]
    try:
        _ensure_executable(ffmpeg_path)
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        st.error(f"Error converting audio: {e.stderr[-500:]}")
        return None
    except FileNotFoundError:
        st.error("FFmpeg was not found. Put ffmpeg in the bin folder or add it to packages.txt.")
        return None
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        st.error(f"Conversion failed: {output_file} is empty or missing.")
        return None
    return output_file


def split_audio(input_file, output_dir, chunk_duration=CHUNK_SECONDS):
    """
    Splits a WAV file into chunks of a specified duration using FFmpeg, without re-encoding.

    Args:
        input_file (str): Path to the input WAV file.
        output_dir (str): Directory under which the "split_audios" folder will be created.
        chunk_duration (int, optional): Duration of each chunk in seconds. Defaults to CHUNK_SECONDS.

    Returns:
        bool: True if splitting was successful, False otherwise.
    """
    split_audio_dir = os.path.join(output_dir, "split_audios")
    os.makedirs(split_audio_dir, exist_ok=True)
    command = [
        ffmpeg_path, "-y", "-i", input_file, "-f", "segment",
        "-segment_time", str(chunk_duration), "-c", "copy",
        os.path.join(split_audio_dir, "chunk_%03d.wav"),
    ]
    try:
        _ensure_executable(ffmpeg_path)
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        st.error(f"Error splitting audio: {e}")
        st.error(f"FFmpeg error output: {e.stderr[-500:]}")
        return False
    except FileNotFoundError:
        st.error("FFmpeg was not found. Put ffmpeg in the bin folder or add it to packages.txt.")
        return False
    return True


def process_and_transcribe_chunks(model, split_audio_folder, output_folder, progress, status, total_chunks):
    """
    Transcribes the audio chunks in a folder, one at a time, using the given model.

    Args:
        model: The faster-whisper model.
        split_audio_folder (str): Folder containing the WAV chunk files.
        output_folder (str): Directory where the transcription folder will be created.
        progress: Streamlit progress bar object for updating progress.
        status: Streamlit placeholder used for status messages.
        total_chunks (int): Total number of chunks to process.

    Returns:
        str: Path to the directory containing full_transcript.txt.

    Only one chunk is held in memory at a time, which keeps memory use low on
    Streamlit Cloud. Timestamps are offset per chunk so they run continuously.
    """
    transcription_dir = os.path.join(output_folder, "transcriptions")
    os.makedirs(transcription_dir, exist_ok=True)
    output_file = os.path.join(transcription_dir, "full_transcript.txt")

    chunk_files = sorted(f for f in os.listdir(split_audio_folder) if f.endswith(".wav"))
    processed_chunks = 0

    with open(output_file, "w", encoding="utf-8") as out_f:
        for chunk_idx, chunk_file in enumerate(chunk_files):
            chunk_path = os.path.join(split_audio_folder, chunk_file)
            offset = chunk_idx * CHUNK_SECONDS
            status.info(f"Transcribing part {chunk_idx + 1} of {total_chunks}...")
            try:
                segments, info = model.transcribe(
                    chunk_path,
                    language=TRANSCRIBE_LANGUAGE,
                    beam_size=5,
                    vad_filter=True,                           # skips silence/music, reduces made-up text
                    vad_parameters=dict(min_silence_duration_ms=500),
                    condition_on_previous_text=False,          # stops repetition loops from snowballing
                    initial_prompt=INITIAL_PROMPT,
                )
                for segment in segments:
                    text = segment.text.strip()
                    if not text:
                        continue
                    if INCLUDE_TIMESTAMPS:
                        out_f.write(f"[{_format_timestamp(offset + segment.start)}] {text}\n")
                    else:
                        out_f.write(text + "\n")
                out_f.flush()
            except Exception as e:
                st.error(f"Error transcribing {chunk_file}: {e}")
                continue
            finally:
                try:
                    os.remove(chunk_path)
                except Exception:
                    pass
                gc.collect()
            processed_chunks += 1
            progress.progress(processed_chunks / total_chunks)

    shutil.rmtree(split_audio_folder, ignore_errors=True)
    gc.collect()
    return transcription_dir


def process_audio_input(input_type, input_data, model, session_temp_dir):
    """
        Handles audio input from either a YouTube link or an uploaded file, converts and splits it,
        and transcribes it with the provided model.

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
        if not audio_path:
            status.empty()
            return None
    else:
        status.info("Uploading audio file...")
        file_type = input_data.name.split(".")[-1]
        audio_path = handle_audio_upload(input_data, session_temp_dir, file_type)
        if not audio_path:
            status.empty()
            return None

    status.info("Converting audio...")
    wav_path = os.path.join(session_temp_dir, "audio_16k.wav")
    converted = convert_to_wav(audio_path, wav_path)
    try:
        os.remove(audio_path)
    except Exception:
        pass
    gc.collect()
    if not converted:
        status.error("Audio conversion failed. Please try another file.")
        return None

    status.info("Splitting audio...")
    split_ok = split_audio(wav_path, session_temp_dir)
    try:
        os.remove(wav_path)
    except Exception:
        pass
    if not split_ok:
        status.error("Failed to split audio.")
        return None

    split_audio_folder = os.path.join(session_temp_dir, "split_audios")
    total_chunks = len([f for f in os.listdir(split_audio_folder) if f.endswith(".wav")])
    if total_chunks == 0:
        status.error("No audio chunks were generated.")
        return None

    progress = st.progress(0)
    transcription_dir = process_and_transcribe_chunks(
        model, split_audio_folder, session_temp_dir, progress, status, total_chunks
    )
    status.empty()
    progress.empty()
    return transcription_dir