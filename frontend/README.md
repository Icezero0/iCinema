# iCinema Front New

## Scripts

Windows:

- `setup_frontend.bat`
  Checks Node.js and installs frontend dependencies.
- `run_frontend.bat`
  Starts the Vite development server.

Linux / macOS:

- `./setup_frontend.sh`
  Checks Node.js and installs frontend dependencies.
- `./run_frontend.sh`
  Starts the Vite development server.

## Requirements

- Node.js `>= 18`

## Notes

- `setup_frontend.*` is only for environment setup and dependency installation.
- `run_frontend.*` is only for running the development server.
- The dev server runs with `--host` so it can be accessed from LAN devices when needed.
