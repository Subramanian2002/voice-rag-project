import requests
from bs4 import BeautifulSoup


def scrape_url(url: str) -> str:
    """
    Scrape readable text from a webpage.

    Returns:
        str: Cleaned webpage text.

    Raises:
        ValueError: If the URL cannot be scraped or
                    no readable text is found.
    """

    if not url or not url.strip():
        raise ValueError("URL cannot be empty.")

    url = url.strip()

    
    # Basic URL validation
    
    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        raise ValueError(
            "URL must start with http:// or https://"
        )

    
    # Browser-like headers
    

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    try:

        
        # Request webpage
        

        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        response.raise_for_status()

        
        # Check content type
        

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if (
            "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            raise ValueError(
                "The URL does not contain an HTML webpage."
            )

        
        # Parse HTML
        
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        
        # Remove unwanted elements
        
        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
                "svg"
            ]
        ):
            element.decompose()

        
        # Extract text
        
        text = soup.get_text(
            separator=" ",
            strip=True
        )

        
        text = " ".join(
            text.split()
        )

        if not text:
            raise ValueError(
                "No readable text found on the webpage."
            )

        return text

    
    # Timeout  

    except requests.exceptions.Timeout:

        raise ValueError(
            "The website took too long to respond."
        )

    
    # Connection errors
    

    except requests.exceptions.ConnectionError:

        raise ValueError(
            "Could not connect to the website."
        )

    
    # HTTP errors
    except requests.exceptions.HTTPError as e:

        status_code = (
            e.response.status_code
            if e.response is not None
            else "unknown"
        )

        raise ValueError(
            f"The website returned HTTP {status_code}."
        )

    
    # Other requests errors
    
    except requests.exceptions.RequestException as e:

        raise ValueError(
            f"Failed to scrape URL: {str(e)}"
        )

    except Exception as e:

        raise ValueError(
            f"Unexpected scraping error: {str(e)}"
        )