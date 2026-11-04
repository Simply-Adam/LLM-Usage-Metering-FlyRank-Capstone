import hashlib


def hash_api_key(api_key):
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()