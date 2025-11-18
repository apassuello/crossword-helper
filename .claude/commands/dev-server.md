# Development Server Command

Start Flask development server for local testing.

## Usage

```bash
claude dev-server [--port PORT]
```

## Arguments

- `--port` (optional): Port number (default: 5000)

## Steps

1. Check if server already running:
   ```bash
   curl -s http://localhost:5000/api/health
   ```
   - If responds: "Server already running on port 5000"
   - If not: Proceed to start

2. Ensure dependencies installed:
   ```bash
   pip list | grep -E "Flask|requests|pytest"
   ```
   - If missing: Run `pip install -r requirements.txt`

3. Start development server:
   ```bash
   cd /home/user/untitled_project/crossword-helper
   FLASK_DEBUG=1 python run.py
   ```

4. Wait for server ready:
   - Watch for: "Running on http://localhost:5000"
   - Check health endpoint works

5. Display startup info:
   - Server URL
   - Available endpoints
   - How to test each tool
   - How to stop server (Ctrl+C)

## Example Output

```
Starting development server...

✓ Dependencies installed
✓ Server started on http://localhost:5000

Available endpoints:
  GET  /                    - Web interface
  GET  /api/health          - Health check
  POST /api/pattern         - Pattern matching
  POST /api/number          - Grid numbering
  POST /api/normalize       - Convention normalization

Quick tests:
  # Pattern matching
  curl -X POST http://localhost:5000/api/pattern \
    -H "Content-Type: application/json" \
    -d '{"pattern": "?I?A"}'

  # Grid numbering
  curl -X POST http://localhost:5000/api/number \
    -H "Content-Type: application/json" \
    -d '{"size": 3, "grid": [["C","A","T"],["A","R","E"],["B","#","E"]]}'

  # Normalization
  curl -X POST http://localhost:5000/api/normalize \
    -H "Content-Type: application/json" \
    -d '{"text": "Tina Fey"}'

Press Ctrl+C to stop server
```

## Background Mode

To run in background:

```bash
# Start in background
nohup python run.py > server.log 2>&1 &

# Save PID
echo $! > server.pid

# Check status
curl http://localhost:5000/api/health

# Stop server
kill $(cat server.pid)
```

## Error Handling

- Port already in use: "Port 5000 in use. Try different port with --port"
- Missing dependencies: "Run `pip install -r requirements.txt`"
- Python not found: "Python 3.9+ required"
- Import errors: Show which module failed, suggest checking backend/ files

## Health Check Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "pattern_matcher": "ok",
    "numbering_validator": "ok",
    "convention_helper": "ok"
  }
}
```
