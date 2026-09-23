from pathlib import Path
from unittest import case

import yt_dlp
import questionary
from questionary import ValidationError

from metadata import get_metadata, update_metadata, print_metadata
from src.settings import load_settings, add_directory, remove_directory, DEFAULT_OUT_DIR


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


def download():
    raise NotImplementedError


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

            chosen_genres = ['Other']
            if genres:
                chosen_genres = questionary.checkbox("Select the genres", choices=[*genres, "Other"]).ask()
            if 'Other' in chosen_genres:
                chosen_genres.remove('Other')
                r = questionary.text("Enter genres (comma separated): ").ask()
                chosen_genres.extend(g.strip() for g in r.split(','))
                chosen_genres = list(set(chosen_genres))

            changes["genre"] = chosen_genres

            def validate_int(y):
                if not y:
                    return True
                try:
                    int(y)
                except:
                    raise ValidationError(message="Year must be an integer")
                return True

            album = "Other"
            if albums:
                album = questionary.select("Album:", choices=[*albums.keys(), "Other"]).ask()
            if album == "Other":
                album = questionary.text("Type the album:").ask()
                date = str(questionary.text("Enter year:", validate=validate_int).ask())
            else:
                date = str(albums[album])
            changes["album"] = [album] if album else None
            changes["date"] = [date] if date else None

            track_number = str(questionary.text("Enter track number:", validate=validate_int).ask())
            changes['tracknumber'] = [track_number] if track_number else None

            print("Current metadata:")
            print_metadata(get_metadata(filepath))
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


if __name__ == "__main__":
    main()
