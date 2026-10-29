"""Bounded metadata-only observations; never returns file contents."""
import hashlib
import os
import stat
from contextlib import ExitStack,contextmanager
from pathlib import Path,PurePosixPath


MAX_BYTES=1024*1024


def linked(path):
    return path.is_symlink() or (hasattr(path,"is_junction") and path.is_junction())


@contextmanager
def regular_file(root,parts):
    with ExitStack() as stack:
        if os.open in os.supports_dir_fd and hasattr(os,"O_NOFOLLOW"):
            directory_flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
            directory=os.open(root,directory_flags);stack.callback(os.close,directory)
            for part in parts[:-1]:
                directory=os.open(part,directory_flags,dir_fd=directory);stack.callback(os.close,directory)
            metadata=os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):raise ValueError("not_regular")
            descriptor=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|getattr(os,"O_NONBLOCK",0),dir_fd=directory)
        else:
            path=root
            for part in parts:
                path=path/part
                if linked(path):raise ValueError("symlink")
            if not path.resolve().is_relative_to(root.resolve()):raise ValueError("outside_root")
            if not stat.S_ISREG(path.stat().st_mode):raise ValueError("not_regular")
            descriptor=os.open(path,os.O_RDONLY|getattr(os,"O_BINARY",0))
        stream=stack.enter_context(os.fdopen(descriptor,"rb"))
        yield stream


def signature(metadata):
    return (metadata.st_dev,metadata.st_ino,metadata.st_size,metadata.st_mtime_ns,metadata.st_ctime_ns)


def observe_file(root,relative):
    root=Path(root)
    path=PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(part in {"..","."} for part in path.parts) or "\\" in relative:
        return {"status":"unreadable","reason":"outside_root","sha256":None}
    try:
        if linked(root) or not root.is_dir():
            return {"status":"unreadable","reason":"root_unavailable","sha256":None}
        with regular_file(root,path.parts) as stream:
            before=os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):raise ValueError("not_regular")
            if before.st_size>MAX_BYTES:raise ValueError("too_large")
            digest=hashlib.sha256();size=0
            while chunk:=stream.read(65536):
                size+=len(chunk)
                if size>MAX_BYTES:raise ValueError("too_large")
                digest.update(chunk)
            after=os.fstat(stream.fileno())
            if signature(before)!=signature(after) or size!=after.st_size:
                raise ValueError("changed_during_read")
            return {"status":"readable","reason":None,"sha256":digest.hexdigest()}
    except FileNotFoundError:
        return {"status":"missing","reason":"missing","sha256":None}
    except ValueError as error:
        return {"status":"unreadable","reason":str(error),"sha256":None}
    except OSError:
        return {"status":"unreadable","reason":"permission_or_io","sha256":None}
