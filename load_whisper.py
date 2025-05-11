# load_and_save_model.py
import whisper
import os


def load_and_save_model(model_name="base", model_dir="whisper_models"):
    """Download and save Whisper model to a folder."""
    # Ensure the directory exists
    os.makedirs(model_dir, exist_ok=True)

    # Load the model and cache it in the specified directory
    model = whisper.load_model(model_name, download_root=model_dir)
    # print(f"Model loaded from {model_dir}")
    return model


if __name__ == "__main__":
    whispers = load_and_save_model()  # This will download the model if not already cached
    # print("Model loaded and saved to disk!")
