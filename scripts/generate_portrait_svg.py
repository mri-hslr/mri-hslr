from pathlib import Path
import html


INPUT = Path("assets/portrait.txt")
OUTPUT = Path("assets/portrait.svg")

FONT_SIZE = 12.9
CHAR_WIDTH = 7.74
LINE_HEIGHT = FONT_SIZE * 1.25

ROW_DELAY = 0.09
ROW_DURATION = 0.8

CURSOR_WIDTH = 7

# Visible on GitHub dark mode
PORTRAIT_COLOR = "#A9FEF7"


def generate_svg():

    lines = INPUT.read_text().splitlines()

    if not lines:
        raise ValueError("portrait.txt is empty")

    rows = len(lines)
    cols = max(len(line) for line in lines)

    width = cols * CHAR_WIDTH
    height = rows * LINE_HEIGHT

    svg = []

    svg.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{width:.0f}"
        height="{height:.0f}"
        viewBox="0 0 {width:.2f} {height:.2f}">'''
    )

    svg.append(
        f'''
        <rect
            width="100%"
            height="100%"
            fill="#0D1117"/>
        '''
    )

    svg.append("<defs>")

    for i in range(rows):

        y = i * LINE_HEIGHT

        svg.append(
            f'''
            <clipPath id="row-{i}">
                <rect
                    x="0"
                    y="{y:.2f}"
                    width="0"
                    height="{LINE_HEIGHT:.2f}">
                    <animate
                        attributeName="width"
                        from="0"
                        to="{width:.2f}"
                        dur="{ROW_DURATION}s"
                        begin="{i * ROW_DELAY:.2f}s"
                        fill="freeze"/>
                </rect>
            </clipPath>
            '''
        )

    svg.append("</defs>")

    for i, line in enumerate(lines):

        y = (i + 1) * LINE_HEIGHT

        escaped_line = html.escape(line)

        svg.append(
            f'''
            <g clip-path="url(#row-{i})">

                <text
                    x="0"
                    y="{y:.2f}"
                    font-family="'JetBrains Mono', 'DejaVu Sans Mono', monospace"
                    font-size="{FONT_SIZE}px"
                    font-weight="400"
                    fill="{PORTRAIT_COLOR}"
                    xml:space="preserve">{escaped_line}</text>

                <rect
                    x="0"
                    y="{i * LINE_HEIGHT:.2f}"
                    width="{CURSOR_WIDTH}"
                    height="{LINE_HEIGHT:.2f}"
                    fill="{PORTRAIT_COLOR}">

                    <animate
                        attributeName="x"
                        from="0"
                        to="{width:.2f}"
                        dur="{ROW_DURATION}s"
                        begin="{i * ROW_DELAY:.2f}s"
                        fill="freeze"/>
                </rect>

            </g>
            '''
        )

    svg.append("</svg>")

    OUTPUT.write_text("\n".join(svg))

    print(f"Generated: {OUTPUT}")
    print(f"Size: {width:.0f} × {height:.0f}")
    print(f"Rows: {rows}")
    print(f"Columns: {cols}")


if __name__ == "__main__":
    generate_svg()