import subprocess
import sys
from pathlib import Path


def run_script(script_path: Path) -> None:
    print(f"\n=== Running: {script_path.name} ===")
    result = subprocess.run([sys.executable, str(script_path)])
    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {script_path.name}")
    print(f"=== Done: {script_path.name} ===")


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent

    scripts = [
        scripts_dir / "migrate_user_domain.py",
        scripts_dir / "migrate_room_domain.py",
        scripts_dir / "migrate_room_settings.py",
        scripts_dir / "migrate_room_join_request.py",
        scripts_dir / "migrate_notification_domain.py",
        scripts_dir / "migrate_message_domain.py",
        scripts_dir / "migrate_media_assets.py",
    ]

    for script in scripts:
        if not script.exists():
            raise FileNotFoundError(f"Script not found: {script}")
        run_script(script)

    print("\nAll migrations completed successfully.")


if __name__ == "__main__":
    main()
