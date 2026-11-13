from huggingface_hub import snapshot_download

print("Starting download...")

path = snapshot_download(
    repo_id="Systran/faster-whisper-tiny"
)

print("Download complete!")
print(path)