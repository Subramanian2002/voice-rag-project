# ============================================================
# SESSION-SCOPED SOURCE STORAGE
# ============================================================

# Files uploaded by each browser session.
# {
#     "session-id": [
#         {
#             "file_path": "...",
#             "source_name": "...",
#             "source_type": "pdf",
#             "file_hash": "...",
#             "source_id": "...",
#             "session_id": "..."
#         }
#     ]
# }
uploaded_sources = {}


# URLs added by each browser session.
# {
#     "session-id": [
#         {
#             "url": "...",
#             "text": "...",
#             "source_type": "url",
#             "source_name": "...",
#             "source_url": "...",
#             "source_id": "...",
#             "session_id": "..."
#         }
#     ]
# }
url_sources = {}


# ============================================================
# FILE SOURCES
# ============================================================

def get_uploaded_sources(session_id: str) -> list:
    return uploaded_sources.get(session_id, [])


def add_uploaded_source(session_id: str, source: dict):
    uploaded_sources.setdefault(session_id, []).append(source)


def remove_uploaded_source(session_id: str, source_id: str):
    sources = uploaded_sources.get(session_id, [])

    uploaded_sources[session_id] = [
        source
        for source in sources
        if source.get("source_id") != source_id
    ]


def clear_uploaded_sources(session_id: str):
    uploaded_sources.pop(session_id, None)


# ============================================================
# URL SOURCES
# ============================================================

def get_url_sources(session_id: str) -> list:
    return url_sources.get(session_id, [])


def add_url_source(session_id: str, source: dict):
    url_sources.setdefault(session_id, []).append(source)


def remove_url_source(session_id: str, source_id: str):
    sources = url_sources.get(session_id, [])

    url_sources[session_id] = [
        source
        for source in sources
        if source.get("source_id") != source_id
    ]


def clear_url_sources(session_id: str):
    url_sources.pop(session_id, None)


# ============================================================
# ALL SESSION SOURCES
# ============================================================

def get_all_sources(session_id: str) -> dict:
    return {
        "files": get_uploaded_sources(session_id),
        "urls": get_url_sources(session_id)
    }


def clear_session_sources(session_id: str):
    uploaded_sources.pop(session_id, None)
    url_sources.pop(session_id, None)