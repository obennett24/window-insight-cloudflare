import os
import re
import html
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

import requests
import markdown
import bleach


OWNER = "obennett24"
REPO = "window-insight-cloudflare"

SITE_NAME = "Window Insight"
BASE_URL = "https://window-insight-cloudflare.pages.dev"

DESCRIPTION = (
    "Window Insight offers practical articles and useful "
    "perspectives on window repair, glass maintenance, "
    "window hardware, energy efficiency, and home comfort."
)

OUTPUT = Path("site")
ARTICLES = OUTPUT / "articles"
ARTICLES.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"


CSS = """
:root {
  --ink: #30313e;
  --purple: #71638c;
  --lavender: #e9e3f1;
  --light: #f8f7fb;
  --white: #ffffff;
  --muted: #74717e;
  --border: #e3dfeb;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: var(--ink);
  background: var(--light);
  line-height: 1.75;
}

a {
  color: var(--purple);
}

.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--border);
}

.nav {
  max-width: 1120px;
  margin: auto;
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.brand {
  font-size: 27px;
  font-weight: 750;
  letter-spacing: -0.7px;
  color: var(--ink);
  text-decoration: none;
}

.nav-links a {
  margin-left: 24px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  text-decoration: none;
}

.nav-links a:hover {
  color: var(--purple);
}

.hero {
  background: linear-gradient(
    120deg,
    #30313e 0%,
    #514a67 60%,
    #71638c 100%
  );
  padding: 105px 24px;
  color: white;
}

.hero-inner {
  max-width: 1120px;
  margin: auto;
}

.eyebrow {
  color: #d9c8f1;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.hero h1 {
  max-width: 850px;
  font-size: clamp(38px, 5vw, 68px);
  line-height: 1.12;
  letter-spacing: -1.5px;
  margin: 24px 0;
}

.hero p {
  max-width: 750px;
  font-size: 19px;
  color: #f0edf5;
}

.container {
  max-width: 1120px;
  margin: 65px auto;
  padding: 0 24px;
}

.section-title {
  font-size: 34px;
  letter-spacing: -0.6px;
  margin-bottom: 30px;
}

.article-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(280px, 1fr)
  );
  gap: 26px;
}

.article-card {
  background: white;
  padding: 32px;
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 6px 22px rgba(48,49,62,0.04);
}

.article-card::before {
  content: "";
  display: block;
  width: 44px;
  height: 4px;
  background: var(--purple);
  border-radius: 4px;
  margin-bottom: 20px;
}

.article-card h2 {
  font-size: 23px;
  line-height: 1.4;
}

.article-card h2 a {
  color: var(--ink);
  text-decoration: none;
}

.article-card h2 a:hover {
  color: var(--purple);
}

.date {
  color: var(--muted);
  font-size: 14px;
}

.read-more {
  display: inline-block;
  margin-top: 12px;
  font-weight: 700;
  text-decoration: none;
}

.article-page {
  max-width: 880px;
  margin: 55px auto;
  padding: 48px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 12px;
}

.article-page h1 {
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.25;
}

.article-content {
  overflow-wrap: anywhere;
}

.article-content img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.article-content h2,
.article-content h3 {
  margin-top: 32px;
  color: var(--purple);
}

.article-content blockquote {
  border-left: 4px solid var(--purple);
  background: var(--light);
  margin: 24px 0;
  padding: 12px 22px;
}

.article-content pre,
.article-content table {
  max-width: 100%;
  overflow-x: auto;
}

.article-content table {
  display: block;
  border-collapse: collapse;
}

.article-content th,
.article-content td {
  border: 1px solid var(--border);
  padding: 10px;
}

.site-footer {
  background: var(--ink);
  color: white;
  text-align: center;
  padding: 34px 24px;
  margin-top: 65px;
  font-size: 14px;
}

@media (max-width: 600px) {
  .nav {
    flex-wrap: wrap;
  }

  .nav-links a {
    margin: 0 16px 0 0;
  }

  .hero {
    padding: 65px 24px;
  }

  .article-page {
    margin: 18px;
    padding: 24px;
  }
}
"""


def safe(value):
    return html.escape(str(value or ""), quote=True)


def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        bleach.clean(
            str(value or ""),
            tags=[],
            strip=True
        )
    ).strip()


def excerpt(value, limit=155):
    text = clean_text(value)

    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + "..."


def allowed_attribute(tag, name, value):
    allowed = {
        "a": {"href", "title"},
        "img": {
            "src", "alt", "title", "width", "height"
        },
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    }

    if name not in allowed.get(tag, set()):
        return False

    if name in ("href", "src"):
        url = str(value).strip()
        parsed = urlsplit(url)

        if parsed.scheme:
            return parsed.scheme.lower() in (
                "https", "http"
            )

        return (
            url.startswith("/")
            and not url.startswith("//")
        ) or url.startswith("#")

    return True


def render_content(body):
    rendered = markdown.markdown(
        str(body or ""),
        extensions=[
            "extra",
            "sane_lists",
            "nl2br"
        ],
    )

    return bleach.clean(
        rendered,
        tags=[
            "p", "br", "h1", "h2", "h3", "h4",
            "strong", "b", "em", "i",
            "a", "img", "ul", "ol", "li",
            "blockquote", "code", "pre", "hr",
            "table", "thead", "tbody",
            "tr", "th", "td", "del", "s",
        ],
        attributes=allowed_attribute,
        protocols=["http", "https"],
        strip=True,
    )


def layout(
    title,
    description,
    canonical,
    content,
    page_type="website"
):
    full_title = f"{title} | {SITE_NAME}"
    year = datetime.now(timezone.utc).year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(full_title)}</title>
<meta name="description" content="{safe(description)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{safe(canonical)}">

<meta property="og:type" content="{safe(page_type)}">
<meta property="og:site_name" content="{safe(SITE_NAME)}">
<meta property="og:title" content="{safe(full_title)}">
<meta property="og:description" content="{safe(description)}">
<meta property="og:url" content="{safe(canonical)}">

<meta name="twitter:card" content="summary">

<style>{CSS}</style>
</head>

<body>
<header class="site-header">
  <nav class="nav" aria-label="Main navigation">
    <a class="brand" href="/">{safe(SITE_NAME)}</a>

    <div class="nav-links">
      <a href="/">Home</a>
      <a href="/#articles">Articles</a>
    </div>
  </nav>
</header>

{content}

<footer class="site-footer">
  &copy; {year} {safe(SITE_NAME)}.
  Thoughtful insights for better window care.
</footer>
</body>
</html>"""


def get_issues():
    issues = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
            timeout=30,
        )

        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        issues.extend(
            item for item in batch
            if "pull_request" not in item
        )

        page += 1

    return issues


def publish():
    issues = get_issues()

    cards = []
    urls = [BASE_URL + "/"]
    active_files = set()

    for issue in issues:
        number = issue["number"]
        title = issue.get("title") or "Untitled"
        body = issue.get("body") or ""
        date = issue["created_at"][:10]

        filename = f"issue-{number}.html"
        active_files.add(filename)

        url = f"{BASE_URL}/articles/{filename}"
        urls.append(url)

        description = excerpt(body) or excerpt(title)
        content_html = render_content(body)

        article = f"""
<main class="article-page">
  <article>
    <h1>{safe(title)}</h1>
    <p class="date">
      <time datetime="{date}">{date}</time>
    </p>
    <div class="article-content">
      {content_html}
    </div>
  </article>
</main>"""

        page_html = layout(
            title,
            description,
            url,
            article,
            "article"
        )

        (ARTICLES / filename).write_text(
            page_html,
            encoding="utf-8"
        )

        cards.append(f"""
<article class="article-card">
  <p class="date">{date}</p>

  <h2>
    <a href="/articles/{filename}">
      {safe(title)}
    </a>
  </h2>

  <p>{safe(excerpt(body, 190))}</p>

  <a class="read-more" href="/articles/{filename}">
    Read article →
  </a>
</article>""")

    for old in ARTICLES.glob("issue-*.html"):
        if old.name not in active_files:
            old.unlink()

    listing = "\n".join(cards) if cards else (
        "<p>No articles published yet.</p>"
    )

    home = f"""
<section class="hero">
  <div class="hero-inner">
    <div class="eyebrow">Window care & home improvement</div>

    <h1>Fresh Perspectives on Better Windows</h1>

    <p>
      Discover practical ideas about window maintenance,
      glass care, repairs, energy efficiency, and
      creating a more comfortable living space.
    </p>
  </div>
</section>

<main class="container" id="articles">
  <h2 class="section-title">Latest Articles</h2>

  <div class="article-grid">
    {listing}
  </div>
</main>"""

    (OUTPUT / "index.html").write_text(
        layout(
            "Window Care Articles & Insights",
            DESCRIPTION,
            BASE_URL + "/",
            home
        ),
        encoding="utf-8"
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(
            f"  <url><loc>{xml_escape(url)}</loc></url>"
            for url in urls
        )
        + "\n</urlset>\n"
    )

    (OUTPUT / "sitemap.xml").write_text(
        sitemap,
        encoding="utf-8"
    )

    (OUTPUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8"
    )

    print(f"Published {len(issues)} articles.")


if __name__ == "__main__":
    publish()
