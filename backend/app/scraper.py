import re
import time
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
# CUSTOM EXCEPTION
# ============================================================

class UnsupportedURL(Exception):
    """
    Raised when the user provides an invalid or unsupported URL.
    """

    pass


# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = 30

PLAYWRIGHT_TIMEOUT = 45000

JINA_TIMEOUT = 90

MIN_TEXT_LENGTH = 100

# Maximum number of pages to crawl
MAX_PAGES = 5

# Maximum combined content stored from one website
MAX_TOTAL_CHARACTERS = 40000

# Number of retries for HTTP requests
REQUEST_RETRIES = 2

# Small delay between retries
RETRY_DELAY = 1


JINA_READER_URL = (
    "https://r.jina.ai/"
)


# ============================================================
# USER AGENT
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/151.0.0.0 "
    "Safari/537.36"
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

    # --------------------------------------------------------
    # Check data type
    # --------------------------------------------------------

    if not isinstance(url, str):

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL."
        )

    # --------------------------------------------------------
    # Remove leading/trailing spaces
    # --------------------------------------------------------

    url = url.strip()

    if not url:

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL."
        )

    # --------------------------------------------------------
    # Parse URL
    # --------------------------------------------------------

    parsed = urlparse(
        url
    )

    # --------------------------------------------------------
    # Only HTTP and HTTPS are supported
    # --------------------------------------------------------

    if parsed.scheme.lower() not in (
        "http",
        "https"
    ):

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL "
            "starting with http:// or https://."
        )

    # --------------------------------------------------------
    # URL must contain a hostname
    # --------------------------------------------------------

    if not parsed.netloc:

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL."
        )

    # --------------------------------------------------------
    # Extract hostname
    # --------------------------------------------------------

    try:

        hostname = parsed.hostname

    except ValueError:

        raise UnsupportedURL(
            "Unsupported URL. "
            "The website address is invalid."
        )

    if not hostname:

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL."
        )

    hostname = hostname.lower()

    # --------------------------------------------------------
    # Reject whitespace anywhere in URL
    # --------------------------------------------------------

    if any(
        character.isspace()
        for character in url
    ):

        raise UnsupportedURL(
            "Unsupported URL. "
            "The URL cannot contain spaces."
        )

    # --------------------------------------------------------
    # Reject nested URLs
    #
    # Example:
    #
    # https://www.whatsapp.com/https://huggingface.co
    #
    # --------------------------------------------------------

    path_and_query = (
        parsed.path
        + "?"
        + parsed.query
    )

    if re.search(
        r"https?://",
        path_and_query,
        re.IGNORECASE
    ):

        raise UnsupportedURL(
            "Unsupported URL. "
            "The URL contains another URL inside it."
        )

    # --------------------------------------------------------
    # Reject malformed hostnames
    # --------------------------------------------------------

    if (
        hostname.startswith(".")
        or hostname.endswith(".")
        or ".." in hostname
    ):

        raise UnsupportedURL(
            "Unsupported URL. "
            "The website address is invalid."
        )

    # --------------------------------------------------------
    # Public website validation
    #
    # Normal domains should contain a dot:
    #
    # google.com
    # knotopian.com
    # huggingface.co
    #
    # This rejects:
    #
    # https://hello
    # https://abc
    #
    # We still allow valid IPv4 addresses.
    # --------------------------------------------------------

    is_ipv4 = re.fullmatch(
        r"\d{1,3}(?:\.\d{1,3}){3}",
        hostname
    )

    if "." not in hostname and not is_ipv4:

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website domain."
        )

    # --------------------------------------------------------
    # Validate IPv4 values if applicable
    # --------------------------------------------------------

    if is_ipv4:

        try:

            octets = [
                int(part)
                for part in hostname.split(".")
            ]

            if any(
                octet > 255
                for octet in octets
            ):

                raise UnsupportedURL(
                    "Unsupported URL. "
                    "The IP address is invalid."
                )

        except ValueError:

            raise UnsupportedURL(
                "Unsupported URL. "
                "The IP address is invalid."
            )

    # --------------------------------------------------------
    # Reject obvious invalid hostname characters
    # --------------------------------------------------------

    if not re.fullmatch(
        r"[a-zA-Z0-9.\-:%]+",
        hostname
    ):

        raise UnsupportedURL(
            "Unsupported URL. "
            "The website address is invalid."
        )

    # --------------------------------------------------------
    # Return validated URL
    # --------------------------------------------------------

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
            "data:",
            "whatsapp:"
        )
    ):

        return None

    # Convert relative URL to absolute URL

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

    if not html:

        return ""

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
            "template",
            "nav",
            "footer"
        ]
    ):

        element.decompose()

    # --------------------------------------------------------
    # Prefer <main>
    # --------------------------------------------------------

    main_content = soup.find(
        "main"
    )

    if main_content:

        text = main_content.get_text(
            separator=" ",
            strip=True
        )

    else:

        # ----------------------------------------------------
        # Otherwise prefer <article>
        # ----------------------------------------------------

        article = soup.find(
            "article"
        )

        if article:

            text = article.get_text(
                separator=" ",
                strip=True
            )

        else:

            # ------------------------------------------------
            # Otherwise use body
            # ------------------------------------------------

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

    if not html:

        return []

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

    if not markdown:

        return []

    links = []

    # Markdown links:
    #
    # [text](https://example.com/page)
    # [text](/page)

    pattern = (
        r"\[[^\]]*\]"
        r"\(([^)\s]+)"
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
# REQUEST HEADERS
# ============================================================

def get_request_headers() -> dict:

    return {

        "User-Agent":
            USER_AGENT,

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "image/avif,"
                "image/webp,"
                "*/*;q=0.8"
            ),

        "Accept-Language":
            "en-US,en;q=0.9",

        "Accept-Encoding":
            "gzip, deflate",

        "Cache-Control":
            "no-cache",

        "Pragma":
            "no-cache",

        "Connection":
            "keep-alive",

        "Upgrade-Insecure-Requests":
            "1",

        "Sec-Fetch-Dest":
            "document",

        "Sec-Fetch-Mode":
            "navigate",

        "Sec-Fetch-Site":
            "none",

        "Sec-Fetch-User":
            "?1"
    }


# ============================================================
# REQUESTS SCRAPER
# ============================================================

def scrape_with_requests(
    url: str
) -> tuple[str, list[str]]:

    headers = get_request_headers()

    last_error = None

    for attempt in range(
        1,
        REQUEST_RETRIES + 1
    ):

        try:

            print(
                f"HTTP attempt "
                f"{attempt}/{REQUEST_RETRIES}: "
                f"{url}"
            )

            response = requests.get(

                url,

                headers=headers,

                timeout=REQUEST_TIMEOUT,

                allow_redirects=True
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            print(
                f"Final URL: "
                f"{response.url}"
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

            print(
                f"Content-Type: "
                f"{content_type}"
            )

            if (
                "text/html"
                not in content_type
                and "application/xhtml+xml"
                not in content_type
            ):

                raise ValueError(
                    "The URL did not return "
                    "an HTML webpage. "
                    f"Content-Type: {content_type}"
                )

            html = response.text

            if not html:

                raise ValueError(
                    "The server returned empty HTML."
                )

            text = extract_html_text(
                html
            )

            print(
                f"Extracted text length: "
                f"{len(text)}"
            )

            if len(text) < MIN_TEXT_LENGTH:

                raise ValueError(
                    "The webpage contains too little "
                    "readable content."
                )

            links = extract_internal_links_from_html(
                response.url,
                html
            )

            return (
                text,
                links
            )

        except Exception as e:

            last_error = str(e)

            print(
                f"HTTP attempt {attempt} failed: "
                f"{last_error}"
            )

            if attempt < REQUEST_RETRIES:

                time.sleep(
                    RETRY_DELAY
                )

    raise ValueError(
        f"HTTP scraping failed: {last_error}"
    )


# ============================================================
# PLAYWRIGHT SCRAPER
# ============================================================

def scrape_with_playwright(
    url: str
) -> tuple[str, list[str]]:

    print(
        f"Starting Playwright: {url}"
    )

    with sync_playwright() as p:

        browser = None

        try:

            browser = p.chromium.launch(

                headless=True,

                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox"
                ]
            )

            context = browser.new_context(

                user_agent=USER_AGENT,

                viewport={
                    "width": 1440,
                    "height": 900
                },

                locale="en-US",

                extra_http_headers={

                    "Accept-Language":
                        "en-US,en;q=0.9"
                }
            )

            page = context.new_page()

            # ------------------------------------------------
            # Block unnecessary resources
            # ------------------------------------------------

            def handle_route(
                route
            ):

                resource_type = (
                    route.request.resource_type
                )

                if resource_type in (
                    "image",
                    "media",
                    "font"
                ):

                    route.abort()

                else:

                    route.continue_()

            page.route(
                "**/*",
                handle_route
            )

            # ------------------------------------------------
            # Navigate
            # ------------------------------------------------

            response = page.goto(

                url,

                wait_until="domcontentloaded",

                timeout=PLAYWRIGHT_TIMEOUT
            )

            if response:

                print(
                    f"Playwright HTTP status: "
                    f"{response.status}"
                )

                print(
                    f"Playwright final URL: "
                    f"{page.url}"
                )

            # ------------------------------------------------
            # Allow JavaScript to render
            # ------------------------------------------------

            page.wait_for_timeout(
                3000
            )

            try:

                page.wait_for_load_state(
                    "networkidle",
                    timeout=10000
                )

            except Exception:

                print(
                    "Playwright networkidle timeout "
                    "- continuing with current page."
                )

            # ------------------------------------------------
            # Get rendered HTML
            # ------------------------------------------------

            html = page.content()

            if not html:

                raise ValueError(
                    "Playwright returned empty HTML."
                )

            text = extract_html_text(
                html
            )

            print(
                f"Playwright extracted text length: "
                f"{len(text)}"
            )

            if len(text) < MIN_TEXT_LENGTH:

                raise ValueError(
                    "The webpage did not contain "
                    "enough readable content "
                    "after JavaScript rendering."
                )

            links = extract_internal_links_from_html(
                page.url,
                html
            )

            return (
                text,
                links
            )

        except Exception as e:

            raise ValueError(
                f"Playwright scraping failed: {e}"
            )

        finally:

            if browser:

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

    print(
        f"Starting Jina Reader: {reader_url}"
    )

    headers = {

        "Accept":
            "text/plain, text/markdown, */*",

        "User-Agent":
            (
                "QUiRRI-RAG/1.0 "
                "(web content extraction)"
            )
    }

    try:

        response = requests.get(

            reader_url,

            headers=headers,

            timeout=JINA_TIMEOUT,

            allow_redirects=True
        )

        print(
            f"Jina HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"Jina Content-Type: "
            f"{response.headers.get('Content-Type', '')}"
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

            "failed to load",

            "page not found",

            "unable to fetch",

            "unable to load",

            "could not fetch",

            "couldn't fetch",

            "access denied",

            "403 forbidden",

            "404 not found",

            "502 bad gateway",

            "503 service unavailable"
        ]

        for indicator in error_indicators:

            if indicator in lower_text:

                raise ValueError(
                    "Jina Reader returned an error: "
                    f"{text[:500]}"
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

    except requests.exceptions.Timeout:

        raise ValueError(
            "Jina Reader request timed out."
        )

    except requests.exceptions.HTTPError as e:

        raise ValueError(
            f"Jina Reader HTTP error: {e}"
        )

    except requests.exceptions.RequestException as e:

        raise ValueError(
            f"Jina Reader network error: {e}"
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

    # ========================================================
    # METHOD 1: REQUESTS
    # ========================================================

    try:

        text, links = scrape_with_requests(
            url
        )

        print(
            f"URL scraped successfully using HTTP: "
            f"{url}"
        )

        return (
            text,
            links,
            "HTTP"
        )

    except Exception as e:

        requests_error = str(e)

        print(
            "\nRequests scraping failed:"
        )

        print(
            requests_error
        )

    # ========================================================
    # METHOD 2: PLAYWRIGHT
    # ========================================================

    try:

        text, links = scrape_with_playwright(
            url
        )

        print(
            f"URL scraped successfully using "
            f"Playwright: {url}"
        )

        return (
            text,
            links,
            "Playwright"
        )

    except Exception as e:

        playwright_error = str(e)

        print(
            "\nPlaywright scraping failed:"
        )

        print(
            playwright_error
        )

    # ========================================================
    # METHOD 3: JINA READER
    # ========================================================

    try:

        text, links = scrape_with_jina(
            url
        )

        print(
            f"URL scraped successfully using "
            f"Jina Reader: {url}"
        )

        return (
            text,
            links,
            "Jina Reader"
        )

    except Exception as e:

        jina_error = str(e)

        print(
            "\nJina Reader scraping failed:"
        )

        print(
            jina_error
        )

    # ========================================================
    # ALL METHODS FAILED
    # ========================================================

    error_message = (

        "Unable to scrape webpage.\n\n"

        "========== HTTP ==========\n"
        f"{requests_error}\n\n"

        "========== PLAYWRIGHT ==========\n"
        f"{playwright_error}\n\n"

        "========== JINA READER ==========\n"
        f"{jina_error}"
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "ALL SCRAPING METHODS FAILED"
    )

    print(
        error_message
    )

    print(
        "=" * 70
    )

    raise ValueError(
        error_message
    )


# ============================================================
# MAIN WEBSITE CRAWLER
# ============================================================

def scrape_url(
    url: str
) -> str:

    # ========================================================
    # VALIDATE URL BEFORE ANY SCRAPING
    # ========================================================

    url = validate_url(
        url
    )

    # ========================================================
    # NORMALIZE INITIAL URL
    # ========================================================

    normalized_start_url = normalize_url(
        url,
        url
    )

    if not normalized_start_url:

        raise UnsupportedURL(
            "Unsupported URL. "
            "Please enter a valid website URL."
        )

    url = normalized_start_url

    # ========================================================
    # CRAWLER STATE
    # ========================================================

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
            "\n"
            + "=" * 70
        )

        print(
            f"Scraping page "
            f"{len(visited)}/{MAX_PAGES}"
        )

        print(
            current_url
        )

        print(
            "=" * 70
        )

        # ====================================================
        # SCRAPE PAGE
        # ====================================================

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

            # =================================================
            # DISCOVER LINKS
            # =================================================

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
                f"\nCould not scrape page "
                f"{current_url}:"
            )

            print(
                str(e)
            )

        # ====================================================
        # PRIORITIZE NEXT PAGES
        # ====================================================

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

            "Unable to scrape the website: "
            f"{url}\n\n"

            "All scraping methods failed. "
            "Check the backend terminal for "
            "the detailed HTTP, Playwright and "
            "Jina Reader errors."
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

        page_method = page[
            "method"
        ]

        if not page_text:

            continue

        combined_parts.append(

            f"Source Page: {page_url}\n"
            f"Scraping Method: {page_method}\n\n"
            f"{page_text}"
        )

    combined_text = (

        "\n\n---\n\n"

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
            f"\nWebsite content limited to "
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
        "\n"
        + "=" * 70
    )

    print(
        "WEBSITE CRAWLING COMPLETED"
    )

    print(
        "=" * 70
    )

    print(
        f"Pages collected: "
        f"{len(collected_pages)}"
    )

    print(
        f"Pages attempted: "
        f"{len(visited)}"
    )

    print(
        f"Total characters: "
        f"{len(combined_text)}"
    )

    print(
        "Methods used:"
    )

    for page in collected_pages:

        print(
            f"  - {page['method']}: "
            f"{page['url']}"
        )

    print(
        "=" * 70
    )

    return combined_text