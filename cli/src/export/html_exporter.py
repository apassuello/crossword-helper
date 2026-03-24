"""
HTML export for crossword grids.

Generates clean, printable HTML output for crossword puzzles.
"""

from ..core.grid import Grid
from ..core.numbering import GridNumbering


class HTMLExporter:
    """Export crossword grids to HTML format."""

    @staticmethod
    def export(grid: Grid, title: str = "Crossword Puzzle") -> str:
        """
        Export grid to HTML.

        Args:
            grid: Grid to export
            title: Puzzle title

        Returns:
            HTML string
        """
        numbering = GridNumbering.auto_number(grid)
        clue_positions = GridNumbering.get_clue_positions(grid)

        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        .grid-container {{
            display: inline-block;
            border: 2px solid #000;
            margin: 20px 0;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat({grid.size}, 40px);
            gap: 0;
        }}
        .cell {{
            width: 40px;
            height: 40px;
            border: 1px solid #999;
            position: relative;
            background: white;
        }}
        .cell.black {{
            background: #000;
            border: 1px solid #000;
        }}
        .cell-number {{
            position: absolute;
            top: 2px;
            left: 2px;
            font-size: 10px;
            font-weight: bold;
        }}
        .cell-letter {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 20px;
            font-weight: bold;
        }}
        .clues {{
            margin-top: 30px;
        }}
        .clue-section {{
            margin: 20px 0;
        }}
        .clue-section h2 {{
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 5px;
        }}
        .clue {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .clue-number {{
            font-weight: bold;
            margin-right: 10px;
        }}
        @media print {{
            .grid {{
                grid-template-columns: repeat({grid.size}, 30px);
            }}
            .cell {{
                width: 30px;
                height: 30px;
            }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="grid-container">
        <div class="grid">
"""

        # Generate grid cells
        for row in range(grid.size):
            for col in range(grid.size):
                cell = grid.get_cell(row, col)

                if cell == "#":
                    html += '            <div class="cell black"></div>\n'
                else:
                    html += '            <div class="cell">\n'

                    # Add number if present
                    if (row, col) in numbering:
                        num = numbering[(row, col)]
                        html += (
                            f'                <span class="cell-number">{num}</span>\n'
                        )

                    # Add letter if filled
                    if cell != ".":
                        html += (
                            f'                <span class="cell-letter">{cell}</span>\n'
                        )

                    html += "            </div>\n"

        html += """        </div>
    </div>

    <div class="clues">
        <div class="clue-section">
            <h2>Across</h2>
"""

        # Generate across clues
        across_clues = [
            (num, info) for num, info in clue_positions.items() if info["has_across"]
        ]
        across_clues.sort(key=lambda x: x[0])

        for num, info in across_clues:
            html += '            <div class="clue">\n'
            html += f'                <span class="clue-number">{num}.</span>\n'
            html += f'                <span>({info["across_length"]} letters)</span>\n'
            html += "            </div>\n"

        html += """        </div>

        <div class="clue-section">
            <h2>Down</h2>
"""

        # Generate down clues
        down_clues = [
            (num, info) for num, info in clue_positions.items() if info["has_down"]
        ]
        down_clues.sort(key=lambda x: x[0])

        for num, info in down_clues:
            html += '            <div class="clue">\n'
            html += f'                <span class="clue-number">{num}.</span>\n'
            html += f'                <span>({info["down_length"]} letters)</span>\n'
            html += "            </div>\n"

        html += """        </div>
    </div>
</body>
</html>"""

        return html

    @staticmethod
    def export_to_file(
        grid: Grid, filepath: str, title: str = "Crossword Puzzle"
    ) -> None:
        """
        Export grid to HTML file.

        Args:
            grid: Grid to export
            filepath: Output file path
            title: Puzzle title
        """
        html = HTMLExporter.export(grid, title)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
