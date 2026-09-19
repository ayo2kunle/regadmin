import secrets

# No 0/O or 1/I, so a code is easier to read if someone types it.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def new_code(length: int = CODE_LENGTH) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if any(character.isalpha() for character in code) and any(character.isdigit() for character in code):
            return code


def assign_public_id(record) -> str:
    """Set a unique public code on a model that has public_id. Returns the code."""
    if record.public_id:
        return record.public_id
    model = type(record)
    for _ in range(30):
        code = new_code()
        taken = model.query.filter_by(public_id=code).first()
        if taken is None:
            record.public_id = code
            return code
    raise RuntimeError("Could not allocate a public id")
