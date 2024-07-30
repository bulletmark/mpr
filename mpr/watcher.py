#!/usr/bin/env python3
'''
Implement monitoring for file changes.
'''
# Author: Mark Blakeney, Oct 2023.
from __future__ import annotations

import time
from pathlib import Path

class _IWatcher:
    'Implementation to monitor file changes using inotify'
    def __init__(self):
        try:
            from inotify_simple import INotify  # type: ignore
            from inotify_simple import flags as F  # type: ignore
        except ImportError:
            self.watcher = None
            return

        # inotify_simple flags to watch on source files
        self.watch_flags = F.ATTRIB | F.CREATE | F.DELETE | F.DELETE_SELF \
                | F.MODIFY | F.MOVED_FROM | F.MOVED_TO | F.MOVE_SELF | F.UNMOUNT

        self.watcher = INotify()
        self.watchers = []

    def wait(self, watching: list[Path]) -> None:
        'Add watch for all files we need to monitor and then wait'
        self.watchers = [self.watcher.add_watch(str(p), self.watch_flags) for
                         p in watching]

        # Will block here until any file we are watching changes
        self.watcher.read()

    def clear(self) -> None:
        'Clear all watches'
        for wd in self.watchers:
            try:
                self.watcher.rm_watch(wd)
            except Exception:
                pass

        # Discard any pending events
        self.watcher.read(0)

class _Watcher:
    'Fallback implementation to monitor file changes using simple polling'
    def wait(self, watching: list[Path]) -> None:
        'Record mtime for files we need to monitor and then wait for changes'
        files = {f: f.stat().st_mtime for f in watching}

        while True:
            time.sleep(1)
            for file in files:
                try:
                    mtime = file.stat().st_mtime
                except FileNotFoundError:
                    return

                if mtime != files[file]:
                    return

    def clear(self) -> None:
        # Not needed for polling implementation
        pass

def create():
    watcher = _IWatcher()
    return watcher if watcher.watcher else _Watcher()
