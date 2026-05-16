# Crop CSP

Solves a crop-assignment constraint problem over a small field graph and visualizes it with `networkx` + `matplotlib`.

## Requirements

- Python 3.9+

## Setup

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Windows (cmd)

```cmd
py -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Run

With the venv activated:

```
python csp.py
```

## Deactivate

```
deactivate
```
