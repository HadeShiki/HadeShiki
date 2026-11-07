import json
import os
import sys
import urllib.request
import urllib.error
import xml.sax.saxutils as xml
from pathlib import Path


# ==========================================
# CONFIGURATION
# ==========================================

USERNAME = os.getenv("GITHUB_USERNAME", "HadeShiki")
TOKEN = os.getenv("GITHUB_TOKEN")

API_URL = "https://api.github.com"

OUTPUT_DIR = Path("profile")

MAX_LANGUAGES = 6

WIDTH = 430
STATS_HEIGHT = 190
LANG_HEIGHT = 240


# ==========================================
# THEMES
# ==========================================

THEMES = {
    "light": {
        "background": "#FFFFFF",
        "text": "#444444",
        "muted": "#777777",
        "accent": "#9B8AD9",
        "border": "#E5E0F0",
        "bar_background": "#EEEAF5",
    },

    "dark": {
        "background": "#0D1117",
        "text": "#E6EDF3",
        "muted": "#9198A1",
        "accent": "#B8A5E8",
        "border": "#30363D",
        "bar_background": "#30363D",
    },
}


LANGUAGE_COLORS = {
    "C++": "#F34B7D",
    "C": "#555555",
    "Rust": "#DEA584",
    "Python": "#3572A5",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "C#": "#178600",
    "Java": "#B07219",
    "Go": "#00ADD8",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Lua": "#000080",
    "Shell": "#89E051",
    "CMake": "#DA3434",
}


DEFAULT_LANGUAGE_COLOR = "#9B8AD9"


# ==========================================
# GITHUB API
# ==========================================

def api_request(url):

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HadeShiki-Profile-Stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(
        url,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"GitHub API error {error.code}: {body}"
        ) from error

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"Network error: {error.reason}"
        ) from error


def fetch_profile():

    url = f"{API_URL}/users/{USERNAME}"

    return api_request(url)


def fetch_repositories():

    repositories = []
    page = 1

    while True:

        url = (
            f"{API_URL}/users/{USERNAME}/repos"
            f"?type=owner&per_page=100&page={page}"
        )

        data = api_request(url)

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


def fetch_repository_languages(owner, repository):

    url = (
        f"{API_URL}/repos/"
        f"{owner}/{repository}/languages"
    )

    return api_request(url)


# ==========================================
# STATISTICS
# ==========================================

def collect_statistics(profile, repositories):

    original_repositories = [
        repository
        for repository in repositories
        if not repository.get("fork", False)
    ]

    total_stars = sum(
        repository.get("stargazers_count", 0)
        for repository in repositories
    )

    total_forks = sum(
        repository.get("forks_count", 0)
        for repository in repositories
    )

    languages = {}

    print("Analyzing repository languages...")

    for repository in original_repositories:

        name = repository.get("name")

        if not name:
            continue

        try:

            language_data = fetch_repository_languages(
                USERNAME,
                name,
            )

            for language, byte_count in language_data.items():

                languages[language] = (
                    languages.get(language, 0)
                    + byte_count
                )

        except RuntimeError as error:

            print(
                f"Warning: Could not analyze {name}: {error}"
            )

    return {
        "repositories": profile.get("public_repos", 0),
        "stars": total_stars,
        "forks": total_forks,
        "followers": profile.get("followers", 0),
        "languages": languages,
    }


# ==========================================
# SVG HELPERS
# ==========================================

def escape(value):

    return xml.escape(str(value))


def svg_start(width, height, theme):

    return f'''<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
    role="img">

    <title>GitHub Profile Statistics</title>

    <rect
        width="100%"
        height="100%"
        rx="12"
        fill="{theme["background"]}"
    />

    <style>
        text {{
            font-family: Arial, Helvetica, sans-serif;
        }}
    </style>
    '''


def svg_end():

    return "</svg>"


# ==========================================
# GITHUB STATISTICS SVG
# ==========================================

def generate_stats(data, mode):

    theme = THEMES[mode]

    svg = svg_start(
        WIDTH,
        STATS_HEIGHT,
        theme,
    )

    svg += f'''
    <text
        x="24"
        y="34"
        font-size="18"
        font-weight="bold"
        fill="{theme["text"]}">
        GitHub Statistics
    </text>

    <text
        x="24"
        y="54"
        font-size="11"
        fill="{theme["muted"]}">
        @{escape(USERNAME)}
    </text>
    '''

    items = [
        ("Public Repositories", data["repositories"]),
        ("Total Stars", data["stars"]),
        ("Total Forks", data["forks"]),
        ("Followers", data["followers"]),
    ]

    positions = [
        (24, 95),
        (225, 95),
        (24, 150),
        (225, 150),
    ]

    for item, position in zip(items, positions):

        label, value = item
        x, y = position

        svg += f'''
        <text
            x="{x}"
            y="{y}"
            font-size="20"
            font-weight="bold"
            fill="{theme["accent"]}">
            {value:,}
        </text>

        <text
            x="{x}"
            y="{y + 18}"
            font-size="11"
            fill="{theme["muted"]}">
            {escape(label)}
        </text>
        '''

    svg += svg_end()

    return svg


# ==========================================
# TOP LANGUAGES SVG
# ==========================================

def generate_languages(data, mode):

    theme = THEMES[mode]

    languages = sorted(
        data["languages"].items(),
        key=lambda item: item[1],
        reverse=True,
    )[:MAX_LANGUAGES]

    total_bytes = sum(
        value
        for _, value in languages
    )

    svg = svg_start(
        WIDTH,
        LANG_HEIGHT,
        theme,
    )

    svg += f'''
    <text
        x="24"
        y="34"
        font-size="18"
        font-weight="bold"
        fill="{theme["text"]}">
        Top Languages
    </text>
    '''

    if not languages or total_bytes == 0:

        svg += f'''
        <text
            x="24"
            y="75"
            font-size="12"
            fill="{theme["muted"]}">
            No language data available
        </text>
        '''

        svg += svg_end()

        return svg

    y = 65

    for language, byte_count in languages:

        percentage = (
            byte_count / total_bytes
        ) * 100

        bar_width = 270 * percentage / 100

        color = LANGUAGE_COLORS.get(
            language,
            DEFAULT_LANGUAGE_COLOR,
        )

        svg += f'''
        <text
            x="24"
            y="{y}"
            font-size="12"
            fill="{theme["text"]}">
            {escape(language)}
        </text>

        <text
            x="405"
            y="{y}"
            font-size="11"
            text-anchor="end"
            fill="{theme["muted"]}">
            {percentage:.1f}%
        </text>

        <rect
            x="24"
            y="{y + 8}"
            width="270"
            height="7"
            rx="3.5"
            fill="{theme["bar_background"]}"
        />

        <rect
            x="24"
            y="{y + 8}"
            width="{bar_width:.2f}"
            height="7"
            rx="3.5"
            fill="{color}"
        />
        '''

        y += 28

    svg += svg_end()

    return svg


# ==========================================
# FILE GENERATION
# ==========================================

def save_svg(filename, content):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = OUTPUT_DIR / filename

    path.write_text(
        content,
        encoding="utf-8",
    )

    print(f"Generated: {path}")


def main():

    print("=" * 45)
    print("HadeShiki GitHub Profile Generator")
    print("=" * 45)

    print(f"Username: {USERNAME}")

    profile = fetch_profile()

    repositories = fetch_repositories()

    statistics = collect_statistics(
        profile,
        repositories,
    )

    print("\nGenerating SVG files...")

    for mode in THEMES:

        save_svg(
            f"stats-{mode}.svg",
            generate_stats(
                statistics,
                mode,
            ),
        )

        save_svg(
            f"top-langs-{mode}.svg",
            generate_languages(
                statistics,
                mode,
            ),
        )

    print("\nGeneration completed successfully.")

    print(
        f"Repositories: {statistics['repositories']}"
    )

    print(
        f"Stars: {statistics['stars']}"
    )

    print(
        f"Forks: {statistics['forks']}"
    )

    print(
        f"Followers: {statistics['followers']}"
    )


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print(
            f"\nERROR: {error}",
            file=sys.stderr,
        )

        sys.exit(1)