"""References to pictures stored by Home Assistant's image-upload service."""

import re


def picture_url(image_id):
    """Never turn arbitrary settings or external URLs into portrait requests."""
    if not isinstance(image_id, str) or re.fullmatch(r"[0-9a-f]{32}", image_id) is None:
        return None
    return f"/api/image/serve/{image_id}/512x512"
