import json
import os
import subprocess
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta


GRAPHQL_URL = "https://api.github.com/graphql"

OUTPUT_DIR = "assets"

# Same visual language as the portrait
BG = "#0D1117"
FG = "#A9FEF7"
MUTED = "#8B949E"
GRID = "#30363D"
ACCENT = "#58A6FF"
GREEN = "#3FB950"

ASCII_RAMP = " .:-=+*#%@"

FONT = "'JetBrains Mono', 'DejaVu Sans Mono', monospace"


def get_token():

    token = os.environ.get("GITHUB_TOKEN")

    if token:
        return token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    except Exception:
        raise RuntimeError(
            "No GITHUB_TOKEN found and GitHub CLI authentication failed."
        )


def get_login():

    login = os.environ.get("GH_LOGIN")

    if login:
        return login

    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    except Exception:
        raise RuntimeError(
            "Could not determine GitHub username."
        )


def github_graphql(query, variables, token):

    payload = json.dumps(
        {
            "query": query,
            "variables": variables
        }
    ).encode()

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "mri-hslr-profile-generator"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:

        result = json.loads(response.read().decode())

    if "errors" in result:

        messages = "\n".join(
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
        )

        raise RuntimeError(
            f"GitHub GraphQL error:\n{messages}"
        )

    return result["data"]


def get_github_data(login, token):

    today = datetime.utcnow().date()

    # Exactly 365 calendar days:
    # today - 364 days through today.
    start = today - timedelta(days=364)

    from_datetime = f"{start.isoformat()}T00:00:00Z"
    to_datetime = f"{today.isoformat()}T23:59:59Z"

    query = """
    query(
        $login: String!,
        $from: DateTime!,
        $to: DateTime!
    ) {

        user(login: $login) {

            login
            name

            contributionsCollection(
                from: $from,
                to: $to
            ) {

                contributionCalendar {

                    totalContributions

                    weeks {

                        firstDay

                        contributionDays {
                            date
                            contributionCount
                        }
                    }
                }
            }

            repositories(
                first: 100,
                ownerAffiliations: OWNER,
                privacy: PUBLIC,
                isFork: false
            ) {

                nodes {

                    name

                    languages(
                        first: 20,
                        orderBy: {
                            field: SIZE,
                            direction: DESC
                        }
                    ) {

                        edges {

                            size

                            node {
                                name
                                color
                            }
                        }
                    }
                }
            }
        }
    }
    """

    variables = {
        "login": login,
        "from": from_datetime,
        "to": to_datetime
    }

    return github_graphql(
        query,
        variables,
        token
    )


def flatten_days(data):

    days = []

    weeks = (
        data["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
        ["weeks"]
    )

    for week in weeks:

        for day in week["contributionDays"]:

            days.append(
                {
                    "date": date.fromisoformat(day["date"]),
                    "count": day["contributionCount"]
                }
            )

    days.sort(
        key=lambda x: x["date"]
    )

    return days


def calculate_streaks(days):

    if not days:
        return 0, 0

    contribution_map = {
        item["date"]: item["count"]
        for item in days
    }

    dates = sorted(contribution_map)

    longest = 0
    current_run = 0
    previous = None

    for current_date in dates:

        count = contribution_map[current_date]

        if count > 0:

            if (
                previous is not None
                and current_date == previous + timedelta(days=1)
            ):
                current_run += 1

            else:
                current_run = 1

            longest = max(
                longest,
                current_run
            )

            previous = current_date

        else:

            current_run = 0
            previous = None

    today = date.today()

    if contribution_map.get(today, 0) > 0:
        cursor = today

    elif contribution_map.get(
        today - timedelta(days=1),
        0
    ) > 0:
        cursor = today - timedelta(days=1)

    else:
        cursor = None

    current = 0

    while cursor is not None:

        if contribution_map.get(cursor, 0) <= 0:
            break

        current += 1
        cursor -= timedelta(days=1)

    return current, longest


def weekly_totals(days):

    if not days:
        return []

    totals = []

    current_total = 0
    current_start = days[0]["date"]

    for item in days:

        current_total += item["count"]

        elapsed = (
            item["date"] - current_start
        ).days

        if elapsed >= 6:

            totals.append(current_total)

            current_total = 0
            current_start = item["date"] + timedelta(days=1)

    if current_total > 0:
        totals.append(current_total)

    return totals[-52:]


def language_stats(data):

    byte_counts = Counter()
    repo_counts = Counter()
    colors = {}

    repositories = data["user"]["repositories"]["nodes"]

    for repo in repositories:

        repo_languages = set()

        if not repo:
            continue

        languages = repo.get("languages")

        if not languages:
            continue

        for edge in languages["edges"]:

            language = edge["node"]["name"]
            size = edge["size"]

            byte_counts[language] += size
            repo_languages.add(language)

            if edge["node"].get("color"):
                colors[language] = edge["node"]["color"]

        for language in repo_languages:
            repo_counts[language] += 1

    return (
        byte_counts,
        repo_counts,
        colors
    )


def svg_start(width, height, title):

    return [
        f'''<svg xmlns="http://www.w3.org/2000/svg"
width="{width}"
height="{height}"
viewBox="0 0 {width} {height}">''',

        f'''
<rect
    width="100%"
    height="100%"
    rx="12"
    fill="{BG}"
    stroke="{GRID}"
    stroke-width="1"/>
''',

        f'''
<text
    x="24"
    y="34"
    font-family="{FONT}"
    font-size="14"
    fill="{MUTED}"
    letter-spacing="1">{title}</text>
'''
    ]


def svg_end(parts):

    parts.append("</svg>")

    return "\n".join(parts)


def generate_stats_svg(total, weekly):

    width = 900
    height = 230

    parts = svg_start(
        width,
        height,
        "CONTRIBUTIONS / LAST 365 DAYS"
    )

    parts.append(
        f'''
<text
    x="24"
    y="100"
    font-family="{FONT}"
    font-size="54"
    font-weight="700"
    fill="{FG}">{total}</text>

<text
    x="27"
    y="128"
    font-family="{FONT}"
    font-size="13"
    fill="{MUTED}">total contributions</text>
'''
    )

    if weekly:

        max_value = max(weekly) or 1

        chart_x = 250
        chart_y = 70
        chart_w = 610
        chart_h = 110

        step = chart_w / max(1, len(weekly) - 1)

        points = []

        for i, value in enumerate(weekly):

            x = chart_x + i * step

            y = (
                chart_y
                + chart_h
                - (value / max_value) * chart_h
            )

            points.append(
                f"{x:.2f},{y:.2f}"
            )

        parts.append(
            f'''
<polyline
    points="{' '.join(points)}"
    fill="none"
    stroke="{FG}"
    stroke-width="2"/>
'''
        )

        for i, value in enumerate(weekly):

            x = chart_x + i * step

            y = (
                chart_y
                + chart_h
                - (value / max_value) * chart_h
            )

            parts.append(
                f'''
<circle
    cx="{x:.2f}"
    cy="{y:.2f}"
    r="2.5"
    fill="{FG}"/>
'''
            )

    return svg_end(parts)


def generate_streak_svg(current, longest):

    width = 900
    height = 210

    parts = svg_start(
        width,
        height,
        "STREAK"
    )

    cards = [
        (
            24,
            "CURRENT STREAK",
            current
        ),
        (
            462,
            "LONGEST STREAK",
            longest
        )
    ]

    for x, label, value in cards:

        parts.append(
            f'''
<rect
    x="{x}"
    y="65"
    width="414"
    height="110"
    rx="10"
    fill="#161B22"
    stroke="{GRID}"/>

<text
    x="{x + 22}"
    y="92"
    font-family="{FONT}"
    font-size="12"
    fill="{MUTED}"
    letter-spacing="1">{label}</text>

<text
    x="{x + 22}"
    y="145"
    font-family="{FONT}"
    font-size="40"
    font-weight="700"
    fill="{FG}">{value}</text>

<text
    x="{x + 22}"
    y="165"
    font-family="{FONT}"
    font-size="11"
    fill="{MUTED}">days</text>
'''
        )

    return svg_end(parts)


def generate_languages_svg(
    byte_counts,
    repo_counts,
    colors
):

    width = 900
    height = 420

    parts = svg_start(
        width,
        height,
        "LANGUAGES / PUBLIC REPOSITORIES"
    )

    total_bytes = sum(byte_counts.values()) or 1
    total_repos = sum(repo_counts.values()) or 1

    top_languages = byte_counts.most_common(8)

    y = 75

    for language, bytes_count in top_languages:

        percentage = (
            bytes_count / total_bytes
        ) * 100

        repo_percentage = (
            repo_counts[language] / total_repos
        ) * 100

        color = colors.get(
            language,
            FG
        )

        parts.append(
            f'''
<text
    x="24"
    y="{y}"
    font-family="{FONT}"
    font-size="13"
    fill="{FG}">{language}</text>

<rect
    x="180"
    y="{y - 12}"
    width="480"
    height="10"
    rx="5"
    fill="{GRID}"/>

<rect
    x="180"
    y="{y - 12}"
    width="{480 * percentage / 100:.2f}"
    height="10"
    rx="5"
    fill="{color}"/>

<text
    x="680"
    y="{y}"
    font-family="{FONT}"
    font-size="12"
    fill="{MUTED}">{percentage:.1f}% bytes</text>

<text
    x="800"
    y="{y}"
    font-family="{FONT}"
    font-size="12"
    fill="{MUTED}">{repo_percentage:.1f}% repos</text>
'''
        )

        y += 40

    return svg_end(parts)


def contribution_character(count, maximum):

    if count <= 0:
        return " "

    if maximum <= 0:
        return ASCII_RAMP[1]

    normalized = count / maximum

    index = int(
        normalized * (len(ASCII_RAMP) - 2)
    ) + 1

    index = min(
        index,
        len(ASCII_RAMP) - 1
    )

    return ASCII_RAMP[index]


def generate_year_svg(days):

    width = 900
    height = 360

    parts = svg_start(
        width,
        height,
        "YEAR / CONTRIBUTIONS"
    )

    max_count = max(
        [item["count"] for item in days] or [1]
    )

    # 53 columns × 7 rows
    cell_w = 15
    cell_h = 34

    start_x = 30
    start_y = 70

    first_date = days[0]["date"]

    # Align to Sunday
    first_date -= timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    contribution_map = {
        item["date"]: item["count"]
        for item in days
    }

    for i in range(365):

        current_date = first_date + timedelta(days=i)

        count = contribution_map.get(
            current_date,
            0
        )

        week = (
            current_date - first_date
        ).days // 7

        weekday = (
            current_date.weekday() + 1
        ) % 7

        x = start_x + week * cell_w
        y = start_y + weekday * cell_h

        char = contribution_character(
            count,
            max_count
        )

        safe_char = (
            char
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        parts.append(
            f'''
<text
    x="{x}"
    y="{y}"
    font-family="{FONT}"
    font-size="16"
    fill="{FG}"
    text-anchor="middle">{safe_char}</text>
'''
        )

    parts.append(
        f'''
<text
    x="30"
    y="330"
    font-family="{FONT}"
    font-size="11"
    fill="{MUTED}">less</text>

<text
    x="100"
    y="330"
    font-family="{FONT}"
    font-size="11"
    fill="{MUTED}">more</text>
'''
    )

    return svg_end(parts)


def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    token = get_token()
    login = get_login()

    print(f"Generating GitHub stats for @{login}")

    data = get_github_data(
        login,
        token
    )

    days = flatten_days(data)

    calendar = (
        data["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )

    total = calendar["totalContributions"]

    current_streak, longest_streak = calculate_streaks(
        days
    )

    weekly = weekly_totals(days)

    (
        byte_counts,
        repo_counts,
        colors
    ) = language_stats(data)

    stats_svg = generate_stats_svg(
        total,
        weekly
    )

    streak_svg = generate_streak_svg(
        current_streak,
        longest_streak
    )

    languages_svg = generate_languages_svg(
        byte_counts,
        repo_counts,
        colors
    )

    year_svg = generate_year_svg(
        days
    )

    with open(
        f"{OUTPUT_DIR}/stats.svg",
        "w"
    ) as file:
        file.write(stats_svg)

    with open(
        f"{OUTPUT_DIR}/streak.svg",
        "w"
    ) as file:
        file.write(streak_svg)

    with open(
        f"{OUTPUT_DIR}/langs.svg",
        "w"
    ) as file:
        file.write(languages_svg)

    with open(
        f"{OUTPUT_DIR}/year.svg",
        "w"
    ) as file:
        file.write(year_svg)

    print("Generated:")
    print("  assets/stats.svg")
    print("  assets/streak.svg")
    print("  assets/langs.svg")
    print("  assets/year.svg")


if __name__ == "__main__":
    main()