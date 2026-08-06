"""Fetch bounded public-place metadata without trusting browser-supplied images."""

from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import socket
import ssl
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlsplit, urlunsplit

import certifi
from django.core import signing
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


PAGE_BYTES_LIMIT = 1 * 1024 * 1024
SOURCE_IMAGE_BYTES_LIMIT = 5 * 1024 * 1024
STORED_IMAGE_BYTES_LIMIT = 800 * 1024
METADATA_TOKEN_MAX_AGE_SECONDS = 30 * 60
METADATA_TOKEN_SALT = "kindlelise.plan-metadata.v1"
REQUEST_TIMEOUT_SECONDS = 5
REDIRECT_LIMIT = 2


class PlanMetadataUnavailable(Exception):
    """Hide provider, parsing and network detail behind one quiet failure."""


def normalise_public_https_url(value):
    """Return one normal HTTPS URL suitable for display and later fetching."""
    value = str(value or "").strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as error:
        raise ValueError("Enter an HTTPS URL.") from error
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Enter an HTTPS URL.")
    if parsed.username or parsed.password or port not in (None, 443):
        raise ValueError("Enter a normal HTTPS URL without credentials or a custom port.")
    return urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


def _global_addresses_for_url(url):
    """Resolve a URL once and return only globally routable target addresses."""
    normalised_url = normalise_public_https_url(url)
    hostname = urlsplit(normalised_url).hostname
    try:
        address_rows = socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as error:
        raise PlanMetadataUnavailable from error
    addresses = []
    for address_row in address_rows:
        address = address_row[4][0]
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as error:
            raise PlanMetadataUnavailable from error
        if not parsed_address.is_global:
            raise PlanMetadataUnavailable
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise PlanMetadataUnavailable
    return normalised_url, addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Verify the URL hostname while connecting to one pre-approved address."""

    def __init__(self, hostname, address):
        super().__init__(
            hostname,
            port=443,
            timeout=REQUEST_TIMEOUT_SECONDS,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        self._approved_address = address

    def connect(self):
        self.sock = socket.create_connection(
            (self._approved_address, self.port),
            self.timeout,
            self.source_address,
        )
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def _read_bounded_response(response, maximum_bytes):
    content_length = response.getheader("Content-Length")
    if content_length:
        try:
            if int(content_length) > maximum_bytes:
                raise PlanMetadataUnavailable
        except ValueError as error:
            raise PlanMetadataUnavailable from error
    response_bytes = response.read(maximum_bytes + 1)
    if len(response_bytes) > maximum_bytes:
        raise PlanMetadataUnavailable
    return response_bytes


def _fetch_https_bytes(url, allowed_content_types, maximum_bytes):
    """Fetch one bounded HTTPS resource, validating every redirect target."""
    current_url = url
    for redirect_count in range(REDIRECT_LIMIT + 1):
        current_url, addresses = _global_addresses_for_url(current_url)
        parsed = urlsplit(current_url)
        request_target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        last_error = None
        for address in addresses:
            connection = _PinnedHTTPSConnection(parsed.hostname, address)
            try:
                connection.request(
                    "GET",
                    request_target,
                    headers={
                        "Accept": ", ".join(allowed_content_types),
                        "Accept-Encoding": "identity",
                        "Host": parsed.hostname,
                        "User-Agent": "KindleliseMetadata/1.0",
                    },
                )
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    redirect_url = response.getheader("Location")
                    response.read(0)
                    if not redirect_url or redirect_count >= REDIRECT_LIMIT:
                        raise PlanMetadataUnavailable
                    current_url = urljoin(current_url, redirect_url)
                    break
                if response.status != 200:
                    raise PlanMetadataUnavailable
                content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
                if content_type not in allowed_content_types:
                    raise PlanMetadataUnavailable
                return current_url, content_type, _read_bounded_response(response, maximum_bytes)
            except PlanMetadataUnavailable:
                raise
            except (OSError, http.client.HTTPException, ssl.SSLError) as error:
                last_error = error
            finally:
                connection.close()
        else:
            raise PlanMetadataUnavailable from last_error
    raise PlanMetadataUnavailable


class _MetadataParser(HTMLParser):
    """Collect only JSON-LD and Open Graph values from bounded HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.json_ld = []
        self._inside_json_ld = False
        self._script_parts = []

    def handle_starttag(self, tag, attrs):
        attributes = {str(name).lower(): value for name, value in attrs}
        if tag.lower() == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            content = attributes.get("content")
            if key and content and key not in self.meta:
                self.meta[key] = content
        elif tag.lower() == "script" and (attributes.get("type") or "").lower() == "application/ld+json":
            self._inside_json_ld = True
            self._script_parts = []

    def handle_data(self, data):
        if self._inside_json_ld:
            self._script_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._inside_json_ld:
            self.json_ld.append("".join(self._script_parts))
            self._inside_json_ld = False
            self._script_parts = []


def _walk_json_nodes(value):
    if isinstance(value, dict):
        yield value
        for nested_value in value.values():
            yield from _walk_json_nodes(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_nodes(item)


def _node_types(node):
    node_types = node.get("@type", [])
    if isinstance(node_types, str):
        node_types = [node_types]
    return {str(node_type).rsplit("/", 1)[-1] for node_type in node_types}


def _clean_place_name(value):
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value if 0 < len(value) <= 200 else None


def _image_value(value):
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        for item in value:
            image_url = _image_value(item)
            if image_url:
                return image_url
    if isinstance(value, dict):
        return _image_value(value.get("contentUrl") or value.get("url"))
    return None


def _extract_metadata(html_bytes, document_url):
    parser = _MetadataParser()
    try:
        parser.feed(html_bytes.decode("utf-8", errors="replace"))
    except (UnicodeError, ValueError) as error:
        raise PlanMetadataUnavailable from error

    nodes = []
    for raw_json_ld in parser.json_ld:
        try:
            nodes.extend(_walk_json_nodes(json.loads(raw_json_ld)))
        except (json.JSONDecodeError, TypeError):
            continue

    place_name = None
    image_url = None
    for node in nodes:
        if "Event" not in _node_types(node):
            continue
        locations = node.get("location", [])
        if isinstance(locations, dict):
            locations = [locations]
        for location in locations if isinstance(locations, list) else []:
            if not isinstance(location, dict):
                continue
            place_name = _clean_place_name(location.get("name"))
            image_url = _image_value(location.get("image")) or _image_value(node.get("image"))
            if place_name:
                break
        if place_name:
            break

    place_types = {
        "Place",
        "LocalBusiness",
        "Museum",
        "Library",
        "CafeOrCoffeeShop",
        "Restaurant",
        "TouristAttraction",
        "Park",
    }
    if not place_name:
        for node in nodes:
            if not (_node_types(node) & place_types):
                continue
            place_name = _clean_place_name(node.get("name"))
            image_url = image_url or _image_value(node.get("image"))
            if place_name:
                break

    # General public-information pages often omit Place/Event JSON-LD. Use the
    # publisher's Open Graph name only as an editable last-resort suggestion.
    place_name = place_name or _clean_place_name(parser.meta.get("og:site_name"))

    image_url = image_url or parser.meta.get("og:image")
    if image_url:
        try:
            image_url = normalise_public_https_url(urljoin(document_url, image_url))
        except ValueError:
            image_url = None
    return place_name, image_url


def _normalise_thumbnail(source_bytes):
    """Return a bounded JPEG suitable for a decorative plan-card background."""
    try:
        with Image.open(BytesIO(source_bytes)) as source_image:
            width, height = source_image.size
            if width < 1 or height < 1 or max(width, height) > 8_192 or width * height > 40_000_000:
                raise PlanMetadataUnavailable
            source_image.load()
            normalised_image = ImageOps.exif_transpose(source_image).convert("RGB")
            normalised_image.thumbnail((1_200, 1_200), Image.Resampling.LANCZOS)
            output = BytesIO()
            normalised_image.save(output, format="JPEG", quality=82, optimize=True)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise PlanMetadataUnavailable from error
    image_bytes = output.getvalue()
    if not image_bytes or len(image_bytes) > STORED_IMAGE_BYTES_LIMIT:
        raise PlanMetadataUnavailable
    return image_bytes


def fetch_plan_metadata(public_url, user_id):
    """Return an editable place suggestion and a signed normalized thumbnail."""
    try:
        public_url = normalise_public_https_url(public_url)
        document_url, _, html_bytes = _fetch_https_bytes(
            public_url,
            {"text/html", "application/xhtml+xml"},
            PAGE_BYTES_LIMIT,
        )
        public_place, image_url = _extract_metadata(html_bytes, document_url)
        image_bytes = None
        if image_url:
            try:
                _, _, source_image_bytes = _fetch_https_bytes(
                    image_url,
                    {"image/jpeg", "image/png", "image/webp"},
                    SOURCE_IMAGE_BYTES_LIMIT,
                )
                image_bytes = _normalise_thumbnail(source_image_bytes)
            except PlanMetadataUnavailable:
                image_bytes = None
    except (PlanMetadataUnavailable, ValueError):
        return None
    if not public_place and not image_bytes:
        return None

    encoded_image = base64.b64encode(image_bytes).decode("ascii") if image_bytes else ""
    token = ""
    if image_bytes:
        token = signing.dumps(
            {
                "user_id": int(user_id),
                "public_url": public_url,
                "thumbnail": encoded_image,
            },
            salt=METADATA_TOKEN_SALT,
            compress=True,
        )
    return {
        "public_place": public_place or "",
        "thumbnail_found": bool(image_bytes),
        "thumbnail_preview": f"data:image/jpeg;base64,{encoded_image}" if image_bytes else "",
        "metadata_token": token,
    }


def thumbnail_from_metadata_token(token, user_id, public_url):
    """Return a trusted thumbnail only when token user and URL still match."""
    if not token or len(token) > 1_500_000:
        return None
    try:
        payload = signing.loads(
            token,
            salt=METADATA_TOKEN_SALT,
            max_age=METADATA_TOKEN_MAX_AGE_SECONDS,
        )
        expected_url = normalise_public_https_url(public_url)
        if payload.get("user_id") != int(user_id) or payload.get("public_url") != expected_url:
            return None
        image_bytes = base64.b64decode(payload.get("thumbnail", ""), validate=True)
    except (signing.BadSignature, ValueError, TypeError, AttributeError):
        return None
    if not image_bytes or len(image_bytes) > STORED_IMAGE_BYTES_LIMIT:
        return None
    return ContentFile(image_bytes, name="plan-thumbnail.jpg")
