from __future__ import annotations

import datetime
import logging as log
import sys

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any
from typing import Callable
from typing import cast
from typing import Generator as RawGenerator
from typing import Generic
from typing import Iterable
from typing import Optional
from typing import TextIO
from typing import TypeAlias
from typing import TypeVar
from typing import Type

import numpy as np

AlgorithmName: TypeAlias = str
FileName: TypeAlias = str
ResourceName: TypeAlias = str
HostName: TypeAlias = str
TimeStamp: TypeAlias = datetime.datetime

T = TypeVar('T')
ContextManager: TypeAlias = RawGenerator[T, None, None]
Generator: TypeAlias = RawGenerator[T, None, None]


# Measurement
# -----------

class Measurement(ABC):
    class TPMData:
        def __init__(self, platform: Optional[str], vendor: Optional[str],
                     vendor_string: Optional[str], firmware: Optional[int]):
            self._platform = platform
            self._vendor = vendor
            self._vendor_string = vendor_string
            self._firmware = firmware

        @property
        def platform(self) -> Optional[str]:
            return self._platform

        @property
        def vendor(self) -> Optional[str]:
            return self._vendor

        @property
        def vendor_string(self) -> Optional[str]:
            return self._vendor_string

        @property
        def firmware(self) -> Optional[int]:
            return self._firmware

        def firmware_str(self) -> Optional[str]:
            if (fw := self.firmware) is None:
                return None

            parts = []
            for _ in range(0, 4):
                parts.append(fw & 0xffff)
                fw = fw >> 16

            assert fw == 0

            parts.reverse()
            return ".".join([str(n) for n in parts])

    class Details(ABC):
        @property
        @abstractmethod
        def source(self) -> str:
            pass

        @property
        @abstractmethod
        def host_name(self) -> HostName:
            pass

        @property
        @abstractmethod
        def stamp(self) -> TimeStamp:
            pass

        @abstractmethod
        def list_perf(self) -> set[AlgorithmName]:
            pass

        @abstractmethod
        def get_perf(self, alg: AlgorithmName, column: str = 'duration') -> Optional[np.ndarray[Any]]:
            pass

        @abstractmethod
        def tpm_data(self) -> Optional[Measurement.TPMData]:
            pass

        def get_aggregator(self, alg: AlgorithmName, column: str = 'duration') -> Aggregator:
            return DefaultAggregator(self, alg, column)

    @abstractmethod
    @contextmanager
    def open(self) -> ContextManager[Measurement.Details]:
        pass

    @property
    @abstractmethod
    def source(self) -> str:
        pass


# MeasurementFactory
# ------------------

class MeasurementFactory(ABC):
    @abstractmethod
    def create(self, resource: ResourceName) -> Generator[Measurement]:
        pass

    def create_all(self, resources: Iterable[ResourceName]) -> Generator[Measurement]:
        for resource in resources:
            log.debug(f"Create all: Making {resource}")

            try:
                for candidate in self.create(resource):
                    yield candidate
            except NotImplementedError as error:
                log.error(error)


class FileAdapterFactory(MeasurementFactory):
    def __init__(self, real_factory: MeasurementFactory, file: TextIO = sys.stdin):
        self.real_factory = real_factory
        self.file = file

    def _read_io(self, file: TextIO) -> Generator[Measurement]:
        while (line := file.readline()) != "":
            for result in self.real_factory.create(line.rstrip()):
                yield result

    def create(self, resource: ResourceName) -> Generator[Measurement]:
        if resource == '-':
            return self._read_io(self.file)

        if resource.endswith('.txt'):
            with open(resource) as file:
                return self._read_io(file)

        return self.real_factory.create(resource)

    def __repr__(self) -> str:
        return "FileAdapterFactory"


# Workshop ≈ Many factories 😛 Pretends to be a factory itself, but actually
# hides multiple factories and tries them one by one. Thus, one can split
# complex functionality into smaller classes and join them here.
class MeasurementWorkshop(MeasurementFactory):
    def __init__(self, init: Iterable[MeasurementFactory] = ()):
        self.factories = list(init)

    def add(self, factory: MeasurementFactory) -> None:
        self.factories.append(factory)

    def get(self, cls: Type[MeasurementFactory]) -> Optional[MeasurementFactory]:
        for factory in self.factories:
            if isinstance(factory, cls):
                return factory

        return None

    def create(self, resource: ResourceName) -> Generator[Measurement]:
        counter = 0

        for factory in self.factories:
            for measurement in factory.create(resource):
                log.debug(f"Create {resource} by {factory}: {measurement}")
                counter += 1
                yield measurement

        if counter == 0:
            log.error(f"Create {resource}: No factory accepted this source")


# Aggregator
# ----------

class Aggregator(ABC):
    @abstractmethod
    def median(self) -> Optional[float]:
        pass


class AggregatorLens(Generic[T]):
    def __init__(self, method: str):
        if method not in ['median', 'values']:
            raise NotImplementedError(f"{method} is not supported")

        self.method = method

    def eval(self, aggregator: Aggregator) -> Optional[T]:
        if (symbol := getattr(aggregator, self.method, None)) is None:
            raise RuntimeError(f"{symbol} not found in {aggregator}")

        if not callable(symbol):
            raise RuntimeError(f"{symbol} on {aggregator} is not callable")

        return cast(Callable[[], Optional[T]], symbol)()


class DefaultAggregator(Aggregator):
    def __init__(self, detail: Measurement.Details, algorithm: AlgorithmName,
                 column: str = 'duration'):
        self.detail = detail
        self.algorithm = algorithm
        self.column = column

    def values(self) -> Optional[np.ndarray[Any]]:
        return self.detail.get_perf(self.algorithm, self.column)

    def median(self) -> Optional[float]:
        values = self.values()

        if values is None:
            return None

        return cast(float, np.median(values))
