from __future__ import annotations

import datetime
import logging as log
from contextlib import contextmanager
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import Numeric
from sqlalchemy import select
from sqlalchemy import Select
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from sqlalchemy.orm import WriteOnlyMapped
from sqlalchemy.sql.functions import percentile_cont
from sqlalchemy.sql.expression import literal_column
from sqlalchemy.sql import exists
from sqlalchemy.sql import schema
from sqlalchemy.sql import text as sqltext
from sqlalchemy.types import DateTime
from sqlalchemy.types import Float
from typing import Any
from typing import cast
from typing import Generator
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import TypeAlias
from typing import TypeVar

import numpy as np

import data
from data import Aggregator
from data import AlgorithmName
from data import HostName
from data import Measurement as RawMeasurement
from data import MeasurementFactory
from data import ResourceName
from data import TimeStamp

from .env import bootstrap
from .cache import FromCache

T = TypeVar('T')
ContextManager: TypeAlias = Generator[T, None, None]


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = 'device'

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(128))

    def __repr__(self) -> str:
        return f"Machine(id={self.id}, hostname={self.hostname})"

    measurements: WriteOnlyMapped["Measurement"] = relationship(
        back_populates="device",
        cascade="all, delete",
    )


class Algorithm(Base):
    __tablename__ = 'algorithm'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True, unique=True)

    def __repr__(self) -> str:
        return f"Algorithm(id={self.id}, name={self.name})"


class Measurement(Base):
    __tablename__ = 'measurement'

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("device.id", ondelete='cascade')
    )

    stamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, unique=True)
    platform: Mapped[Optional[str]] = mapped_column(String)
    vendor: Mapped[Optional[str]] = mapped_column(String)
    vendor_string: Mapped[Optional[str]] = mapped_column(String)
    firmware: Mapped[Optional[Decimal]] = mapped_column(Numeric(20))

    __table_args__ = (
        schema.Index('ix_measurement_source', 'source', postgresql_using='hash'),
    )

    def __repr__(self) -> str:
        return f"Measurement(id={self.id}, stamp={self.stamp} source={self.source})"

    device: Mapped["Device"] = relationship(
        back_populates="measurements",
    )

    data: WriteOnlyMapped["DataPoint"] = relationship(
        back_populates="measurement",
        cascade="all, delete",
        passive_deletes=True,
    )


class DataPoint(Base):
    __tablename__ = 'data'

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(
        ForeignKey("device.id", ondelete='cascade')
    )

    measurement_id: Mapped[int] = mapped_column(
        ForeignKey("measurement.id", ondelete='cascade')
    )

    algorithm_id: Mapped[int] = mapped_column(
        ForeignKey("algorithm.id", ondelete='cascade')
    )

    value: Mapped[float] = mapped_column(Float)

    def __repr__(self) -> str:
        return f"DataPoint(id={self.id}, algorithm={self.algorithm.name}, value={self.value})"

    device: Mapped["Device"] = relationship()

    measurement: Mapped["Measurement"] = relationship(
        back_populates="data",
    )

    algorithm: Mapped["Algorithm"] = relationship(
        passive_deletes=True,
    )


class Database:
    class Handle:
        def __init__(self, session: Session):
            self.session = session
            # Aggregator → Algorithm → MeasurementID → Value
            self.tables: dict[str, dict[str, dict[int, float]]] = {}

        def commit(self) -> None:
            self.session.commit()

        def exists(self, measurement: data.Measurement) -> bool:
            value = self.session.scalar(
                select(literal_column("true")).where(
                    exists().where(Measurement.source == measurement.source)
                )
            )

            return cast(bool, value)

        def machine(self, hostname: str) -> Device:
            device = self.session.execute(
                select(Device)
                .where(Device.hostname == hostname)
                .options(FromCache("default"))
            ).scalars().first()

            if device is None:
                device = Device(hostname=hostname)
                self.session.add(device)

            return device

        def measurement(self, device: Device, stamp: TimeStamp, source: str,
                        tpm_data: Optional[RawMeasurement.TPMData]) -> Measurement:
            measurement = self.session.execute(
                select(Measurement)
                .where(Measurement.device_id == device.id, Measurement.source == source)
            ).scalars().first()

            if not measurement:
                if tpm_data is not None:
                    measurement = Measurement(stamp=stamp, source=source,
                                              platform=tpm_data.platform,
                                              vendor=tpm_data.vendor,
                                              vendor_string=tpm_data.vendor_string,
                                              firmware=tpm_data.firmware)
                else:
                    measurement = Measurement(stamp=stamp, source=source)
                device.measurements.add(measurement)

            return measurement

        def algorithm(self, name: str) -> Algorithm:
            algorithm = self.session.execute(
                select(Algorithm)
                .where(Algorithm.name == name)
                .options(FromCache("default"))
            ).scalars().first()

            if algorithm is None:
                algorithm = Algorithm(name=name)
                self.session.add(algorithm)

            return algorithm

        def map_values(self, device: Device, measurement: Measurement, algorithm: Algorithm,
                       values: np.ndarray[Any]) -> Iterable[DataPoint]:
            return map(lambda v: DataPoint(device=device, algorithm=algorithm, value=v), values)

        def insert(self, detail: data.Measurement.Details) -> None:
            device = self.machine(detail.host_name)
            measurement = self.measurement(device, detail.stamp, detail.source,
                                           detail.tpm_data())

            datapoints: list[DataPoint] = []
            for algorithm_name in detail.list_perf():
                algorithm = self.algorithm(algorithm_name)
                values = detail.get_perf(algorithm_name)

                if values is not None:
                    datapoints.extend(self.map_values(device, measurement, algorithm, values))

            measurement.data.add_all(datapoints)

    def __init__(self, url: str):
        self.engine = create_engine(url, echo=log.getLogger().isEnabledFor(log.DEBUG))
        Base.metadata.create_all(self.engine)

    @contextmanager
    def connect(self) -> ContextManager["Database.Handle"]:
        try:
            session = Session(self.engine)
            bootstrap(session)
            yield Database.Handle(session)

        finally:
            session.close()


class DBMeasurement(data.Measurement):
    class Details(data.Measurement.Details):
        def __init__(self, handle: Database.Handle, measurement: Measurement):
            self.handle = handle
            self.entity = measurement

        @property
        def session(self) -> Session:
            return self.handle.session

        @property
        def source(self) -> str:
            return f"db#{self.entity.id}={self.entity.source}"

        @property
        def host_name(self) -> HostName:
            return self.entity.device.hostname

        @property
        def stamp(self) -> TimeStamp:
            return self.entity.stamp

        def list_perf(self) -> set[AlgorithmName]:
            textual_sql = sqltext("""
                select  algorithm.name as name
                  from  view_algorithms
                  join  algorithm
                    on  view_algorithms.algorithm_id = algorithm.id
                 where  view_algorithms.measurement_id = :id
            """)

            return set(self.session.execute(textual_sql, {"id": self.entity.id}).scalars().all())

        def get_perf(self, alg: AlgorithmName, column: str = 'duration') -> Optional[np.ndarray[Any]]:
            pass

        def tpm_data(self) -> Optional[data.Measurement.TPMData]:
            entity = self.entity

            if all([x is None for x in [entity.platform, entity.vendor, entity.vendor_string]]):
                return None

            if entity.firmware is not None:
                firmware = int(entity.firmware.to_integral_value())

            return data.Measurement.TPMData(
                entity.platform,
                entity.vendor,
                entity.vendor_string,
                firmware,
            )

        def get_aggregator(self, alg: AlgorithmName, column: str = 'duration') -> Aggregator:
            return DBAggregator(self, alg, column)

    def __init__(self, handle: Database.Handle, instance: Measurement):
        self.detail = DBMeasurement.Details(handle, instance)

    @contextmanager
    def open(self) -> ContextManager[DBMeasurement.Details]:
        yield self.detail

    @property
    def source(self) -> str:
        return self.detail.source


class DBAggregator(Aggregator):
    def __init__(self, detail: DBMeasurement.Details,
                 algorithm: AlgorithmName, column: str = 'duration'):
        self.detail = detail
        self.algorithm = algorithm
        self.column = column

    def compute(self, aggregate: str, query: Select[tuple[int, float]]) -> dict[int, float]:
        handle = self.detail.handle

        if (table := handle.tables.get(aggregate)) is not None \
                and (subtable := table.get(self.algorithm)) is not None:
            return subtable

        q0 = handle.tables.setdefault(aggregate, {})
        q1 = q0.setdefault(self.algorithm, {})
        for row in handle.session.execute(query).all():
            q1[row[0]] = row[1]

        return q1

    def median(self) -> Optional[float]:
        query: Select[tuple[int, float]] = select(
            DataPoint.measurement_id,
            percentile_cont(0.5).within_group(DataPoint.value).label('median')  # type: ignore
        ).join(Algorithm)\
            .where(Algorithm.name == self.algorithm)\
            .group_by(DataPoint.measurement_id, Algorithm.name)

        return self.compute('median', query).get(self.detail.entity.id)

    def values(self) -> Optional[list[float]]:
        query: Select[tuple[float]] = select(
            DataPoint.value
        ).join(Device).join(Algorithm)\
         .where(Algorithm.name == self.algorithm) \
         .where(DataPoint.measurement_id == self.detail.entity.id)

        return [x[0] for x in self.detail.handle.session.execute(query).all()]


class DBMeasurementFactory(MeasurementFactory):
    def __init__(self, db: Database, handle: Database.Handle):
        self.db = db
        self.handle = handle

    @property
    def session(self) -> Session:
        return self.handle.session

    def execute(self, query: str) -> Generator[data.Measurement, None, None]:
        textual_sql = sqltext(f"""
                select measurement.id, measurement.device_id

                  from measurement
                  join device
                    on measurement.device_id = device.id

                 where {query}
        """).columns(Measurement.id, Measurement.device_id)

        for measurement in self.session.execute(
                select(Measurement).from_statement(textual_sql)).scalars().all():
            yield DBMeasurement(self.handle, measurement)

    def stats(self, algorithm: str, resources: str = "@db") -> Generator[Tuple[Device, Tuple[str, float, float, int]], None, None]:
        constraints = self.resource_query(resources) or "true"
        query: Select[tuple[Device, float, float]] = select(
            DataPoint.device_id,
            func.max(Measurement.vendor).label('vendor'),
            percentile_cont(0.5).within_group(DataPoint.value).label('median'),  # type: ignore
            func.stddev(DataPoint.value).label('stddev'),
            func.count().label('count')
        ).join(Device, (Device.id == DataPoint.device_id))\
         .join(Measurement, (Measurement.id == DataPoint.measurement_id))\
         .join(Algorithm)\
         .where(Algorithm.name == algorithm)\
         .where(sqltext(constraints))\
         .group_by(DataPoint.device_id)

        for row in self.session.execute(query).yield_per(64):
            device = self.session.get(Device, row[0])
            assert device is not None
            yield device, (row[1], row[2], row[3], row[4])

    def box_stats(self, algorithm: str, resources: str = "@db") -> Generator[Tuple[Device, list[float], TimeStamp], None, None]:
        constraints = self.resource_query(resources) or "true"
        query: Select[tuple[Device, float, float, float, float, float, TimeStamp]] = select(
            DataPoint.device_id,
            func.min(DataPoint.value).label('q0'),
            percentile_cont(0.25).within_group(DataPoint.value).label('q1'),  # type: ignore
            percentile_cont(0.50).within_group(DataPoint.value).label('q2'),  # type: ignore
            percentile_cont(0.75).within_group(DataPoint.value).label('q3'),  # type: ignore
            func.max(DataPoint.value).label('q4'),
            func.date_trunc('month', Measurement.stamp).label('month')
        ).join(Device, (Device.id == DataPoint.device_id))\
         .join(Measurement, (Measurement.id == DataPoint.measurement_id))\
         .join(Algorithm)\
         .where(Algorithm.name == algorithm)\
         .where(sqltext(constraints))\
         .group_by(DataPoint.device_id, Device.hostname, 'month')\
         .order_by(Device.hostname, 'month')

        for row in self.session.execute(query).yield_per(64):
            device = self.session.get(Device, row[0])
            assert device is not None
            yield device, list(row[1:6]), row[6]

    def resource_query(self, resource: ResourceName) -> Optional[str]:
        if resource.startswith('db:'):
            return resource.removeprefix('db:')

        if resource == '@db':
            return 'true'

        return None

    def create(self, resource: ResourceName) -> Generator[data.Measurement, None, None]:
        if (filter_string := self.resource_query(resource)) is not None:
            for measurement in self.execute(filter_string):
                yield measurement

    def __repr__(self) -> str:
        return "ZipMeasurementFactory"
