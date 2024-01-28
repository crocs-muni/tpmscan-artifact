from __future__ import annotations

# import csv
import datetime
import io
import logging as log
import os
import re
import yaml
import zipfile

from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import Any
from typing import cast
from typing import Generator
from typing import Optional
from typing import TypeAlias
from typing import TypeVar

import numpy as np
import numpy.typing as npt

from data import AlgorithmName
from data import FileName
from data import HostName
from data import Measurement
from data import MeasurementFactory
from data import ResourceName
from data import TimeStamp

T = TypeVar('T')
ContextManager: TypeAlias = Generator[T, None, None]


class ZipMeasurement(Measurement):
    PERF_RE = re.compile(r'detail/(Perf_.*)\.csv')
    HOST_RE = re.compile(r'out-(.*)-[0-9]+-[0-9]+')

    @dataclass
    class Property:
        raw: int
        value: str

    def __init__(self, file_name: FileName):
        self._file_name = file_name

    @property
    def source(self) -> FileName:
        return os.path.basename(self._file_name)

    # Civilised ZIP files ‹NAME.zip› usually contain a single root directory
    # with name ‹NAME›. However, sometimes this directory is ommited. This
    # method determines the root directory with contents.
    def _get_root(self, zf: zipfile.ZipFile) -> zipfile.Path:
        root = zipfile.Path(zf)
        entries = list(root.iterdir())

        if len(entries) != 1 or not entries[0].is_dir():
            return root

        pattern = r"(^|/)" + entries[0].stem + r"\.zip$"
        return entries[0] if re.search(pattern, self.source) else root

    @contextmanager
    def open(self) -> ContextManager[ZipMeasurement.Details]:
        try:
            handle = zipfile.ZipFile(self._file_name, 'r')
        except Exception:
            raise RuntimeError(f"Bad file: {self._file_name}")

        try:
            root = self._get_root(handle)
            yield ZipMeasurement.Details(self._file_name, handle, root)
        finally:
            handle.close()

    class Details(Measurement.Details):
        def __init__(self, file_name: FileName, handle: zipfile.ZipFile,
                     root: zipfile.Path):
            self._file_name = file_name
            self._handle = handle
            self._root = root

        def _parse_yaml_brute_force(self, file: FileName, handle: io.TextIOWrapper) -> dict[str, str]:
            yaml = {}
            while (line := handle.readline()) != "":
                parts = line.rstrip('\n').split(': ', maxsplit=1)

                if len(parts) != 2:
                    continue

                yaml[parts[0].strip(" \t\"'")] = parts[1].strip(" \"'")

            return yaml

        def _parse_yaml_clean(self, file: FileName, handle: io.TextIOWrapper) -> dict[str, Any]:
            return cast(dict[str, Any], yaml.load(handle.read(), Loader=yaml.Loader))

        def _parse_yaml(self, file: FileName, handle: io.TextIOWrapper) -> dict[str, Any]:
            try:
                return self._parse_yaml_clean(file, handle)
            except yaml.YAMLError:
                log.warning(f"{self._file_name}: {file} is not valid YAML, trying brute force parse")
                handle.seek(0)
                return self._parse_yaml_brute_force(file, handle)

        @property
        def source(self) -> FileName:
            return os.path.basename(self._file_name)

        @cache
        def get_system_info(self) -> Optional[list[str]]:
            uname_path = self._root.joinpath('detail/uname_system_info.txt')

            if not uname_path.exists():
                return None

            with uname_path.open() as info:
                # The following assert persuades Mypy that ‹readline()› returns
                # a string instead of bytes.
                assert isinstance(info, io.TextIOWrapper)
                return info.readline().split(' ')

        def _get_host_from_results(self) -> Optional[str]:
            file_path = self._root.joinpath('results.yaml')

            if not file_path.exists():
                return None

            with file_path.open() as handle:
                assert isinstance(handle, io.TextIOWrapper)
                # Do not bother with true YAML parser here, it mostly fails
                # and just makes things slower.
                results = self._parse_yaml_brute_force(file_path, handle)

                if 'Manufacturer' in results \
                        and 'Vendor string' in results \
                        and 'Device name' in results:
                    return "-".join([results['Manufacturer'],
                                    results['Vendor string'],
                                    results['Device name']
                                     ]).replace(' ', '-').lower()

            return None

        def _parse_properties(self, file_name: FileName, handle:
                              io.TextIOWrapper) -> dict[str, ZipMeasurement.Property]:
            data = {}

            header_re = re.compile(r"^(\S+):$")
            header = None

            while (line := handle.readline()) != "":
                line = line.rstrip('\n')

                if (match := header_re.search(line)):
                    header = match[1]
                    data[header] = ZipMeasurement.Property(0, "")
                    continue

                parts = line.split(': ', maxsplit=1)

                if len(parts) != 2:
                    continue

                key = parts[0].strip(" \t\"'")
                value = parts[1].strip(" \t\"'")

                if header is None:
                    log.error(f"{self._file_name}: {key} found before any header")
                    raise RuntimeError(f"{self._file_name}: {key} found before any header")

                if key == "value" and value != "":
                    data[header].value = value
                if key == "raw":
                    data[header].raw = int(value, 16)

            return data

        def _get_vendor_string(self, parts: list[int]) -> str:
            data = []

            for part in parts:
                chunk = []

                while part > 0:
                    chunk.append(chr(part & 0xff))
                    part = part >> 8

                chunk.reverse()
                data.extend(chunk)

            while data != [] and data[-1] == '\0':
                data.pop()

            if all([c.isprintable() for c in data]):
                return "".join(data)

            return "".join([f"{ord(c):02x}" for c in data])

        def _get_host_from_detail(self) -> Optional[str]:
            # lambda x: x is not None does not work for some reason, stupid mypy
            def _filter(s: Optional[str]) -> bool:
                return s is not None

            tpm_data = self.tpm_data()

            if tpm_data is None:
                return None

            parts = [tpm_data.platform, tpm_data.vendor, tpm_data.vendor_string]
            return "-".join(filter(_filter, parts)).replace(' ', '-').lower()  # type: ignore

        @property
        def host_name(self) -> HostName:
            if (m := ZipMeasurement.HOST_RE.search(self._file_name)) is not None:
                return m.group(1)

            if (r := self._get_host_from_results()) is not None:
                return r

            if (p := self._get_host_from_detail()) is not None:
                return p

            if (s := self.get_system_info()) is not None:
                if 'algtest' not in s[1]:
                    return s[1]

            raise RuntimeError(f"{self._file_name}: Cannot determine hostname")

        def _strptime_results(self, s: str) -> TimeStamp:
            return datetime.datetime.strptime(s, '%Y/%m/%d %H:%M:%S')

        @cache
        def _date_parse_from_results(self, file: FileName) -> Optional[TimeStamp]:
            file_name = self._root.joinpath(file)

            if not file_name.exists():
                return None

            with file_name.open() as file_raw:
                assert isinstance(file_raw, io.TextIOWrapper)

                results = self._parse_yaml(file_name, file_raw)

                if 'Execution date/time' not in results:
                    return None

                return self._strptime_results(results['Execution date/time'])

        def _date_parse_brute_force(self, file: FileName,
                                    handle: io.TextIOWrapper) -> Optional[TimeStamp]:
            yaml = self._parse_yaml_brute_force(file, handle)
            if 'Execution date/time' in yaml:
                return self._strptime_results(yaml['Execution date/time'])

            return None

        def _date_parse_from_filename(self) -> Optional[TimeStamp]:
            parts = self._file_name.split('-')
            try:
                return datetime.datetime.strptime(' '.join(parts[2:4]), '%y%m%d %H%M%S.zip')
            except Exception:
                return None

        def _date_get_from_member(self) -> Optional[TimeStamp]:
            for member in self._handle.infolist():
                if not member.is_dir():
                    d = member.date_time
                    return datetime.datetime(d[0], d[1], d[2], d[3], d[4], d[5])

            return None

        @property
        def stamp(self) -> TimeStamp:
            stamp = self._date_parse_from_results('results.yaml') \
                or self._date_parse_from_filename() \
                or self._date_get_from_member()

            if stamp is None:
                raise RuntimeError(f"{self._file_name}: Cannot determine time stamp")

            return stamp

        def _get_perf_name(self, entry_name: FileName) -> Optional[AlgorithmName]:
            if (match := ZipMeasurement.PERF_RE.search(entry_name)) is None:
                return None

            return match.group(1)

        def list_perf(self) -> set[AlgorithmName]:
            perfs = set()

            for entry in self._handle.infolist():
                if (perf := self._get_perf_name(entry.filename)) is not None:
                    perfs.add(perf)

            return perfs

        def _parse_perf(self, alg: AlgorithmName, perf: io.TextIOWrapper,
                        column: str) -> Optional[npt.ArrayLike]:
            fields = perf.readline().rstrip().split(',')

            if 'duration' not in fields or 'return_code' not in fields:
                log.debug(f'{self._file_name}: {alg}: Required fields missing, skipping')
                return None

            indices = [fields.index(name) for name in ['duration', 'return_code']]

            dtype = np.dtype([("value", float), ("label", "U12")])

            perf.seek(0, os.SEEK_SET)
            datapoints = np.array([
                    x[0] for x in np.loadtxt(perf, dtype=dtype, delimiter=',',
                                             usecols=indices, skiprows=1, ndmin=1)
                    if int(x[1], 16) == 0
            ])

            if len(datapoints) == 0:
                log.debug(f'{self._file_name}: {alg}: No data points, skipping')
                return None

            return datapoints

        def get_perf(self, alg: AlgorithmName, column: str = 'duration') -> Optional[np.ndarray[Any]]:
            path = self._root.joinpath(f'detail/{alg}.csv')

            if not path.exists():
                log.debug(f'{self._file_name}: {alg} not found, skipping')
                return None

            with path.open() as perf:
                assert isinstance(perf, io.TextIOWrapper)
                return self._parse_perf(alg, perf, column)

        def _tpm_data_props(self) -> Optional[dict[str, Any]]:
            files_to_check = map(lambda p: self._root.joinpath(p), [
                'detail/Quicktest_properties-fixed.txt',
                'detail/Capability_properties-fixed.txt',
            ])

            properties_path = next((p for p in files_to_check if p.exists()), None)

            if properties_path is None or not properties_path.exists():
                return None

            with properties_path.open() as properties:
                assert isinstance(properties, io.TextIOWrapper)
                props = self._parse_properties(properties_path, properties)

                if 'TPM2_PT_MANUFACTURER' not in props:
                    return None

                vendor_string = self._get_vendor_string(
                    [props[f"TPM2_PT_VENDOR_STRING_{n}"].raw for n in range(1, 5)]
                )

                fw = None
                if all([f"TPM2_PT_FIRMWARE_VERSION_{n}" in props for n in [1, 2]]):
                    fw = (props['TPM2_PT_FIRMWARE_VERSION_1'].raw << 32) \
                        | props['TPM2_PT_FIRMWARE_VERSION_2'].raw

                return {
                    "manufacturer": props['TPM2_PT_MANUFACTURER'].value,
                    "vendor_string": vendor_string,
                    "firmware": fw
                }

        def _tpm_data_dmi(self) -> Optional[str]:
            dmidecode_path = self._root.joinpath('detail/dmidecode_system_info.txt')
            if not dmidecode_path.exists():
                return None

            with dmidecode_path.open() as dmidecode:
                assert isinstance(dmidecode, io.TextIOWrapper)
                dmidata = self._parse_yaml(dmidecode_path, dmidecode)
                return dmidata.get('Product Name') if dmidata is not None else None

        @cache
        def tpm_data(self) -> Optional[Measurement.TPMData]:
            mf, vendor, fw = None, None, None

            if (props := self._tpm_data_props()) is not None:
                mf, vendor, fw = props['manufacturer'], props['vendor_string'], props['firmware']

            platform = self._tpm_data_dmi()

            if all([x is None for x in [mf, vendor, platform]]):
                return None

            return Measurement.TPMData(platform, mf, vendor, fw)


class ZipMeasurementFactory(MeasurementFactory):
    @staticmethod
    def create(resource: ResourceName) -> Generator[Measurement, None, None]:
        if resource.endswith('.zip') and os.path.isfile(resource):
            yield ZipMeasurement(resource)

    def __repr__(self) -> str:
        return "ZipMeasurementFactory"
