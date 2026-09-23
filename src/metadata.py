import base64
import questionary
import json
from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture
from mutagen.oggopus import OggOpus

def get_metadata(filepath) -> dict[str, list[str]]:
    return dict(_get_audio(filepath))

def print_metadata(metadata: dict[str, list[str]]) -> None:
    transformed = {k: v[0] if len(v) == 1 else v for k, v in metadata.items()}
    print(json.dumps(transformed, indent=2))
    print()

def update_metadata(filepath, changes: dict[str, list[str]]):
    audio = _get_audio(filepath)
    for key, value in changes.items():
        if value:
            audio[key] = value
        else:
            audio.pop(key, None)

    print("Result:")
    print_metadata(dict(audio))

    if questionary.confirm("Apply changes?").ask():
        audio.save()
        print("Changes saved")
        return True
    return False

def update_front_cover(filepath, cover_path: str):
    picture = Picture()
    picture.type = 3  # 3 is for Front Cover
    picture.desc = "Front Cover"
    picture.mime = "image/jpeg"
    with open(cover_path, "rb") as f:
        picture.data = f.read()
    picture_data = picture.write()
    encoded_picture = base64.b64encode(picture_data).decode("ascii")

    audio = _get_audio(filepath)
    audio["metadata_block_picture"] = [encoded_picture]
    audio.save()

def _get_audio(filepath):
    if filepath.endswith('.mp3'):
        return EasyID3(filepath)
    elif filepath.endswith('.opus'):
        return OggOpus(filepath)
    else:
        raise ValueError("Unsupported file type")