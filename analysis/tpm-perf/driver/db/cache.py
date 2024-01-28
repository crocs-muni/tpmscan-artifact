# Source obtained from
# https://docs.sqlalchemy.org/en/20/orm/examples.html#module-examples.dogpile_caching

from __future__ import annotations

"""Represent functions and classes
which allow the usage of Dogpile caching with SQLAlchemy.
Introduces a query option called FromCache.

.. versionchanged:: 1.4  the caching approach has been altered to work
   based on a session event.


The three new concepts introduced here are:

 * ORMCache - an extension for an ORM :class:`.Session`
   retrieves results in/from dogpile.cache.
 * FromCache - a query option that establishes caching
   parameters on a Query
 * RelationshipCache - a variant of FromCache which is specific
   to a query invoked during a lazy load.

The rest of what's here are standard SQLAlchemy and
dogpile.cache constructs.

"""
from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion

from sqlalchemy import event
from sqlalchemy.engine import FrozenResult
from sqlalchemy.orm import loading
from sqlalchemy.orm import ORMExecuteState
from sqlalchemy.orm import Query
from sqlalchemy.orm import QueryableAttribute
from sqlalchemy.orm import Session
from sqlalchemy.orm.interfaces import UserDefinedOption
from sqlalchemy.sql.expression import Executable

from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence


class ORMCache:
    """
    An add-on for an ORM :class:`.Session` optionally loads full results
    from a dogpile cache region.
    """

    def __init__(self, regions: dict[str, CacheRegion]):
        self.cache_regions = regions
        self._statement_cache: dict[int, int] = {}

    def listen_on_session(self, session: Session) -> Any:
        event.listen(session, "do_orm_execute", self._do_orm_execute)

    def _do_orm_execute(self, orm_context: ORMExecuteState) -> Optional[Any]:
        for opt in orm_context.user_defined_options:
            if isinstance(opt, RelationshipCache):
                opt = opt._process_orm_context(orm_context)  # type: ignore
                if opt is None:
                    continue

            if isinstance(opt, FromCache):
                dogpile_region = self.cache_regions[opt.region]

                our_cache_key = opt._generate_cache_key(
                    orm_context.statement, orm_context.parameters or {}, self
                )

                if opt.ignore_expiration:
                    cached_value = dogpile_region.get(  # type: ignore
                        our_cache_key,
                        expiration_time=opt.expiration_time,
                        ignore_expiration=opt.ignore_expiration,
                    )
                else:

                    def createfunc() -> FrozenResult[Any]:
                        return orm_context.invoke_statement().freeze()

                    cached_value = dogpile_region.get_or_create(
                        our_cache_key,
                        createfunc,
                        expiration_time=opt.expiration_time,
                    )

                if cached_value is NO_VALUE:
                    # keyerror?   this is bigger than a keyerror...
                    raise KeyError()

                orm_result = loading.merge_frozen_result(  # type: ignore
                    orm_context.session,
                    orm_context.statement,
                    cached_value,
                    load=False,
                )
                return orm_result()

        else:
            return None

    def invalidate(self, statement: Executable,
                   parameters: Sequence[Mapping[str, Any]] | Mapping[str, Any],
                   opt: Any) -> None:
        """Invalidate the cache value represented by a statement."""

        if isinstance(statement, Query):
            statement = statement.__clause_element__()

        dogpile_region = self.cache_regions[opt.region]
        cache_key = opt._generate_cache_key(statement, parameters, self)
        dogpile_region.delete(cache_key)


class FromCache(UserDefinedOption):
    """Specifies that a Query should load results from a cache."""

    propagate_to_loaders = False

    def __init__(
        self,
        region: str = "default",
        cache_key: Optional[str] = None,
        expiration_time: Optional[int] = None,
        ignore_expiration: Optional[bool] = False,
    ):
        """Construct a new FromCache.

        :param region: the cache region.  Should be a
         region configured in the dictionary of dogpile
         regions.

        :param cache_key: optional.  A string cache key
         that will serve as the key to the query.   Use this
         if your query has a huge amount of parameters (such
         as when using in_()) which correspond more simply to
         some other identifier.

        """
        self.region = region
        self.cache_key = cache_key
        self.expiration_time = expiration_time
        self.ignore_expiration = ignore_expiration

    # this is not needed as of SQLAlchemy 1.4.28;
    # UserDefinedOption classes no longer participate in the SQL
    # compilation cache key
    def _gen_cache_key(self, anon_map: Any, bindparams: Any) -> Any:
        return None

    def _generate_cache_key(self, statement: Executable,
                            parameters: Sequence[Mapping[str, Any]] | Mapping[str, Any],
                            orm_cache: ORMCache) -> Any:
        """generate a cache key with which to key the results of a statement.

        This leverages the use of the SQL compilation cache key which is
        repurposed as a SQL results key.

        """
        statement_cache_key = statement._generate_cache_key()  # type: ignore

        key = statement_cache_key.to_offline_string(
            orm_cache._statement_cache, statement, parameters
        ) + repr(self.cache_key)
        # print("here's our key...%s" % key)
        return key


class RelationshipCache(FromCache):
    """Specifies that a Query as called within a "lazy load"
    should load results from a cache."""

    propagate_to_loaders = True

    def __init__(
        self,
        attribute: QueryableAttribute[Any],
        region: str = "default",
        cache_key: Any = None,
        expiration_time: Optional[int] = None,
        ignore_expiration: bool = False,
    ):
        """Construct a new RelationshipCache.

        :param attribute: A Class.attribute which
         indicates a particular class relationship() whose
         lazy loader should be pulled from the cache.

        :param region: name of the cache region.

        :param cache_key: optional.  A string cache key
         that will serve as the key to the query, bypassing
         the usual means of forming a key from the Query itself.

        """
        self.region = region
        self.cache_key = cache_key
        self.expiration_time = expiration_time
        self.ignore_expiration = ignore_expiration
        self._relationship_options = {
            (attribute.property.parent.class_, attribute.property.key): self
        }

    def _process_orm_context(self, orm_context: ORMExecuteState) -> Optional[RelationshipCache]:
        current_path = orm_context.loader_strategy_path

        if not current_path:
            return None

        mapper, prop = current_path[-2:]
        key = prop.key  # type: ignore

        for cls in mapper.class_.__mro__:  # type: ignore
            if (cls, key) in self._relationship_options:
                relationship_option = self._relationship_options[
                    (cls, key)
                ]
                return relationship_option

        return None

    def and_(self, option: Any) -> RelationshipCache:
        """Chain another RelationshipCache option to this one.

        While many RelationshipCache objects can be specified on a single
        Query separately, chaining them together allows for a more efficient
        lookup during load.

        """
        self._relationship_options.update(option._relationship_options)
        return self
