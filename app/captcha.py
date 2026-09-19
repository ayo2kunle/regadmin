import hashlib
import hmac
import io
import random
import secrets
import time

from flask import current_app, session
from PIL import Image, ImageDraw, ImageFont

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 5
TTL_SECONDS = 10 * 60


def issue_captcha() -> str:
    """Start a new challenge and return its id. The answer is never stored."""
    captcha_id = secrets.token_urlsafe(18)
    session["captcha_id"] = captcha_id
    session["captcha_issued"] = int(time.time())
    return captcha_id


def clear_captcha() -> None:
    session.pop("captcha_id", None)
    session.pop("captcha_issued", None)


def current_code() -> str | None:
    captcha_id = session.get("captcha_id")
    issued = session.get("captcha_issued")
    if not captcha_id or issued is None:
        return None
    try:
        age = time.time() - int(issued)
    except (TypeError, ValueError):
        return None
    if age < 0 or age > TTL_SECONDS:
        return None
    return _code_for(str(captcha_id))


def captcha_matches(submitted: str) -> bool:
    expected = current_code()
    if expected is None:
        return False
    given = "".join((submitted or "").split()).upper()
    return hmac.compare_digest(_digest(given), _digest(expected))


def render_captcha(code: str) -> bytes:
    width, height = 220, 76
    image = Image.new("RGB", (width, height), (255, 250, 243))
    draw = ImageDraw.Draw(image)
    rng = random.SystemRandom()
    for _ in range(7):
        draw.line(
            [
                (rng.randint(0, width), rng.randint(0, height)),
                (rng.randint(0, width), rng.randint(0, height)),
            ],
            fill=(rng.randint(170, 214), rng.randint(150, 196), rng.randint(130, 176)),
            width=rng.choice((1, 2)),
        )

    font = ImageFont.load_default(size=40)
    for index, character in enumerate(code):
        glyph = Image.new("RGBA", (48, 56), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((4, 2), character, font=font, fill=(15, 61, 46, 255))
        glyph = glyph.rotate(rng.randint(-22, 22), expand=True, resample=Image.Resampling.BICUBIC)
        x = 8 + index * 40
        y = rng.randint(2, 12)
        image.paste(glyph, (x, y), glyph)

    for _ in range(35):
        draw.point(
            (rng.randint(0, width - 1), rng.randint(0, height - 1)),
            fill=(196, 107, 44),
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _code_for(captcha_id: str) -> str:
    secret = current_app.config["SECRET_KEY"]
    if isinstance(secret, str):
        secret = secret.encode()
    digest = hmac.new(secret, f"regadmin-captcha:{captcha_id}".encode(), hashlib.sha256).digest()
    return "".join(ALPHABET[byte % len(ALPHABET)] for byte in digest[:CODE_LENGTH])


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()
