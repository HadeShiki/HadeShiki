import json
import os
import urllib.request
import xml.sax.saxutils as xml

USERNAME = os.getenv("GITHUB_USERNAME", "HadeShiki")
TOKEN = os.getenv("GITHUB_TOKEN")

API = "https://api.github.com"

THEMES = {
    "light": {
        "bg": "#FFFFFF",
        "text": "#444444",
        "muted": "#777777",
        "accent": "#9B8AD9",
        "border": "#E5E0F0",
        "bar_bg": "#EEEAF5",
    },
    "dark": {
        "bg": "#0D1117",
        "text": "#E6EDF3",
        "muted": "#9198A1",
        "accent": "#B8A5E8",
        "border": "#30363D",
        "bar_bg": "#30363D",
    },
}


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HadeShiki-Profile-Stats",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def fetch_profile():
    return request_json(f"{API}/users/{USERNAME}")


def fetch_repositories():
    repos = []
    page = 1

    while True:
        url = (
            f"{API}/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&type=owner"
        )

        data = request_json(url)

        if not data:
            break

        repos.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repos


def collect_stats(profile, repos):
    original_repos = [
        repo for repo in repos
        if not repo.get("fork", False)
    ]

    stars = sum(
        repo.get("stargazers_count", 0)
        for repo in repos
    )

    forks = sum(
        repo.get("forks_count", 0)
        for repo in repos
    )

    languages = {}

    for repo in original_repos:
        language = repo.get("language")

        if language:
            languages[language] = (
                languages.get(language, 0) + 1
            )

    return {
        "repos": profile.get("public_repos", 0),
        "followers": profile.get("followers", 0),
        "stars": stars,
        "forks": forks,
        "languages": languages,
    }


def svg_header(width, height, theme):
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}" height="{height}"
        viewBox="0 0 {width} {height}">
        <rect width="100%" height="100%"
        rx="12" fill="{theme["bg"]}"/>
        <style>
        text {{
            font-family: Arial, Helvetica, sans-serif;
        }}
        </style>
    '''


def generate_stats(stats, mode):
    theme = THEMES[mode]
    width, height = 430, 190

    items = [
        ("Public Repositories", stats["repos"]),
        ("Total Stars", stats["stars"]),
        ("Total Forks", stats["forks"]),
        ("Followers", stats["followers"]),
    ]

    svg = svg_header(width, height, theme)

    svg += f'''
    <text x="24" y="34" font-size="18"
        font-weight="bold" fill="{theme["text"]}">
        GitHub Statistics
    </text>

    <text x="24" y="54" font-size="11"
        fill="{theme["muted"]}">
        @{xml.escape(USERNAME)}
    </text>
    '''

    positions = [
        (24, 95),
        (225, 95),
        (24, 150),
        (225, 150),
    ]

    for (label, value), (x, y) in zip(items, positions):
        svg += f'''
        <text x="{x}" y="{y}"
            font-size="20" font-weight="bold"
            fill="{theme["accent"]}">
            {value:,}
        </text>

        <text x="{x}" y="{y + 18}"
            font-size="11" fill="{theme["muted"]}">
            {label}
        </text>
        '''

    svg += "</svg>"

    return svg


def generate_languages(stats, mode):
    theme = THEMES[mode]
    width, height = 430, 190

    languages = sorted(
        stats["languages"].items(),
        key=lambda item: item[1],
        reverse=True
    )[:6]

    total = sum(value for _, value in languages) or 1

    svg = svg_header(width, height, theme)

    svg += f'''
    <text x="24" y="34" font-size="18"
        font-weight="bold" fill="{theme["text"]}">
        Top Languages
    </text>
    '''

    colors = [
        "#9B8AD9",
        "#39C5BB",
        "#6C9FE8",
        "#D69BC8",
        "#8BC6A8",
        "#D6B477",
    ]

    y = 62

    for index, (language, count) in enumerate(languages):
        percentage = count / total * 100
        bar_width = 270 * percentage / 100
        color = colors[index % len(colors)]

        svg += f'''
        <text x="24" y="{y}"
            font-size="12" fill="{theme["text"]}">
            {xml.escape(language)}
        </text>

        <text x="405" y="{y}"
            font-size="11" text-anchor="end"
            fill="{theme["muted"]}">
            {percentage:.1f}%
        </text>

        <rect x="24" y="{y + 8}"
            width="270" height="7"
            rx="3.5" fill="{theme["bar_bg"]}"/>

        <rect x="24" y="{y + 8}"
            width="{bar_width:.2f}" height="7"
            rx="3.5" fill="{color}"/>
        '''

        y += 25

    if not languages:
        svg += f'''
        <text x="24" y="80" font-size="12"
            fill="{theme["muted"]}">
            No language data available
        </text>
        '''

    svg += "</svg>"

    return svg


def save_svg(filename, content):
    os.makedirs("profile", exist_ok=True)

    with open(
        os.path.join("profile", filename),
        "w",
        encoding="utf-8"
    ) as file:
        file.write(content)


def main():
    print(f"Generating stats for {USERNAME}...")

    profile = fetch_profile()
    repos = fetch_repositories()

    stats = collect_stats(profile, repos)

    for mode in THEMES:
        save_svg(
            f"stats-{mode}.svg",
            generate_stats(stats, mode)
        )

        save_svg(
            f"top-langs-{mode}.svg",
            generate_languages(stats, mode)
        )

    print("Successfully generated all profile SVG files.")


if __name__ == "__main__":
    main()