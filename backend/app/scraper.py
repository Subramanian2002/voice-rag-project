import re
import requests

from bs4 import BeautifulSoup

from playwright.sync_api import (
    sync_playwright
)

from urllib.parse import (
    urlparse,
    urljoin,
    urldefrag
)


# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = 20

PLAYWRIGHT_TIMEOUT = 30000

JINA_TIMEOUT = 60

MIN_TEXT_LENGTH = 100

# Maximum number of pages to crawl
MAX_PAGES = 3

# Maximum combined content stored from one website
MAX_TOTAL_CHARACTERS = 20000

JINA_READER_URL = (
    "https://r.jina.ai/"
)


# ============================================================
# PRIORITY KEYWORDS
# ============================================================

# Pages containing these words are considered more useful
# for company-related questions.

PRIORITY_KEYWORDS = [

    "about",

    "company",

    "leadership",

    "leader",

    "team",

    "management",

    "founder",

    "ceo",

    "director",

    "people",

    "contact",

    "service",

    "services",

    "solution",

    "solutions",

    "career",

    "careers"
]


# ============================================================
# IGNORED FILE EXTENSIONS
# ============================================================

IGNORED_EXTENSIONS = (

    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",

    # Videos
    ".mp4",
    ".avi",
    ".mov",
    ".webm",

    # Audio
    ".mp3",
    ".wav",

    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",

    # Archives
    ".zip",
    ".rar",

    # Web assets
    ".css",
    ".js",
    ".xml"
)


# ============================================================
# URL VALIDATION
# ============================================================

def validate_url(
    url: str
) -> str:

    url = url.strip()

    if not url:

        raise ValueError(
            "URL cannot be empty."
        )

    parsed = urlparse(
        url
    )

    if parsed.scheme not in (
        "http",
        "https"
    ):

        raise ValueError(
            "Only HTTP and HTTPS URLs are supported."
        )

    if not parsed.netloc:

        raise ValueError(
            "Invalid URL."
        )

    return url


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(
    base_url: str,
    link: str
) -> str | None:

    if not link:

        return None

    link = link.strip()

    # Ignore non-web links

    if link.startswith(
        (
            "#",
            "javascript:",
            "mailto:",
            "tel:",
            "data:"
        )
    ):

        return None

    absolute_url = urljoin(
        base_url,
        link
    )

    # Remove #fragment

    absolute_url, _ = urldefrag(
        absolute_url
    )

    parsed = urlparse(
        absolute_url
    )

    if parsed.scheme not in (
        "http",
        "https"
    ):

        return None

    if not parsed.netloc:

        return None

    path = parsed.path.lower()

    # Ignore files that are not webpages

    if path.endswith(
        IGNORED_EXTENSIONS
    ):

        return None

    return absolute_url


# ============================================================
# SAME DOMAIN CHECK
# ============================================================

def is_same_domain(
    base_url: str,
    target_url: str
) -> bool:

    base_domain = (
        urlparse(
            base_url
        )
        .netloc
        .lower()
        .replace(
            "www.",
            ""
        )
    )

    target_domain = (
        urlparse(
            target_url
        )
        .netloc
        .lower()
        .replace(
            "www.",
            ""
        )
    )

    return (
        base_domain
        == target_domain
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(
    text: str
) -> str:

    if not text:

        return ""

    # Normalize line endings

    text = re.sub(
        r"\r\n?",
        "\n",
        text
    )

    # Remove excessive spaces

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT TEXT FROM HTML
# ============================================================

def extract_html_text(
    html: str
) -> str:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove unnecessary elements

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "canvas",
            "iframe",
            "template"
        ]
    ):

        element.decompose()

    # Prefer <main>

    main_content = soup.find(
        "main"
    )

    if main_content:

        text = main_content.get_text(
            separator=" ",
            strip=True
        )

    else:

        # Otherwise prefer <article>

        article = soup.find(
            "article"
        )

        if article:

            text = article.get_text(
                separator=" ",
                strip=True
            )

        else:

            body = soup.find(
                "body"
            )

            if body:

                text = body.get_text(
                    separator=" ",
                    strip=True
                )

            else:

                text = soup.get_text(
                    separator=" ",
                    strip=True
                )

    return clean_text(
        text
    )


# ============================================================
# EXTRACT INTERNAL LINKS FROM HTML
# ============================================================

def extract_internal_links_from_html(
    base_url: str,
    html: str
) -> list[str]:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href"
        )

        normalized = normalize_url(
            base_url,
            href
        )

        if not normalized:

            continue

        if not is_same_domain(
            base_url,
            normalized
        ):

            continue

        if normalized not in links:

            links.append(
                normalized
            )

    return links


# ============================================================
# EXTRACT LINKS FROM JINA MARKDOWN
# ============================================================

def extract_links_from_markdown(
    base_url: str,
    markdown: str
) -> list[str]:

    links = []

    # Markdown format:
    #
    # [text](https://example.com/page)

    pattern = (
        r"\[[^\]]*\]"
        r"\((https?://[^)\s]+|/[^)\s]+)"
        r"\)"
    )

    matches = re.findall(
        pattern,
        markdown
    )

    for link in matches:

        normalized = normalize_url(
            base_url,
            link
        )

        if not normalized:

            continue

        if not is_same_domain(
            base_url,
            normalized
        ):

            continue

        if normalized not in links:

            links.append(
                normalized
            )

    return links


# ============================================================
# PRIORITIZE LINKS
# ============================================================

def prioritize_links(
    links: list[str]
) -> list[str]:

    def score(
        url: str
    ) -> int:

        lower_url = url.lower()

        total_score = 0

        for keyword in PRIORITY_KEYWORDS:

            if keyword in lower_url:

                total_score += 10

        return total_score

    return sorted(
        links,
        key=score,
        reverse=True
    )


# ============================================================
# REQUESTS SCRAPER
# ============================================================

def scrape_with_requests(
    url: str
) -> tuple[str, list[str]]:

    headers = {

        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 "
                "Safari/537.36"
            ),

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

        "Accept-Language":
            "en-US,en;q=0.9",

        "Connection":
            "keep-alive"
    }

    response = requests.get(

        url,

        headers=headers,

        timeout=REQUEST_TIMEOUT,

        allow_redirects=True
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "Content-Type",
            ""
        )
        .lower()
    )

    if (
        "text/html"
        not in content_type
    ):

        raise ValueError(
            "The URL did not return an HTML webpage."
        )

    html = response.text

    text = extract_html_text(
        html
    )

    if len(text) < MIN_TEXT_LENGTH:

        raise ValueError(
            "The webpage contains too little "
            "readable content."
        )

    links = extract_internal_links_from_html(
        url,
        html
    )

    return (
        text,
        links
    )


# ============================================================
# PLAYWRIGHT SCRAPER
# ============================================================

def scrape_with_playwright(
    url: str
) -> tuple[str, list[str]]:

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(

            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 "
                "Safari/537.36"
            ),

            viewport={
                "width": 1440,
                "height": 900
            }
        )

        try:

            page.goto(

                url,

                wait_until="domcontentloaded",

                timeout=PLAYWRIGHT_TIMEOUT
            )

            # Give JavaScript-rendered content a short time.

            page.wait_for_timeout(
                1500
            )

            html = page.content()

            text = extract_html_text(
                html
            )

            if len(text) < MIN_TEXT_LENGTH:

                raise ValueError(
                    "The webpage did not contain "
                    "enough readable content."
                )

            links = extract_internal_links_from_html(
                url,
                html
            )

            return (
                text,
                links
            )

        finally:

            browser.close()


# ============================================================
# JINA READER SCRAPER
# ============================================================

def scrape_with_jina(
    url: str
) -> tuple[str, list[str]]:

    reader_url = (
        JINA_READER_URL
        + url
    )

    headers = {

        "Accept":
            "text/plain",

        "User-Agent":
            (
                "QUiRRI-RAG/1.0 "
                "(web content extraction)"
            )
    }

    response = requests.get(

        reader_url,

        headers=headers,

        timeout=JINA_TIMEOUT
    )

    response.raise_for_status()

    text = response.text.strip()

    if not text:

        raise ValueError(
            "Jina Reader returned empty content."
        )

    lower_text = text.lower()

    error_indicators = [

        "error:",

        "failed to fetch",

        "page not found",

        "unable to fetch"
    ]

    if any(
        indicator in lower_text
        for indicator in error_indicators
    ):

        raise ValueError(
            "Jina Reader could not retrieve "
            "the webpage."
        )

    if len(text) < MIN_TEXT_LENGTH:

        raise ValueError(
            "Jina Reader returned too little "
            "readable content."
        )

    links = extract_links_from_markdown(
        url,
        text
    )

    return (
        clean_text(text),
        links
    )


# ============================================================
# SCRAPE ONE PAGE WITH FALLBACKS
# ============================================================

def scrape_single_page(
    url: str
) -> tuple[str, list[str], str]:

    requests_error = None

    playwright_error = None

    jina_error = None


    # --------------------------------------------------------
    # METHOD 1: REQUESTS
    # --------------------------------------------------------

    try:

        text, links = scrape_with_requests(
            url
        )

        print(
            f"URL scraped using HTTP: {url}"
        )

        return (
            text,
            links,
            "HTTP"
        )

    except Exception as e:

        requests_error = str(e)

        print(
            "Requests scraping failed:",
            requests_error
        )


    # --------------------------------------------------------
    # METHOD 2: PLAYWRIGHT
    # --------------------------------------------------------

    try:

        text, links = scrape_with_playwright(
            url
        )

        print(
            f"URL scraped using Playwright: {url}"
        )

        return (
            text,
            links,
            "Playwright"
        )

    except Exception as e:

        playwright_error = str(e)

        print(
            "Playwright scraping failed:",
            playwright_error
        )


    # --------------------------------------------------------
    # METHOD 3: JINA READER
    # --------------------------------------------------------

    try:

        text, links = scrape_with_jina(
            url
        )

        print(
            f"URL scraped using Jina Reader: {url}"
        )

        return (
            text,
            links,
            "Jina Reader"
        )

    except Exception as e:

        jina_error = str(e)

        print(
            "Jina Reader scraping failed:",
            jina_error
        )


    # --------------------------------------------------------
    # ALL METHODS FAILED
    # --------------------------------------------------------

    raise ValueError(

        "Unable to scrape webpage.\n\n"

        f"HTTP scraping failed: "
        f"{requests_error}\n\n"

        f"Browser scraping failed: "
        f"{playwright_error}\n\n"

        f"External Reader fallback failed: "
        f"{jina_error}"
    )


# ============================================================
# MAIN WEBSITE CRAWLER
# ============================================================

def scrape_url(
    url: str
) -> str:

    url = validate_url(
        url
    )

    visited = set()

    pages_to_visit = [
        url
    ]

    collected_pages = []

    all_discovered_links = set()


    # ========================================================
    # CRAWL
    # ========================================================

    while (

        pages_to_visit

        and

        len(visited) < MAX_PAGES
    ):

        current_url = pages_to_visit.pop(
            0
        )

        current_url = normalize_url(
            url,
            current_url
        )

        if not current_url:

            continue

        if current_url in visited:

            continue

        if not is_same_domain(
            url,
            current_url
        ):

            continue

        visited.add(
            current_url
        )

        print(
            f"\nScraping page "
            f"{len(visited)}/{MAX_PAGES}: "
            f"{current_url}"
        )


        try:

            text, links, method = (
                scrape_single_page(
                    current_url
                )
            )

            collected_pages.append(

                {
                    "url":
                        current_url,

                    "text":
                        text,

                    "method":
                        method
                }
            )

            print(
                f"Collected {len(text)} characters "
                f"using {method}"
            )


            # ------------------------------------------------
            # DISCOVER LINKS
            # ------------------------------------------------

            for link in links:

                if link in visited:

                    continue

                if not is_same_domain(
                    url,
                    link
                ):

                    continue

                all_discovered_links.add(
                    link
                )


        except Exception as e:

            print(
                f"Could not scrape page "
                f"{current_url}: {e}"
            )


        # ----------------------------------------------------
        # PRIORITIZE NEXT PAGES
        # ----------------------------------------------------

        candidates = [

            link

            for link
            in all_discovered_links

            if link not in visited
        ]

        candidates = prioritize_links(
            candidates
        )

        pages_to_visit = candidates[
            :MAX_PAGES
        ]


    # ========================================================
    # VERIFY RESULT
    # ========================================================

    if not collected_pages:

        raise ValueError(
            f"Unable to scrape the website: {url}"
        )


    # ========================================================
    # COMBINE CONTENT
    # ========================================================

    combined_parts = []

    for page in collected_pages:

        page_url = page[
            "url"
        ]

        page_text = page[
            "text"
        ]

        if not page_text:

            continue

        combined_parts.append(

            f"Source Page: {page_url}\n\n"
            f"{page_text}"
        )


    combined_text = (

        "\n\n"

        + "\n\n---\n\n".join(
            combined_parts
        )

    ).strip()


    # ========================================================
    # LIMIT TOTAL CONTENT
    # ========================================================

    if (
        len(combined_text)
        > MAX_TOTAL_CHARACTERS
    ):

        combined_text = (
            combined_text[
                :MAX_TOTAL_CHARACTERS
            ]
        )

        print(
            f"Website content limited to "
            f"{MAX_TOTAL_CHARACTERS} characters."
        )


    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if len(combined_text) < MIN_TEXT_LENGTH:

        raise ValueError(
            "The website did not contain enough "
            "readable content."
        )


    # ========================================================
    # FINAL LOG
    # ========================================================

    print(
        "\nWebsite crawling completed."
    )

    print(
        f"Pages collected: "
        f"{len(collected_pages)}"
    )

    print(
        f"Total characters: "
        f"{len(combined_text)}"
    )

    return combined_text