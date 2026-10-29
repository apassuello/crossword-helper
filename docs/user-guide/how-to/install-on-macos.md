# Install Crossword Helper on macOS

## Goal

Install Crossword Helper and everything it depends on from its GitHub repository, then open the web app
in your browser. You need to be able to open Terminal and paste commands. Linux works the same way;
Windows is not supported.

## Prerequisites

- **Python 3.9 or later.** Install it from [python.org](https://www.python.org/downloads/). The `python3`
  that comes with macOS is a stub that opens an Xcode command-line-tools install dialog the first time
  you use it; either route works. [?] *The stub's behaviour is quoted from the project README and could not
  be run on the Linux machine this guide was checked on.*
- **Node.js 18 or later (LTS).** Install it from [nodejs.org](https://nodejs.org/). `npm` comes with it.
- An internet connection: the setup step downloads Python and JavaScript packages.

Check what you have:

```bash
python3 --version
node --version
npm --version
```

## Steps

### 1. Get the code

Either clone the repository:

```bash
git clone https://github.com/apassuello/crossword-helper.git
cd crossword-helper
```

or use **Download ZIP** on the GitHub page, extract it, open Terminal in the extracted folder, and run:

```bash
chmod +x setup.sh
```

A clone keeps the script executable, so the `chmod` is only needed after a ZIP download.

### 2. Run the setup script

```bash
./setup.sh
```

The script checks your Python and Node versions, then creates a virtual environment in `venv/`, installs
the Python packages from `requirements.txt` into it, installs the JavaScript packages with `npm ci`, and
builds the web interface into `frontend/dist/`. The packages go into `venv/` and `node_modules/` inside the
project folder, not into your system Python or global Node packages.

When it works, the output ends like this (from a Linux run; version numbers on your Mac will differ):

```text
=== Crossword Helper Setup ===

[ok] Python 3.13
[ok] Node.js v22.22.0

Creating Python virtual environment...
[ok] Virtual environment created at venv/

Installing Python dependencies...
[ok] Python dependencies installed

Installing Node.js dependencies...
[ok] Node.js dependencies installed

Building frontend...
...
[ok] Frontend built to frontend/dist/

=== Setup complete ===
```

If a line starts with `Missing:`, install the tool it names (the message includes the download address) and
run `./setup.sh` again. The script stops before it creates anything when a tool is missing.

### 3. Start the app

```bash
source venv/bin/activate
python3 run.py
```

The terminal prints a line ending in `Running on http://localhost:5000` and keeps running. Leave it open.

### 4. Open it in your browser

Go to <http://localhost:5000>.

If `run.py` instead prints `Port 5000 is in use. Start with PORT=<other> python3 run.py`, another program
holds the port. Start on a different one and open that address instead:

```bash
PORT=5001 python3 run.py
```

Then open <http://localhost:5001>. [?] *On macOS the AirPlay Receiver service can hold port 5000; this is
stated in a code comment in `run.py` and was not reproduced on the Linux machine used to check this page.*

### 5. Stop and restart later

Press `Ctrl+C` in the terminal to stop the app. To start it again, from the project folder:

```bash
source venv/bin/activate
python3 run.py
```

## Final Result

With the app running, the status label in the top bar reads **online**. You can also check from a second
Terminal window:

```bash
curl http://localhost:5000/api/health
```

```text
{"architecture":"cli-backend","components":{"api_server":"ok","cli_adapter":"ok"},"status":"healthy","version":"2.0.0"}
```

## Update to a newer version

Fetch the new code (`git pull` in a clone, or download a fresh ZIP) and run `./setup.sh` again. The script
can be repeated: on a second run it reports `Virtual environment already exists` and reinstalls the
packages.

## Next Steps

- Build your first puzzle: [Your first crossword](../tutorials/first-crossword.md).
- Something went wrong: [Troubleshoot common problems](troubleshoot.md).
