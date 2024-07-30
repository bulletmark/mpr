#!/usr/bin/env python3
'''
See description in mpr.py.
'''
# Author: Mark Blakeney, Oct 2023.
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from platformdirs import user_config_path

PROG = Path(sys.argv[0]).stem + '-' + Path(__file__).stem
FLAGSFILE = f'{PROG}.conf'
CACHE = Path(f'.{PROG}.cache')
CNFDIRS = ('.', str(user_config_path()))
options: ArgumentParser = ArgumentParser()

def set_prog(option: str | None, name: str) -> str:
    'Work out location of specified program'
    prog = Path(sys.argv[0]).absolute()
    if option:
        path = prog.parent / Path(option).expanduser()
        if not path.is_file():
            sys.exit(f'{name} {path} does not exist.')
        return str(path)

    path = prog.with_name(name)
    return str(path) if path.is_file() else name

def get_depth(path: Path, want_depth: int) -> int:
    'Get depth or -1 if depth is beyond what we want'
    depth = len(path.parts)
    return depth if (want_depth <= 1 or depth <= want_depth) else -1

def get_map(maps: list[str], prog: str) -> str | None:
    'Get any remapped name for specified program'
    lookup = {}
    for pair in maps:
        try:
            src, tgt = pair.split(':')
        except ValueError:
            sys.exit(f'Invalid map "{pair}", must be "src:tgt".')

        pathsrc = Path(src)
        pathtgt = Path(tgt)
        for path in pathsrc, pathtgt:
            if len(path.parts) > 1:
                sys.exit(f'map {pair}: {path} must be a single file name.')

        lookup[pathsrc.stem] = pathtgt.stem

    return lookup.get(prog)

def start(prog: Path | None, remap_prog: str | None,
          modname: str | None, cmdline: str, excludes: set,
          watching: set, args: Namespace) -> subprocess.Popen | None:
    '''
    Compile changed files to mpy files, copy them to remove device,
    and then start the program
    '''
    watching.clear()
    for path in Path('.').rglob('*.py'):
        # Ignore this path if it is excluded, or below an excluded dir
        if path in excludes or \
                any(str(path).startswith(str(p) + os.sep) for p in excludes):
            continue

        # Ignore this path if beyond dir depth we want
        depth = get_depth(path, args.depth)
        if depth <= 0:
            continue

        # Ignore this path if we only want to monitor the main prog
        if prog and args.only and path != prog:
            continue

        # Keep record of all files we need to watch
        watching.add(path)

        # Substitute target name if needed for main prog
        tgt = path.with_suffix('.mpy')
        if prog and path == prog:
            if remap_prog:
                tgt = path.with_name(remap_prog).with_suffix('.mpy')

        # Compile those files that have changed and copy changed
        # bytecode files to remote device
        mpy = CACHE / tgt
        if not mpy.exists() or mpy.stat().st_mtime <= path.stat().st_mtime:
            mpy.parent.mkdir(exist_ok=True, parents=True)
            print(f'>> {path} compiling to {tgt} ..')
            res = subprocess.run(f'{args.mpy_cross} {path} -o {mpy}'.split())
            if res.returncode == 0 and not args.compile_only:
                dest = ':' if depth <= 1 else f':{path.parent}/'
                cmd = f'{args.mpremote} cp --no-verbose {mpy} {dest}'
                subprocess.run(cmd.split())

    if not prog:
        return None

    # Sanity check that we did find the main prog
    if prog not in watching:
        sys.exit(f'{prog} not found.')

    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    argstr = ' ' + ' '.join(args.args) if args.args else ''
    if not args.once:
        print(f'>> {now} starting {prog} as {modname}.mpy{argstr}')

    if args.once:
        subprocess.run(cmdline, shell=True)
        return None

    return subprocess.Popen(cmdline, shell=True)

def run(prog: Path | None, args: Namespace) -> None:
    'Run the monitor'
    from . import watcher
    watch = watcher.create()

    # Create a set of excluded paths from what is given on command line
    excludes: set[Path] = set(Path(p) for p in args.exclude)

    cmdline = f'exec {args.mpremote} exec "'

    if prog:
        remap_prog = get_map(args.map, prog.stem)
        modname = remap_prog if remap_prog else prog.stem

        if args.args:
            cmdline += f'import sys; sys.argv.extend([\'{prog.stem}\'] + '\
                    f'{args.args}); '

        cmdline += f'import {modname}"'

        # If user specified a program then remove it from the excludes
        excludes.discard(prog)
    else:
        remap_prog = None
        modname = None

    watching: set[Path] = set()

    # Start monitoring (potentially forever)
    while True:
        # Start program and then monitor for file changes
        child = start(prog, remap_prog, modname, cmdline, excludes,
                      watching, args)
        if not child:
            break

        # Watch all files we need to monitor
        watch.wait(watching)

        # kill the running process and remove all watches
        child.kill()
        watch.clear()
        print()
        time.sleep(1)

def init(opt: ArgumentParser) -> None:
    'Main code'
    global options
    # Process command line options
    opt.add_argument('-f', '--flush', action='store_true',
            help='flush cache and force update of all .mpy files at start')
    opt.add_argument('-D', '--depth', type=int, default=0,
            help='directory depth limit, 1 = current directory only')
    opt.add_argument('-o', '--only', action='store_true',
            help='only monitor the specified program file, not the whole '
            'directory/tree')
    opt.add_argument('-C', '--compile-only', action='store_true',
            help='just compile new .mpy files, don\'t copy to device or '
                 'run any program')
    opt.add_argument('-e', '--exclude', action='append',
                     default=['main.py', 'boot.py'],
            help='exclude specified directory or file from monitoring. '
                 'Can specify this option multiple times. If you exclude '
                 'a directory then all files/dirs below it are also excluded. '
                 'Default excludes are "main.py" and "boot.py". '
                 'Any specified runnable "prog" file is removed from the '
                 'excludes list.')
    opt.add_argument('--map', action='append', default=[],
            help='map specified source name to different target name when '
                 'run as main prog, e.g. "main:main1" to map '
                 'main.py -> main1.mpy on target and "main1" will be run. '
                 'Can specify this option multiple times, e.g. may want '
                 'to map main.py and boot.py permanently for when you run '
                 'either as prog.')
    opt.add_argument('-1', '--once', action='store_true',
            help='run once only')
    opt.add_argument('-X', '--path-to-mpy-cross',
            help='path to mpy-cross program. Assumes same directory as this '
                 'program, or then just "mpy-cross"')
    opt.add_argument('prog', nargs='?',
            help='name of .py module to run, e.g. "main.py". If not specified '
                 'then new .mpy files are merely compiled and copied to the '
                 'device.')
    opt.add_argument('args', nargs='*',
            help='optional arguments to pass in sys.argv to started '
                 'program. Separate with -- if switch options are passed')
    options = opt

def main(args: Namespace) -> None:
    # Merge in default args from user config file.
    for cdir in CNFDIRS:
        cnffile = Path(cdir) / FLAGSFILE
        if cnffile.is_file():
            with cnffile.open() as fp:
                lines = [re.sub(r'#.*$', '', line).strip() for line in fp]
            cnflines = ' '.join(lines).strip()
            args_dict_file = vars(options.parse_args(shlex.split(cnflines)))
            args_dict = vars(args)
            for attr in 'map', 'exclude':
                args_dict[attr] = set(args_dict[attr] + args_dict_file[attr])

            args_dict_file.update(args_dict)
            args = Namespace(**args_dict)
            break

    if args.prog and not args.compile_only:
        prog = Path(args.prog).with_suffix('.py')
        if len(prog.parts) > 1:
            sys.exit(f'{args.prog} must be Python file in top level dir.')

        if not prog.is_file():
            sys.exit(f'{prog} does not exist or is not a file.')
    else:
        prog = None

    args.mpy_cross = set_prog(args.path_to_mpy_cross, 'mpy-cross')

    # If specified, tack explicit device on to mpremote command
    args.mpremote = args.path_to_mpremote
    if args.device:
        ext = args.device if len(args.device) <= 2 else f'connect {args.device}'
        args.mpremote += f' {ext}'

    # Flush cache if requested
    if args.flush and CACHE.exists():
        shutil.rmtree(CACHE)

    CACHE.mkdir(exist_ok=True, parents=True)

    # Write a .gitignore file so git ignores this cache dir
    ignore = CACHE / '.gitignore'
    if not ignore.is_file():
        ignore.write_text(f'# Automatically created by {PROG}\n*\n')

    try:
        run(prog, args)
    except KeyboardInterrupt:
        pass
