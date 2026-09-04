"""Fetch bounded public-place metadata without trusting browser-supplied images."""

# KEYWORD: HTTPS — the encrypted form of a public web address.
# KEYWORD: DNS — the lookup that turns a website name into the network address used to contact it.
# KEYWORD: token — a signed, short-lived value that proves fetched image details came from this site.
# KEYWORD: metadata — a public place's name and image details read from its information page.


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

# =============================================================================
# FETCHING LIMITS AND TOKEN SETTINGS
# Defines the boundaries applied to public pages, images, redirects, and proof.
# =============================================================================

# WHY: Bounds public pages, source images, and saved thumbnails at each separate stage of fetching.
PAGE_BYTES_LIMIT = 1 * 1024 * 1024
SOURCE_IMAGE_BYTES_LIMIT = 5 * 1024 * 1024
STORED_IMAGE_BYTES_LIMIT = 800 * 1024

# WHY: Makes fetched image proof expire after enough time to complete the plan form, not indefinitely.
METADATA_TOKEN_MAX_AGE_SECONDS = 30 * 60

# WHY: Separates these signed values from every other signed value; this is not a password or credential.
METADATA_TOKEN_SALT = "kindlelise.plan-metadata.v1"  # nosec B105

# WHY: Stops slow outside sites and repeated redirects holding the request open for too long.
REQUEST_TIMEOUT_SECONDS = 5
REDIRECT_LIMIT = 2


# WHY: Keeps the PlanMetadataUnavailable information and its rules together so they stay consistent.
class PlanMetadataUnavailable(Exception):
    """Hide provider, parsing and network detail behind one quiet failure."""


# =============================================================================
# SAFE PUBLIC HTTPS FETCHING
# Checks public addresses and downloads bounded page or image bytes.
# =============================================================================

# WHY: Keeps the normalise public https url steps in one named place so they can be understood, checked, and reused.
def normalise_public_https_url(value):
    """Return one normal HTTPS URL suitable for display and later fetching."""
    # WHY: Treats a missing value as empty text and removes harmless surrounding spaces.
    value = str(value or "").strip()

    # WHY: Lets the standard URL reader split the address while turning malformed ports into one clear error.
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as error:
        raise ValueError("Enter an HTTPS URL.") from error
    # WHY: Requires encrypted public web addresses with a real host.
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Enter an HTTPS URL.")
    # WHY: Refuses embedded credentials and unusual ports that could point at private services.
    if parsed.username or parsed.password or port not in (None, 443):
        raise ValueError("Enter a normal HTTPS URL without credentials or a custom port.")
    # WHY: Rebuilds a consistent HTTPS address and deliberately removes any page fragment.
    return urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


# WHY: Keeps the global addresses for url steps in one named place so they can be understood, checked, and reused.
def _global_addresses_for_url(url):
    """Resolve a URL once and return only globally routable target addresses."""
    # WHY: Reapplies address rules before every lookup, including after redirects.
    normalised_url = normalise_public_https_url(url)
    hostname = urlsplit(normalised_url).hostname
    # WHY: Resolves only normal web connections on HTTPS port 443.
    try:
        address_rows = socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as error:
        raise PlanMetadataUnavailable from error
    # WHY: Checks every returned network address because one hostname can point to several places.
    addresses = []
    for address_row in address_rows:
        address = address_row[4][0]
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as error:
            raise PlanMetadataUnavailable from error
        # WHY: Refuses local, private, reserved, and otherwise non-public network destinations.
        if not parsed_address.is_global:
            raise PlanMetadataUnavailable
        # WHY: Keeps each approved address once so failed duplicate connection attempts are avoided.
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise PlanMetadataUnavailable
    return normalised_url, addresses


# WHY: Keeps the PinnedHTTPSConnection information and its rules together so they stay consistent.
class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Verify the URL hostname while connecting to one pre-approved address."""

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self, hostname, address):
        # WHY: Verifies the public hostname's certificate while applying the short request timeout.
        super().__init__(
            hostname,
            port=443,
            timeout=REQUEST_TIMEOUT_SECONDS,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        # WHY: Remembers the already checked public address so a second name lookup cannot redirect the connection.
        self._approved_address = address

    # WHY: Keeps the connect steps in one named place so they can be understood, checked, and reused.
    def connect(self):
        # WHY: Connects directly to the approved address rather than resolving the hostname again.
        self.sock = socket.create_connection(
            (self._approved_address, self.port),
            self.timeout,
            self.source_address,
        )
        # WHY: Still verifies that the encrypted certificate belongs to the original public hostname.
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


# WHY: Keeps the read bounded response steps in one named place so they can be understood, checked, and reused.
def _read_bounded_response(response, maximum_bytes):
    # WHY: Rejects a declared oversized response before downloading its body.
    content_length = response.getheader("Content-Length")
    if content_length:
        try:
            if int(content_length) > maximum_bytes:
                raise PlanMetadataUnavailable
        except ValueError as error:
            raise PlanMetadataUnavailable from error
    # WHY: Reads one extra byte so a missing or dishonest length header cannot bypass the limit.
    response_bytes = response.read(maximum_bytes + 1)
    if len(response_bytes) > maximum_bytes:
        raise PlanMetadataUnavailable
    return response_bytes


# WHY: Loads https bytes while applying the same safety limits each time.
def _fetch_https_bytes(url, allowed_content_types, maximum_bytes):
    """Fetch one bounded HTTPS resource, validating every redirect target."""
    # WHY: Tracks the current destination separately because a permitted public page may redirect.
    current_url = url

    # WHY: Allows only the initial request plus the small fixed number of redirects.
    for redirect_count in range(REDIRECT_LIMIT + 1):
        # WHY: Rechecks every redirect hostname and freezes its public addresses before connecting.
        current_url, addresses = _global_addresses_for_url(current_url)
        parsed = urlsplit(current_url)
        request_target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        # WHY: Tries each approved address because a public hostname may have one temporarily unavailable server.
        last_error = None
        for address in addresses:
            connection = _PinnedHTTPSConnection(parsed.hostname, address)
            try:
                # WHY: Requests an uncompressed response so byte limits apply to exactly what is read.
                connection.request(
                    "GET",
                    request_target,
                    headers={
                        "Accept": ", ".join(allowed_content_types),
                        "Accept-Encoding": "identity",
                        "Host": parsed.hostname,
                        "User-Agent": "KindeliseMetadata/1.0",
                    },
                )
                response = connection.getresponse()

                # WHY: Accepts only ordinary redirect codes and rechecks the new target on the next loop.
                if response.status in {301, 302, 303, 307, 308}:
                    redirect_url = response.getheader("Location")
                    response.read(0)
                    if not redirect_url or redirect_count >= REDIRECT_LIMIT:
                        raise PlanMetadataUnavailable
                    current_url = urljoin(current_url, redirect_url)
                    break
                # WHY: Uses only a complete successful response, never an error page or partial result.
                if response.status != 200:
                    raise PlanMetadataUnavailable
                # WHY: Checks the server-declared kind before treating bytes as HTML or an image.
                content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
                if content_type not in allowed_content_types:
                    raise PlanMetadataUnavailable
                return current_url, content_type, _read_bounded_response(response, maximum_bytes)
            # WHY: Keeps deliberate safety refusals final instead of trying to work around them.
            except PlanMetadataUnavailable:
                raise
            # WHY: Remembers a normal connection failure and tries the next already approved address.
            except (OSError, http.client.HTTPException, ssl.SSLError) as error:
                last_error = error
            finally:
                # WHY: Releases the network connection after success, refusal, or failure.
                connection.close()
        else:
            raise PlanMetadataUnavailable from last_error
    raise PlanMetadataUnavailable


# =============================================================================
# PUBLIC PAGE METADATA READING
# Reads supported place names and image addresses from bounded public HTML.
# =============================================================================

# WHY: Keeps the MetadataParser information and its rules together so they stay consistent.
class _MetadataParser(HTMLParser):
    """Collect only JSON-LD and Open Graph values from bounded HTML."""

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self):
        # WHY: Lets Python handle normal HTML character references before values are inspected.
        super().__init__(convert_charrefs=True)

        # WHY: Stores only the small public fields this feature understands, not a copy of the whole page.
        self.meta = {}
        self.json_ld = []
        self._inside_json_ld = False
        self._script_parts = []

    # WHY: Keeps the handle starttag steps in one named place so they can be understood, checked, and reused.
    def handle_starttag(self, tag, attrs):
        # WHY: Makes HTML attribute names consistent because websites may use different capitalisation.
        attributes = {str(name).lower(): value for name, value in attrs}

        # WHY: Keeps the first value for each public meta name instead of accepting later conflicting duplicates.
        if tag.lower() == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            content = attributes.get("content")
            if key and content and key not in self.meta:
                self.meta[key] = content
        # WHY: Reads only labelled public JSON data, never ordinary page scripts.
        elif tag.lower() == "script" and (attributes.get("type") or "").lower() == "application/ld+json":
            self._inside_json_ld = True
            self._script_parts = []

    # WHY: Keeps the handle data steps in one named place so they can be understood, checked, and reused.
    def handle_data(self, data):
        # WHY: Collects text only while inside the recognised public-data script block.
        if self._inside_json_ld:
            self._script_parts.append(data)

    # WHY: Keeps the handle endtag steps in one named place so they can be understood, checked, and reused.
    def handle_endtag(self, tag):
        # WHY: Joins one completed public-data block and resets state before the next one.
        if tag.lower() == "script" and self._inside_json_ld:
            self.json_ld.append("".join(self._script_parts))
            self._inside_json_ld = False
            self._script_parts = []


# WHY: Keeps the walk json nodes steps in one named place so they can be understood, checked, and reused.
def _walk_json_nodes(value):
    # WHY: Yields every labelled object even when a website nests it several levels deep.
    if isinstance(value, dict):
        yield value
        for nested_value in value.values():
            yield from _walk_json_nodes(nested_value)
    # WHY: Handles lists of public-data objects using the same recursive walk.
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_nodes(item)


# WHY: Keeps the node types steps in one named place so they can be understood, checked, and reused.
def _node_types(node):
    # WHY: Treats one type and a list of types consistently before comparing their final names.
    node_types = node.get("@type", [])
    if isinstance(node_types, str):
        node_types = [node_types]
    return {str(node_type).rsplit("/", 1)[-1] for node_type in node_types}


# WHY: Keeps the clean place name steps in one named place so they can be understood, checked, and reused.
def _clean_place_name(value):
    # WHY: Accepts only text, collapses repeated whitespace, and applies the plan place-name limit.
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value if 0 < len(value) <= 200 else None


# WHY: Keeps the image value steps in one named place so they can be understood, checked, and reused.
def _image_value(value):
    # WHY: Handles the common ways websites publish an image: one URL, a list, or a labelled object.
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


# WHY: Turns common Schema.org PostalAddress values into one short editable directions address.
def _address_value(value):
    if isinstance(value, str):
        return " ".join(value.split())[:300] or None
    if not isinstance(value, dict):
        return None
    country = value.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = (
        value.get("streetAddress"),
        value.get("addressLocality"),
        value.get("addressRegion"),
        value.get("postalCode"),
        country,
    )
    cleaned_parts = [" ".join(str(part).split()) for part in parts if part]
    return ", ".join(dict.fromkeys(cleaned_parts))[:300] or None


# WHY: Keeps the extract metadata steps in one named place so they can be understood, checked, and reused.
def _extract_metadata(html_bytes, document_url):
    # WHY: Uses the narrow parser above so only supported public place details are collected.
    parser = _MetadataParser()
    try:
        parser.feed(html_bytes.decode("utf-8", errors="replace"))
    except (UnicodeError, ValueError) as error:
        raise PlanMetadataUnavailable from error

    # WHY: Ignores malformed public-data blocks while keeping usable blocks from the same page.
    nodes = []
    for raw_json_ld in parser.json_ld:
        try:
            nodes.extend(_walk_json_nodes(json.loads(raw_json_ld)))
        except (json.JSONDecodeError, TypeError):
            continue

    # WHY: Looks for an event location first because it is usually more precise than the page publisher's name.
    place_name = None
    public_address = None
    image_url = None
    for node in nodes:
        if "Event" not in _node_types(node):
            continue
        locations = node.get("location", [])
        if isinstance(locations, dict):
            locations = [locations]
        # WHY: Checks each labelled event location until one usable public place name is found.
        for location in locations if isinstance(locations, list) else []:
            if not isinstance(location, dict):
                continue
            place_name = _clean_place_name(location.get("name"))
            public_address = _address_value(location.get("address"))
            image_url = _image_value(location.get("image")) or _image_value(node.get("image"))
            if place_name or public_address:
                break
        if place_name or public_address:
            break

    # WHY: Limits the next search to recognised kinds of established public places.
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
    # WHY: Falls back to a page describing the place itself when no event location was published.
    if not place_name:
        for node in nodes:
            if not (_node_types(node) & place_types):
                continue
            place_name = _clean_place_name(node.get("name"))
            public_address = public_address or _address_value(node.get("address"))
            image_url = image_url or _image_value(node.get("image"))
            if place_name:
                break

    # WHY: General information pages may omit labelled place data, so their public site name is an editable last resort.
    place_name = place_name or _clean_place_name(parser.meta.get("og:site_name"))

    # WHY: Uses the public preview image only when no more specific labelled image was found.
    image_url = image_url or parser.meta.get("og:image")
    if image_url:
        try:
            # WHY: Resolves a relative image against the page and then applies the full safe HTTPS rule.
            image_url = normalise_public_https_url(urljoin(document_url, image_url))
        except ValueError:
            image_url = None
    return place_name, public_address, image_url


# =============================================================================
# PLAN IMAGE PREPARATION
# Converts a checked source image into the bounded JPEG stored for plan cards.
# =============================================================================

# WHY: Keeps the normalise thumbnail steps in one named place so they can be understood, checked, and reused.
def _normalise_thumbnail(source_bytes):
    """Return a bounded JPEG suitable for a decorative plan-card background."""
    try:
        # WHY: Opens the downloaded bytes as a real image instead of trusting the server's content label alone.
        with Image.open(BytesIO(source_bytes)) as source_image:
            width, height = source_image.size
            # WHY: Refuses empty or extreme dimensions that could consume excessive memory while decoding.
            if width < 1 or height < 1 or max(width, height) > 8_192 or width * height > 40_000_000:
                raise PlanMetadataUnavailable

            # WHY: Fully reads the pixels now so a damaged file fails before a plan can use it.
            source_image.load()

            # WHY: Applies camera rotation, removes embedded information, and uses a consistent colour mode.
            normalised_image = ImageOps.exif_transpose(source_image).convert("RGB")

            # WHY: Shrinks large images to a practical card-background size without stretching them.
            normalised_image.thumbnail((1_200, 1_200), Image.Resampling.LANCZOS)
            output = BytesIO()
            # WHY: Saves one predictable compressed format that every plan card can display.
            normalised_image.save(output, format="JPEG", quality=82, optimize=True)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise PlanMetadataUnavailable from error
    # WHY: Applies the final stored-size limit after conversion because output size cannot be known beforehand.
    image_bytes = output.getvalue()
    if not image_bytes or len(image_bytes) > STORED_IMAGE_BYTES_LIMIT:
        raise PlanMetadataUnavailable
    return image_bytes


# WHY: Lets a visitor-supplied fallback use the exact same safe plan-card image pipeline as fetched metadata.
def thumbnail_from_uploaded_file(uploaded_file):
    """Return one normalized JPEG ContentFile from a bounded uploaded plan image."""
    if not uploaded_file or uploaded_file.size > SOURCE_IMAGE_BYTES_LIMIT:
        raise PlanMetadataUnavailable
    uploaded_file.seek(0)
    source_bytes = uploaded_file.read(SOURCE_IMAGE_BYTES_LIMIT + 1)
    if len(source_bytes) > SOURCE_IMAGE_BYTES_LIMIT:
        raise PlanMetadataUnavailable
    return ContentFile(
        _normalise_thumbnail(source_bytes),
        name="uploaded-plan-thumbnail.jpg",
    )


# =============================================================================
# PLAN METADATA RESULT
# Combines the place suggestion and optional image proof returned to the form.
# =============================================================================

# WHY: Loads plan metadata while applying the same safety limits each time.
def fetch_plan_metadata(public_url, user_id):
    """Return an editable place suggestion and a signed normalized thumbnail."""
    # WHY: Treats all unsafe, unavailable, or malformed public pages as the same quiet no-result outcome.
    try:
        # WHY: Normalises once so the exact checked address is also the address bound into the signed token.
        public_url = normalise_public_https_url(public_url)

        # WHY: Downloads only a bounded HTML page with one of the two accepted page content types.
        document_url, _, html_bytes = _fetch_https_bytes(
            public_url,
            {"text/html", "application/xhtml+xml"},
            PAGE_BYTES_LIMIT,
        )
        # WHY: Extracts an editable name suggestion and optional separately checked image address.
        public_place, public_address, image_url = _extract_metadata(html_bytes, document_url)
        image_bytes = None
        if image_url:
            # WHY: Image failure does not discard a useful place name; it simply returns no thumbnail.
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
    # WHY: Returns no result when the public page provided neither useful part of the feature.
    if not public_place and not public_address and not image_bytes:
        return None

    # WHY: Turns the small clean image into text so it can be previewed and placed inside signed proof.
    encoded_image = base64.b64encode(image_bytes).decode("ascii") if image_bytes else ""

    # WHY: Empty means no thumbnail was returned; this value is never used as account authentication.
    token = ""  # nosec B105
    if image_bytes:
        # WHY: Binds the image to this account and public URL so a browser cannot swap either before saving.
        token = signing.dumps(
            {
                "user_id": int(user_id),
                "public_url": public_url,
                "thumbnail": encoded_image,
            },
            salt=METADATA_TOKEN_SALT,
            compress=True,
        )
    # WHY: Returns only the values needed to fill and preview the still-editable plan form.
    return {
        "public_place": public_place or "",
        "public_address": public_address or "",
        "thumbnail_found": bool(image_bytes),
        "thumbnail_preview": f"data:image/jpeg;base64,{encoded_image}" if image_bytes else "",
        "metadata_token": token,
    }


# =============================================================================
# SAVED THUMBNAIL PROOF
# Checks the signed form token before returning image bytes for a saved plan.
# =============================================================================

# WHY: Keeps the thumbnail from metadata token steps in one named place so they can be understood, checked, and reused.
def thumbnail_from_metadata_token(token, user_id, public_url):
    """Return a trusted thumbnail only when token user and URL still match."""
    # WHY: Refuses missing or unexpectedly huge signed text before attempting to decode it.
    if not token or len(token) > 1_500_000:
        return None
    try:
        # WHY: Verifies the signature and short expiry before trusting any embedded image bytes.
        payload = signing.loads(
            token,
            salt=METADATA_TOKEN_SALT,
            max_age=METADATA_TOKEN_MAX_AGE_SECONDS,
        )
        # WHY: Requires both the submitting account and current form URL to match the original fetch.
        expected_url = normalise_public_https_url(public_url)
        if payload.get("user_id") != int(user_id) or payload.get("public_url") != expected_url:
            return None
        # WHY: Accepts only correctly formed encoded bytes from the verified signed value.
        image_bytes = base64.b64decode(payload.get("thumbnail", ""), validate=True)
    except (signing.BadSignature, ValueError, TypeError, AttributeError):
        return None
    # WHY: Reapplies the final image boundary even after a valid signature.
    if not image_bytes or len(image_bytes) > STORED_IMAGE_BYTES_LIMIT:
        return None

    # WHY: Gives Django a small trusted in-memory file ready for the plan's configured image storage.
    return ContentFile(image_bytes, name="plan-thumbnail.jpg")
