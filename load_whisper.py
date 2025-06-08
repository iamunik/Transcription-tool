# import whisper
# import streamlit as st
# import os
#
# @st.cache_resource(show_spinner="Loading Whisper model...")
# def load_and_save_model(model_name="tiny", model_dir="whisper_models"):
#     os.makedirs(model_dir, exist_ok=True)
#     model = whisper.load_model(model_name, download_root=model_dir)
#     return model
#
# if __name__ == "__main__":
#     whispers = load_and_save_model()
from faster_whisper import WhisperModel
import streamlit as st
import os


@st.cache_resource(show_spinner="Loading Faster-Whisper model...")
def load_and_save_model(model_name="base", model_dir="whisper_models"):
    os.makedirs(model_dir, exist_ok=True)
    # device="cpu" or "cuda", compute_type="int8" or "float16" for GPU
    whisper_model = WhisperModel(model_name, download_root=model_dir, device="cpu", compute_type="int8")
    return whisper_model


if __name__ == "__main__":
    model = load_and_save_model()
