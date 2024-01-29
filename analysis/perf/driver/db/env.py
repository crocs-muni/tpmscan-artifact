# Source obtained from
# https://docs.sqlalchemy.org/en/20/orm/examples.html#module-examples.dogpile_caching

"""Establish data / cache file paths, and configurations,
bootstrap fixture data if necessary.

"""
from dogpile.cache.region import make_region
from hashlib import md5
from sqlalchemy.orm import Session

from .cache import ORMCache

REGIONS = {}
CACHE = None


def md5_key_mangler(key: str) -> str:
    """Receive cache keys as long concatenated strings;
    distill them into an md5 hash.

    """
    return md5(key.encode("ascii")).hexdigest()


REGIONS["default"] = make_region(
    key_mangler=md5_key_mangler
).configure(
    "dogpile.cache.dbm",
    expiration_time=3600,
    arguments={"filename": "cache/tpm.dbm"},
)


def bootstrap(session: Session) -> None:
    CACHE = ORMCache(REGIONS)
    CACHE.listen_on_session(session)
