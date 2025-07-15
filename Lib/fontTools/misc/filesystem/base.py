from __future__ import annotations
import typing
from abc import ABC, abstractmethod

from .copy import copy_dir, copy_file
from .walk import BoundWalker
from .errors import (
    DestinationExists,
    DirectoryExpected,
    FileExpected,
    FilesystemClosed,
    NoSysPath,
    ResourceNotFound,
)
from .path import dirname

if typing.TYPE_CHECKING:
    from typing import Any, IO, Iterator, Collection, Self, Type
    from .subfs import SubFS
    from .info import Info


class FS(ABC):
    """Abstract base class for custom filesystems."""

    _closed: bool = False

    @abstractmethod
    def open(self, path: str, mode: str = "rb", **kwargs) -> IO[Any]: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...

    @abstractmethod
    def isdir(self, path: str) -> bool: ...

    @abstractmethod
    def isfile(self, path: str) -> bool: ...

    @abstractmethod
    def listdir(self, path: str) -> list[str]: ...

    @abstractmethod
    def makedir(self, path: str, recreate: bool = False) -> SubFS: ...

    @abstractmethod
    def makedirs(self, path: str, recreate: bool = False) -> SubFS: ...

    @abstractmethod
    def getinfo(self, path: str, namespaces: Collection[str] | None = None) -> Info: ...

    @abstractmethod
    def remove(self, path: str) -> None: ...

    @abstractmethod
    def removedir(self, path: str) -> None: ...

    @abstractmethod
    def removetree(self, path: str) -> None: ...

    @abstractmethod
    def movedir(self, src: str, dst: str, create: bool = False) -> None: ...

    def getsyspath(self, path: str) -> str:
        raise NoSysPath(f"the filesystem {self!r} has no system path")

    def close(self):
        self._closed = True

    def isclosed(self) -> bool:
        return self._closed

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False  # never swallow exceptions

    def check(self):
        if self._closed:
            raise FilesystemClosed(f"the filesystem {self!r} is closed")

    def opendir(self, path: str, *, factory: Type[SubFS] | None = None) -> SubFS:
        """Return a sub‑filesystem rooted at `path`."""
        if factory is None:
            from .subfs import SubFS

            factory = SubFS
        return factory(self, path)

    def scandir(
        self, path: str, namespaces: Collection[str] | None = None
    ) -> Iterator[Info]:
        return (self.getinfo(f"{path}/{p}", namespaces) for p in self.listdir(path))

    @property
    def walk(self) -> BoundWalker:
        return BoundWalker(self)

    def readbytes(self, path: str) -> bytes:
        with self.open(path, "rb") as f:
            return f.read()

    def writebytes(self, path: str, data: bytes):
        with self.open(path, "wb") as f:
            f.write(data)

    def create(self, path: str, wipe: bool = False):
        if not wipe and self.exists(path):
            return False
        with self.open(path, "wb"):
            pass  # 'touch' empty file
        return True

    def copy(self, src_path: str, dst_path: str, overwrite=False):
        if not self.exists(src_path):
            raise ResourceNotFound(f"{src_path!r} does not exist")
        elif not self.isfile(src_path):
            raise FileExpected(f"path {src_path!r} should be a file")
        if not overwrite and self.exists(dst_path):
            raise DestinationExists(f"destination {dst_path!r} already exists")
        if not self.isdir(dirname(dst_path)):
            raise DirectoryExpected(f"path {dirname(dst_path)!r} should be a directory")
        copy_file(self, src_path, self, dst_path)

    def copydir(self, src_path: str, dst_path: str, create=False):
        if not create and not self.exists(dst_path):
            raise ResourceNotFound(f"{dst_path!r} does not exist")
        if not self.isdir(src_path):
            raise DirectoryExpected(f"path {src_path!r} should be a directory")
        copy_dir(self, src_path, self, dst_path)
