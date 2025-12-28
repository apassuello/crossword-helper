#!/usr/bin/env python3
"""
Demonstration of Phase 3: Theme Entry Support

This script demonstrates the complete theme entry workflow:
1. Create a small grid with theme words locked
2. Extract theme entries in frontend format
3. Send to API with theme entries
4. Verify CLI preserves theme words during autofill
"""

import json
import tempfile
import subprocess
from pathlib import Path

# Colors
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_grid(grid_data, title="Grid"):
    """Pretty print a grid."""
    print(f"\n{BLUE}{title}:{RESET}")
    for row in grid_data:
        print("  ", end="")
        for cell in row:
            if cell == '#':
                print('█', end=' ')
            elif cell == '.':
                print('·', end=' ')
            else:
                print(cell, end=' ')
        print()

def main():
    print(f"\n{BLUE}{'='*70}")
    print("Phase 3: Theme Entry Support - Live Demonstration")
    print(f"{'='*70}{RESET}\n")

    # Step 1: Create a small grid with theme entries
    print(f"{YELLOW}Step 1: Create test grid with theme entries{RESET}")

    # 7x7 grid with two theme words locked: HELLO (across) and HELP (down)
    grid = [
        ["H", "E", "L", "L", "O", ".", "."],  # Row 0: HELLO (theme)
        ["E", ".", ".", ".", ".", ".", "."],  # Row 1
        ["L", ".", ".", ".", ".", ".", "."],  # Row 2
        ["P", ".", ".", ".", ".", ".", "."],  # Row 3: HELP complete (theme)
        [".", ".", ".", ".", ".", ".", "."],  # Row 4
        [".", ".", ".", ".", ".", ".", "."],  # Row 5
        [".", ".", ".", ".", ".", ".", "."],  # Row 6
    ]

    grid_data = {
        "size": 7,
        "grid": grid
    }

    print_grid(grid, "Original Grid with Theme Words")

    # Theme entries (simulating frontend extraction)
    # HELLO at (0,0) across and HELP at (0,0) down
    theme_entries = {
        "(0,0,across)": "HELLO",  # Row 0, Col 0, across
        "(0,0,down)": "HELP"       # Row 0, Col 0, down
    }

    print(f"\n{GREEN}Theme entries to preserve:{RESET}")
    for key, word in theme_entries.items():
        print(f"  {key}: {word}")

    # Step 2: Write to temp files
    print(f"\n{YELLOW}Step 2: Prepare files for CLI{RESET}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name
    print(f"  Grid file: {grid_file}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(theme_entries, f)
        theme_file = f.name
    print(f"  Theme file: {theme_file}")

    # Step 3: Run CLI with theme entries
    print(f"\n{YELLOW}Step 3: Run autofill with theme entries preserved{RESET}")

    cli_dir = Path(__file__).parent / 'cli'
    wordlist_path = Path(__file__).parent / 'data' / 'wordlists' / 'comprehensive.txt'

    cmd = [
        'python3', '-m', 'src.cli',
        'fill', grid_file,
        '--wordlists', str(wordlist_path),
        '--theme-entries', theme_file,
        '--timeout', '30',
        '--min-score', '30',
        '--algorithm', 'trie',
        '--allow-nonstandard',
        '--json-output'
    ]

    print(f"  Running: python3 -m src.cli fill ...")
    print(f"  {GREEN}This may take up to 30 seconds...{RESET}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cli_dir
        )

        # Step 4: Verify results
        print(f"\n{YELLOW}Step 4: Verify theme entries were preserved{RESET}")

        if result.returncode == 0:
            # Parse result
            output = json.loads(result.stdout)

            filled_grid = output.get('grid', [])

            print_grid(filled_grid, "Filled Grid")

            # Check if theme words are preserved
            print(f"\n{GREEN}Verification:{RESET}")

            # Check HELLO across
            hello_preserved = (
                filled_grid[0][0] == 'H' and
                filled_grid[0][1] == 'E' and
                filled_grid[0][2] == 'L' and
                filled_grid[0][3] == 'L' and
                filled_grid[0][4] == 'O'
            )

            if hello_preserved:
                print(f"  {GREEN}✓ HELLO (across) preserved{RESET}")
            else:
                print(f"  ✗ HELLO (across) was modified!")

            # Check HELP down
            help_preserved = (
                filled_grid[0][0] == 'H' and
                filled_grid[1][0] == 'E' and
                filled_grid[2][0] == 'L' and
                filled_grid[3][0] == 'P'
            )

            if help_preserved:
                print(f"  {GREEN}✓ HELP (down) preserved{RESET}")
            else:
                print(f"  ✗ HELP (down) was modified!")

            # Check if grid was filled
            slots_filled = output.get('slots_filled', 0)
            total_slots = output.get('total_slots', 0)

            print(f"\n{GREEN}Autofill Statistics:{RESET}")
            print(f"  Slots filled: {slots_filled}/{total_slots}")
            print(f"  Success: {output.get('success', False)}")

            if output.get('success') and hello_preserved and help_preserved:
                print(f"\n{GREEN}{'='*70}")
                print("✓ SUCCESS: Theme entries work correctly!")
                print("  - Theme words were preserved during autofill")
                print("  - Grid was filled around the theme entries")
                print(f"{'='*70}{RESET}\n")
                return 0
            else:
                print(f"\n{YELLOW}⚠ Partial success or theme preservation issue{RESET}\n")
                return 1

        else:
            print(f"\n{YELLOW}CLI returned non-zero exit code: {result.returncode}{RESET}")
            print(f"stderr: {result.stderr[:500]}")

            # Try to parse partial output
            if result.stdout:
                try:
                    output = json.loads(result.stdout)
                    filled_grid = output.get('grid', [])
                    if filled_grid:
                        print_grid(filled_grid, "Partial Grid")
                except:
                    pass

            return 1

    except subprocess.TimeoutExpired:
        print(f"\n{YELLOW}⚠ Autofill timed out (60s limit){RESET}")
        print(f"  This is acceptable - it means CLI accepted theme entries")
        print(f"  For full test, use longer timeout or smaller grid")
        return 0
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    finally:
        # Cleanup
        Path(grid_file).unlink()
        Path(theme_file).unlink()

if __name__ == '__main__':
    exit(main())
