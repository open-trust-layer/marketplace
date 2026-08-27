"""Deeply immutable prepared federation host values and integrity snapshots.

This module contains no semantic authority and no network capability. It turns
the bounded M8 host representation used by a prepared exchange into detached
``dict``/``list``-compatible values whose authoritative state is stored only in
private immutable tuples, together with an immutable type-tagged integrity
snapshot.
"""
from __future__ import annotations

from collections.abc import Mapping
from itertools import islice
from typing import Any, Final

MAX_PREPARED_SNAPSHOT_DEPTH: Final = 8
MAX_PREPARED_SNAPSHOT_ITEMS: Final = 512


class PreparedExchangeIntegrityError(ValueError):
    """Fail-closed local prepared-exchange integrity error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise PreparedExchangeIntegrityError(code, message)


class FrozenList(list):
    """List-compatible immutable host value backed by one private tuple.

    The inherited ``list`` storage is deliberately left empty. Even an explicit
    call such as ``list.append(frozen, value)`` can only alter ignored base-class
    storage; iteration, indexing, length, equality, representation, and OLP
    encoding all read the immutable tuple instead.
    """

    __slots__ = ("_values",)

    def __init__(self, values: Any = ()) -> None:
        list.__init__(self)
        object.__setattr__(self, "_values", tuple(values))

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError("prepared federation host values are immutable")

    def __delattr__(self, name: str) -> None:
        raise TypeError("prepared federation host values are immutable")

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, key: Any) -> Any:
        return self._values[key]

    def __contains__(self, value: object) -> bool:
        return value in self._values

    def __reversed__(self):
        return reversed(self._values)

    def count(self, value: object) -> int:
        return self._values.count(value)

    def index(self, value: object, *args: int) -> int:
        return self._values.index(value, *args)

    def copy(self) -> list[Any]:
        return list(self._values)

    def __repr__(self) -> str:
        return repr(list(self._values))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (list, tuple)):
            return self._values == tuple(other)
        return NotImplemented

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("prepared federation host values are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable


class FrozenDict(dict):
    """Dict-compatible immutable host value backed by private tuple pairs.

    The inherited ``dict`` storage is deliberately left empty. Explicit base
    calls such as ``dict.__setitem__(frozen, key, value)`` can only modify ignored
    base storage; all Mapping behavior used by Marketplace/OLP reads ``_items``.
    """

    __slots__ = ("_items",)

    def __init__(self, values: Mapping[str, Any] | None = None) -> None:
        dict.__init__(self)
        source = {} if values is None else values
        object.__setattr__(self, "_items", tuple(source.items()))

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError("prepared federation host values are immutable")

    def __delattr__(self, name: str) -> None:
        raise TypeError("prepared federation host values are immutable")

    def __iter__(self):
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: Any) -> Any:
        for existing_key, value in self._items:
            if existing_key == key:
                return value
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return any(existing_key == key for existing_key, _ in self._items)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self._items)

    def items(self) -> tuple[tuple[str, Any], ...]:
        return self._items

    def values(self) -> tuple[Any, ...]:
        return tuple(value for _, value in self._items)

    def copy(self) -> dict[str, Any]:
        return {key: value for key, value in self._items}

    def __repr__(self) -> str:
        return repr(self.copy())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            try:
                return self.copy() == dict(other)
            except Exception:
                return False
        return NotImplemented

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("prepared federation host values are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def _detach(value: Any, *, depth: int = 0) -> tuple[Any, tuple[Any, ...]]:
    if depth > MAX_PREPARED_SNAPSHOT_DEPTH:
        _fail("SNAPSHOT_DEPTH_EXCEEDED", "prepared exchange exceeds the integrity snapshot depth bound")

    value_type = type(value)
    if value is None:
        return None, ("none",)
    if value_type is bool:
        return value, ("bool", value)
    if value_type is int:
        return value, ("int", value)
    if value_type is str:
        return value, ("str", value)
    if value_type is bytes:
        return value, ("bytes", value)

    if value_type is tuple:
        if len(value) > MAX_PREPARED_SNAPSHOT_ITEMS:
            _fail("SNAPSHOT_ITEM_LIMIT", "prepared exchange tuple exceeds the integrity snapshot item bound")
        detached_items: list[Any] = []
        snapshots: list[tuple[Any, ...]] = []
        for item in value:
            detached, snapshot = _detach(item, depth=depth + 1)
            detached_items.append(detached)
            snapshots.append(snapshot)
        return tuple(detached_items), ("tuple", tuple(snapshots))

    if isinstance(value, list):
        if value_type not in (list, FrozenList):
            _fail("SNAPSHOT_UNSUPPORTED_TYPE", f"unsupported prepared exchange list type {value_type.__name__}")
        if len(value) > MAX_PREPARED_SNAPSHOT_ITEMS:
            _fail("SNAPSHOT_ITEM_LIMIT", "prepared exchange list exceeds the integrity snapshot item bound")
        detached_items = []
        snapshots = []
        for item in value:
            detached, snapshot = _detach(item, depth=depth + 1)
            detached_items.append(detached)
            snapshots.append(snapshot)
        return FrozenList(detached_items), ("list", tuple(snapshots))

    if isinstance(value, Mapping):
        if value_type not in (dict, FrozenDict):
            _fail("SNAPSHOT_UNSUPPORTED_TYPE", f"unsupported prepared exchange mapping type {value_type.__name__}")
        try:
            items = tuple(islice(value.items(), MAX_PREPARED_SNAPSHOT_ITEMS + 1))
        except Exception as exc:
            _fail("SNAPSHOT_MAPPING_FAILED", f"prepared exchange mapping snapshot failed: {type(exc).__name__}")
        if len(items) > MAX_PREPARED_SNAPSHOT_ITEMS:
            _fail("SNAPSHOT_ITEM_LIMIT", "prepared exchange mapping exceeds the integrity snapshot item bound")

        detached_map: dict[str, Any] = {}
        snapshot_items: list[tuple[str, tuple[Any, ...]]] = []
        for key, item in items:
            if type(key) is not str or not key:
                _fail("SNAPSHOT_INVALID_KEY", "prepared exchange mappings MUST use non-empty exact text keys")
            if key in detached_map:
                _fail("SNAPSHOT_DUPLICATE_KEY", "prepared exchange mapping repeated a key during snapshot")
            detached, snapshot = _detach(item, depth=depth + 1)
            detached_map[key] = detached
            snapshot_items.append((key, snapshot))
        snapshot_items.sort(key=lambda pair: pair[0].encode("utf-8"))
        return FrozenDict(detached_map), ("map", tuple(snapshot_items))

    _fail("SNAPSHOT_UNSUPPORTED_TYPE", f"unsupported prepared exchange host value type {value_type.__name__}")


def detach_host_value(value: Any) -> Any:
    """Return one bounded deeply detached host value with immutable authoritative state."""
    detached, _ = _detach(value)
    return detached


def host_value_integrity_snapshot(value: Any) -> tuple[Any, ...]:
    """Return the bounded type-tagged snapshot of one supported host value."""
    _, snapshot = _detach(value)
    return snapshot


def _binding_snapshot(binding: Any) -> tuple[Any, ...]:
    required = (
        "source",
        "operation",
        "scope_fingerprint",
        "required_capabilities",
        "page_size",
        "expected_result_message_type",
    )
    if any(not hasattr(binding, name) for name in required):
        _fail("INVALID_BINDING", "prepared exchange binding is missing required fields")

    source = binding.source
    operation = binding.operation
    scope_fingerprint = binding.scope_fingerprint
    capabilities = binding.required_capabilities
    page_size = binding.page_size
    expected_result = binding.expected_result_message_type

    if any(type(value) is not str or not value for value in (source, operation, scope_fingerprint, expected_result)):
        _fail("INVALID_BINDING", "prepared exchange binding text fields MUST be non-empty exact strings")
    if type(capabilities) is not tuple or not capabilities or not all(type(item) is str and item for item in capabilities):
        _fail("INVALID_BINDING", "prepared exchange binding capabilities MUST be a non-empty exact tuple of text")
    if type(page_size) is not int or page_size < 1:
        _fail("INVALID_BINDING", "prepared exchange binding page_size MUST be a positive exact integer")

    return (
        "federation-request-binding-v1",
        source,
        operation,
        scope_fingerprint,
        tuple(capabilities),
        page_size,
        expected_result,
    )


def detach_prepared_exchange(binding: Any, envelope: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Return a deeply immutable detached envelope plus its integrity snapshot."""
    detached, envelope_snapshot = _detach(envelope)
    if type(detached) is not tuple or len(detached) != 4:
        _fail("INVALID_ENVELOPE", "prepared exchange envelope MUST be an exact four-element tuple")
    marker, version, message_type, payload = detached
    if marker != "OLP-TRANSPORT":
        _fail("INVALID_ENVELOPE", "prepared exchange envelope marker is invalid")
    if type(version) is not int or version != 1:
        _fail("INVALID_ENVELOPE", "prepared exchange envelope version MUST be exact integer 1")
    if type(message_type) is not str or not message_type:
        _fail("INVALID_ENVELOPE", "prepared exchange request message type MUST be non-empty exact text")
    if not isinstance(payload, Mapping):
        _fail("INVALID_ENVELOPE", "prepared exchange request payload MUST be a mapping")

    integrity = (
        "prepared-federation-exchange-integrity-v1",
        _binding_snapshot(binding),
        envelope_snapshot,
    )
    return detached, integrity


def prepared_exchange_integrity_snapshot(binding: Any, envelope: Any) -> tuple[Any, ...]:
    """Return only the immutable integrity snapshot for one prepared exchange."""
    _, integrity = detach_prepared_exchange(binding, envelope)
    return integrity
