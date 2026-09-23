from pathlib import Path

import yt_dlp
import requests
import questionary
from bs4 import BeautifulSoup
from questionary import Choice

from metadata import get_metadata, update_metadata, print_metadata
from src.settings import load_settings, add_directory, remove_directory, DEFAULT_OUT_DIR
from src.validation import validate_pos_int, validate_pos_float, validate_neg_float


def main():
    action = ""
    while action != "Exit":
        action = questionary.select(
            "What do you want to do?",
            choices=[
                "Download Track",
                "Modify Metadata",
                "Read Metadata",
                "Manage Directories",
                "Exit",
            ]
        ).ask()
        match action:
            case "Download Track":
                download()
            case "Modify Metadata":
                modify_metadata()
            case "Read Metadata":
                read_metadata()
            case "Manage Directories":
                manage_directories()


def download():
    url = questionary.text("Enter URL: ").ask()
    if not url:
        return
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, features="html.parser")

    def is_excluded(t: str) -> bool:
        excluded_title_prefixes = [
            "Your Browser",
            "Dein Browser",
        ]
        for p in excluded_title_prefixes:
            if t.startswith(p):
                return True
        return False
    links = soup.find_all(name="title")
    title = next((link.text for link in links if not is_excluded(link.text)), "?")
    meta = soup.find_all(name="meta")
    artist = next((m.attrs.get("content") for m in meta if m.attrs.get("name", "") == "description"), "?")
    filename = questionary.text("Enter filename:", default=f"{artist} - {title}").ask()
    if not filename:
        return

    yt_ops = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'outtmpl': f'out/{filename}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '0',  # VBR (Variable Bit Rate) highest quality
        }],
    }

    start_offset = float(questionary.text("Enter start offset:", default="0", validate=validate_pos_float).ask())
    end_offset = float(questionary.text("Enter end offset:", default="0", validate=validate_neg_float).ask())
    if start_offset > 0 or end_offset < 0:
        yt_ops['download_ranges'] = yt_dlp.utils.download_range_func([], [[start_offset, end_offset]])
    if start_offset > 0:
        yt_ops['force_keyframes_at_cuts'] = True

    with yt_dlp.YoutubeDL(yt_ops) as ydl:
        ydl.download([url])

    filepath = Path(__file__).parent.parent / "out" / f"{filename}.opus"
    modify_metadata(filepath.as_posix())


def modify_metadata(filepath = None):
    settings = load_settings()
    filename: str | None = None
    while not filepath:
        files = {f.name: f.as_posix() for f in DEFAULT_OUT_DIR.iterdir()}
        filename = questionary.select("File to modify:", choices=list(files.keys())).ask()
        filepath = files[filename]
    if not filename:
        filename = filepath.split('/')[-1]

    source = questionary.select("Metadata source:", choices=["Type", "Copy"]).ask()
    match source:
        case "Copy":
            files = {
                f.name: f.as_posix()
                for dir in settings.directories
                for f in dir.iterdir()
                if f.name != filename
            }
            c = filename.split(".")[0]
            best_candidates = [f for f in files if f.split(".")[0] == c]
            input = "Other"
            if best_candidates:
                input = questionary.select("Input file:", choices=[*best_candidates, "Other"]).ask()
            if input == "Other":
                input = questionary.select("Input file:", choices=list(files.keys())).ask()

            changes = get_metadata(files[input])
            print("Current metadata:")
            print_metadata(get_metadata(filepath))
            print("Updates:")
            print_metadata(changes)

            if update_metadata(filepath, changes):
                if questionary.confirm(f"Delete {input}?").ask():
                    Path(files[input]).unlink(missing_ok=True)

        case "Type":
            changes = {}

            parts = filename.split("-", 1)
            artist = parts[0].strip()
            title = '.'.join(parts[1].split('.')[:-1]).strip()

            if not questionary.confirm(f"Artist: {artist}").ask():
                artist = questionary.text("Type the artist").ask().strip()
            changes["albumartist"] = [artist] if artist else None

            if not questionary.confirm(f"Track Title: {title}").ask():
                title = questionary.text("Type the track title:").ask().strip()
            changes["title"] = [title] if title else None

            other_tracks = [
                t.as_posix()
                for d in settings.directories
                for t in d.iterdir()
                if t.name.split('-')[0].strip() == artist
            ]
            genres = set()
            albums = {}
            for metadata in [get_metadata(t) for t in other_tracks]:
                for g in metadata.get('genre', []):
                    genres.add(g)
                if 'album' in metadata and 'date' in metadata:
                    albums[metadata["album"][0]] = metadata["date"][0]

            current_metadata = get_metadata(filepath)
            current_genres = current_metadata.get("genre", [])
            genre_choices = [Choice(g, checked=g in current_genres) for g in genres]

            chosen_genres = ['Other']
            if genres:
                chosen_genres = questionary.checkbox("Select the genres", choices=[*genre_choices, "Other"]).ask()
            if 'Other' in chosen_genres:
                chosen_genres.remove('Other')
                r = questionary.text("Enter genres (comma separated): ").ask()
                chosen_genres.extend(g.strip() for g in r.split(','))
                chosen_genres = list(set(chosen_genres))

            changes["genre"] = chosen_genres

            current_albums = current_metadata.get("album", [])
            current_album = current_albums[0] if current_albums else None
            album = "Other"
            if albums:
                album = questionary.select("Album:", default=current_album, choices=[*albums.keys(), "Other"]).ask()
            if album == "Other":
                album = questionary.text("Type the album:").ask()
                date = str(questionary.text("Enter year:", validate=validate_pos_int).ask())
            else:
                date = str(albums[album])
            changes["album"] = [album] if album else None
            changes["date"] = [date] if date else None

            track_numbers = current_metadata.get('tracknumber', [])
            track_number = track_numbers[0] if track_numbers else ""

            track_number = str(questionary.text(
                "Enter track number:", default=track_number, validate=validate_pos_int
            ).ask())
            changes['tracknumber'] = [track_number] if track_number else None

            print("Current metadata:")
            print_metadata(current_metadata)
            print("Updates:")
            print_metadata(changes)

            update_metadata(filepath, changes)

def read_metadata():
    settings = load_settings()
    dirs = [d for d in settings.directories if next(d.iterdir(), None)]
    input_dir = questionary.select("Directory:", choices=[d.as_posix() for d in dirs]).ask()
    input_dir_path = Path(input_dir)
    choices = [f.as_posix() for f in input_dir_path.iterdir()]
    input_file = questionary.select("Input file:", choices=choices).ask()
    print_metadata(get_metadata(input_file))


def manage_directories():
    action = ""
    while action != "Exit Submenu":
        settings = load_settings()

        print("Current Directories:")
        for d in settings.directories:
            print(f"  - {d.as_posix()}")
        print()

        choices = ["Add Directory"]
        if settings.directories:
            choices.append("Remove Directory")
        choices.append("Exit Submenu")
        action = questionary.select("What do you want to do?", choices=choices).ask()
        match action:
            case "Add Directory":
                new_dir = Path(questionary.text("Enter new directory:").ask())
                if new_dir in settings.directories:
                    continue
                add_directory(new_dir)
            case "Remove Directory":
                rm_dir = questionary.select(
                    "Which directory would you like to remove?",
                    choices=[*[d.as_posix() for d in settings.directories], "Cancel Operation"],
                ).ask()
                if rm_dir == "Cancel Operation":
                    continue
                remove_directory(Path(rm_dir))


if __name__ == "__main__":
    main()
