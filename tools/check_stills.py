import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOVIES_PATH = ROOT / "movies.json"
REQUIRED_PATH = ROOT / "assets" / "stills" / "required-stills.txt"


def main():
    movies = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    required = [still["path"] for movie in movies for still in movie.get("stills", [])]
    missing = [path for path in required if not (ROOT / path).exists()]

    REQUIRED_PATH.write_text("\n".join(required) + "\n", encoding="utf-8")

    print(f"Movies: {len(movies)}")
    print(f"Required stills: {len(required)}")
    print(f"Existing stills: {len(required) - len(missing)}")
    print(f"Missing stills: {len(missing)}")

    if missing:
        print("\nMissing files:")
        for path in missing:
            print(path)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
