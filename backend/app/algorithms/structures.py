from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
from time import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")


class BinaryMinHeap(Generic[T]):
    """Array-backed binary min-heap; push/pop are O(log n), peek is O(1)."""

    def __init__(self, key: Callable[[T], object] | None = None) -> None:
        self._items: list[T] = []
        self._key = key or (lambda value: value)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def push(self, value: T) -> None:
        self._items.append(value)
        child = len(self._items) - 1
        while child > 0:
            parent = (child - 1) // 2
            if self._key(self._items[parent]) <= self._key(self._items[child]):
                break
            self._items[parent], self._items[child] = self._items[child], self._items[parent]
            child = parent

    def peek(self) -> T:
        if not self._items:
            raise IndexError("peek from empty heap")
        return self._items[0]

    def pop(self) -> T:
        if not self._items:
            raise IndexError("pop from empty heap")
        if len(self._items) == 1:
            return self._items.pop()
        minimum = self._items[0]
        self._items[0] = self._items.pop()
        parent = 0
        size = len(self._items)
        while True:
            left = parent * 2 + 1
            right = left + 1
            smallest = parent
            if left < size and self._key(self._items[left]) < self._key(self._items[smallest]):
                smallest = left
            if right < size and self._key(self._items[right]) < self._key(self._items[smallest]):
                smallest = right
            if smallest == parent:
                break
            self._items[parent], self._items[smallest] = self._items[smallest], self._items[parent]
            parent = smallest
        return minimum


@dataclass
class PriorityEntry(Generic[T]):
    value: T
    priority: float
    enqueued_at: float
    sequence: int


class EmergencyPriorityQueue(Generic[T]):
    """Stable priority queue with bounded wait-time boost to prevent starvation."""

    def __init__(self, starvation_interval_seconds: float = 300.0, max_wait_boost: float = 5.0) -> None:
        if starvation_interval_seconds <= 0 or max_wait_boost < 0:
            raise ValueError("Invalid starvation-prevention configuration")
        self._interval = starvation_interval_seconds
        self._max_boost = max_wait_boost
        self._entries: list[tuple[float, int, PriorityEntry[T]]] = []
        self._sequence = 0

    def __len__(self) -> int:
        return len(self._entries)

    def push(self, value: T, priority: float, enqueued_at: float | None = None) -> None:
        entry = PriorityEntry(value, float(priority), enqueued_at if enqueued_at is not None else time(), self._sequence)
        self._sequence += 1
        heappush(self._entries, (-entry.priority, entry.sequence, entry))

    def _rebuild(self, now: float) -> None:
        self._entries = []
        for entry in getattr(self, "_all_entries", []):
            boost = min(max(now - entry.enqueued_at, 0) / self._interval, self._max_boost)
            self._entries.append((-(entry.priority + boost), entry.sequence, entry))
        heapify(self._entries)

    def pop(self, now: float | None = None) -> T:
        if not self._entries:
            raise IndexError("pop from empty emergency queue")
        timestamp = now if now is not None else time()
        entries = [item[2] for item in self._entries]
        self._all_entries = entries
        self._rebuild(timestamp)
        entry = heappop(self._entries)[2]
        self._all_entries = [item[2] for item in self._entries]
        return entry.value

    def peek(self, now: float | None = None) -> T:
        if not self._entries:
            raise IndexError("peek from empty emergency queue")
        timestamp = now if now is not None else time()
        self._all_entries = [item[2] for item in self._entries]
        self._rebuild(timestamp)
        return self._entries[0][2].value


class Trie:
    """Prefix index; insert/search/prefix checks are O(m) for key length m."""

    _terminal = "\0"

    def __init__(self) -> None:
        self._root: dict[str, dict] = {}

    def insert(self, word: str) -> None:
        if not word:
            raise ValueError("Trie keys cannot be empty")
        node = self._root
        for character in word.casefold():
            node = node.setdefault(character, {})
        node[self._terminal] = {}

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and self._terminal in node

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def _walk(self, value: str) -> dict | None:
        node = self._root
        for character in value.casefold():
            child = node.get(character)
            if child is None:
                return None
            node = child
        return node


class DisjointSetUnion:
    """Union-find with path compression and union by rank; amortized O(alpha(n))."""

    def __init__(self, values: list[K] | None = None) -> None:
        self.parent: dict[K, K] = {}
        self.rank: dict[K, int] = {}
        for value in values or []:
            self.add(value)

    def add(self, value: K) -> None:
        if value not in self.parent:
            self.parent[value] = value
            self.rank[value] = 0

    def find(self, value: K) -> K:
        if value not in self.parent:
            raise KeyError(value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, first: K, second: K) -> bool:
        self.add(first)
        self.add(second)
        root_first, root_second = self.find(first), self.find(second)
        if root_first == root_second:
            return False
        if self.rank[root_first] < self.rank[root_second]:
            root_first, root_second = root_second, root_first
        self.parent[root_second] = root_first
        if self.rank[root_first] == self.rank[root_second]:
            self.rank[root_first] += 1
        return True


class SegmentTree:
    """Range-sum segment tree; build O(n), point update/range sum O(log n)."""

    def __init__(self, values: list[int | float]) -> None:
        self.length = len(values)
        self.size = 1
        while self.size < self.length:
            self.size <<= 1
        self.tree: list[float] = [0.0] * (2 * self.size)
        for index, value in enumerate(values):
            self.tree[self.size + index] = float(value)
        for index in range(self.size - 1, 0, -1):
            self.tree[index] = self.tree[index * 2] + self.tree[index * 2 + 1]

    def update(self, index: int, value: int | float) -> None:
        if not 0 <= index < self.length:
            raise IndexError(index)
        cursor = self.size + index
        self.tree[cursor] = float(value)
        cursor //= 2
        while cursor:
            self.tree[cursor] = self.tree[cursor * 2] + self.tree[cursor * 2 + 1]
            cursor //= 2

    def query(self, left: int, right: int) -> float:
        if not 0 <= left <= right < self.length:
            raise IndexError((left, right))
        start, end = left + self.size, right + self.size
        result = 0.0
        while start <= end:
            if start % 2:
                result += self.tree[start]
                start += 1
            if not end % 2:
                result += self.tree[end]
                end -= 1
            start //= 2
            end //= 2
        return result


class FenwickTree:
    """Fenwick prefix-sum tree; updates and prefix queries are O(log n)."""

    def __init__(self, values: list[int | float]) -> None:
        self.length = len(values)
        self.tree = [0.0] * (self.length + 1)
        for index, value in enumerate(values):
            self.add(index, float(value))

    def add(self, index: int, delta: int | float) -> None:
        if not 0 <= index < self.length:
            raise IndexError(index)
        cursor = index + 1
        while cursor <= self.length:
            self.tree[cursor] += float(delta)
            cursor += cursor & -cursor

    def prefix_sum(self, end: int) -> float:
        if not -1 <= end < self.length:
            raise IndexError(end)
        total = 0.0
        cursor = end + 1
        while cursor:
            total += self.tree[cursor]
            cursor -= cursor & -cursor
        return total

    def range_sum(self, left: int, right: int) -> float:
        if not 0 <= left <= right < self.length:
            raise IndexError((left, right))
        return self.prefix_sum(right) - self.prefix_sum(left - 1)


class LRUCache(Generic[K, T]):
    """Least-recently-used cache; get/put are O(1) average using OrderedDict."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self._items: OrderedDict[K, T] = OrderedDict()

    def get(self, key: K) -> T | None:
        if key not in self._items:
            return None
        self._items.move_to_end(key)
        return self._items[key]

    def put(self, key: K, value: T) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
