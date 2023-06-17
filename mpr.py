#!/usr/bin/python3
'''
This is a command line tool to wrap the MicroPython mpremote tool and
provide a more conventional command line interface. Multiple arguments
can be specified for commands and inbuilt usage help is provided for all
commands.
'''
import json
import os
import re
import shlex
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

DEVICE_NAMES = '''
Devices can be specified via -d/--device using any of the following
names/mnemonics:

auto - connect automatically to first available device. This is the
       default if nothing is specified.

a0, a1, a2, a3, .. an - connect to /dev/ttyACMn
u0, u1, u2, u3, .. un - connect to /dev/ttyUSBn
c0, c1, c2, c3, .. cn - connect to COMn

id:<serial> - connect to the device with USB serial number <serial>
              (the second entry in the output from the list command)

port:<path> - connect to the device with the given path

You can also use any valid device name/path.
'''.strip()

try:
    import argcomplete
except ModuleNotFoundError:
    completion = False
else:
    completion = True

MIPURL = 'https://micropython.org/pi/v2/index.json'

PROG = Path(__file__).stem
CNFFILE = Path(os.getenv('XDG_CONFIG_HOME', '~/.config'), f'{PROG}.conf')
DIRS = Path.cwd().parts[1:]
MAXDIRS = len(DIRS)
options = {}
aliases_all = {}
cnffile = None

DEVICE_SHORTCUTS = {
    'a': '/dev/ttyACM',
    'u': '/dev/ttyUSB',
    'c': 'COM',
}

# We use our own function to convert device shortcuts rather than rely
# on mpremote native shortcuts because (oddly) mpremote only implements
# the first 4 devices.
def get_device(device: str) -> str:
    'Intercept device name shortcuts'
    devpath = DEVICE_SHORTCUTS.get(device[0])
    num = device[1:]
    return (devpath + num) if devpath and num.isdigit() else device

infer_path_count = 0

def infer_path(path: str, *, dest: bool = False) -> str:
    'Infer leading directory path'
    global infer_path_count

    def dirlist(count):
        return '' if count == 0 else '/' + '/'.join(DIRS[(MAXDIRS - count):])

    slashcount = len(path) - len(path.lstrip('/'))

    if slashcount == 0:
        if dest:
            return path

        parent = dirlist(infer_path_count)
        return f'{parent}/{path}' if parent else path

    # Limit leading slashes to max dirs we can infer
    diff = slashcount - MAXDIRS - 1
    if diff > 0:
        path = path[diff:]
        slashcount -= diff

    dircount = slashcount - 1

    if slashcount != len(path):
        return dirlist(dircount) + path[dircount:]

    if dest:
        return dirlist(dircount) or '/'

    infer_path_count = dircount
    return ''

def doexit(args: Namespace, code_or_msg: int = 0) -> None:
    'Exit but check if final hard/soft reset is required'
    if args.reset:
        reset_val = args.reset
        args.reset = None
        mpcmd(args, 'soft-reset' if reset_val == 1 else 'reset')

    sys.exit(code_or_msg)

mpcmd_cmdtext = None

def mpcmd(args: Namespace, cmdstr: str, quiet: bool = False) -> str:
    'Send mpremote cmdstr to device'
    global mpcmd_cmdtext
    # Only build main command text the first time
    if mpcmd_cmdtext is None:
        arglist = [args.path_to_mpremote]
        if args.device:
            # Intercept device name shortcuts
            device = get_device(args.device)
            arglist.append(f'connect {device}')

        if args.mount_unsafe_links:
            arglist.append(f'mount -l {args.mount_unsafe_links}')
        elif args.mount:
            arglist.append(f'mount {args.mount}')

        mpcmd_cmdtext = ' '.join(arglist)

    cmd = f'{mpcmd_cmdtext} {cmdstr}'

    if args.verbose:
        print(cmd)

    out = subprocess.DEVNULL if quiet else None
    res = subprocess.run(cmd, stderr=out, stdout=out,
                         universal_newlines=True, shell=True)
    if res.returncode != 0:
        doexit(args, res.returncode)
    return res.stdout

def mpcmd_wrap(args: Namespace) -> None:
    'Extract args/options and send to device'
    cmdname = aliases_all[args.cmdname]
    opts = options[cmdname]
    arglist = [cmdname]
    for opt in opts._actions:
        arg = args.__dict__.get(opt.dest)
        if arg is None:
            continue
        if opt.const:
            if arg == opt.default:
                continue
            arg = None

        if opt.option_strings:
            arglist.append(opt.option_strings[-1])

        if arg is not None:
            arglist.append(' '.join(arg) if isinstance(arg, list) else arg)

    mpcmd(args, ' '.join(arglist))

def mip_list(args: Namespace) -> None:
    'Fetch and print MIP package list'
    try:
        url = urlopen(args.mip_list_url)
    except Exception as e:
        sys.exit(f'Fetch to {MIPURL} error: {e}')

    data = json.load(url).get('packages', {})

    def max_len(field: str) -> int:
        return max(len(p.get(field, '')) for p in data)

    name_w = max_len('name')
    version_w = max_len('version')

    for p in data:
        p = SimpleNamespace(**p)
        add = f'{p.version:{version_w}} {p.description}' \
                if p.description else p.version
        print(f'{p.name:{name_w}} {add}')

def set_mp_prog(progstr: str, args: Namespace) -> None:
    'Work out location of mpremote program'
    prog = Path(progstr).absolute()
    if not args.path_to_mpremote:
        path = prog.with_name('mpremote')
        args.path_to_mpremote = str(path) if path.is_file() else path.name
    else:
        path = prog.parent / Path(args.path_to_mpremote).expanduser()
        if not path.is_file():
            sys.exit(f'Error: no mpremote program at {path}')
        args.path_to_mpremote = str(path)

class COMMAND:
    'Base class for all commands'
    commands = []

    @classmethod
    def run(cls, args: Namespace) -> None:
        'Base runner, called if not overridden by parent'
        mpcmd(args, aliases_all[args.cmdname])

    @classmethod
    def add(cls, parent) -> None:
        'Append parent command to internal list'
        cls.commands.append(parent)

def main() -> None:
    'Main code'
    global cnffile

    # Parse arguments
    opt = ArgumentParser(description=__doc__,
            epilog=f'Type "{PROG} <command> -h" to see specific help/usage '
            ' for any of the above commands. Note you can set default '
            f'options in {CNFFILE} (e.g. for --path-to-mpremote '
            ' or --mip-list-url). '
            f'Use "{PROG} config" to conveniently change the file.')

    # Set up main/global arguments
    opt.add_argument('-d', '--device',
            help='serial port/device to connect to, default is "auto". '
                 'Specify "-d list" to print out device mnemonics that '
                 'can be used.')
    opt.add_argument('-m', '--mount',
            help='mount local directory on device before command')
    opt.add_argument('-M', '--mount-unsafe-links',
            help='mount local directory and allow external links')
    opt.add_argument('-x', '--reset', dest='reset',
            action='store_const', const=1,
            help='do soft reset after command')
    opt.add_argument('-b', '--reboot', dest='reset',
            action='store_const', const=2,
            help='do hard reboot after command')
    opt.add_argument('-p', '--path-to-mpremote',
            help='path to mpremote program. Assumes same directory as this '
                     'program, or then just "mpremote"')
    opt.add_argument('--mip-list-url', default=MIPURL,
            help='mip list url for packages, default="%(default)s"')
    opt.add_argument('-c', '--completion', action='store_true',
            help='output shell TAB completion code')
    opt.add_argument('-v', '--verbose', action='store_true',
            help='print executed commands (for debug)')
    opt.add_argument('-V', '--version', action='store_true',
            help=f'show {PROG} version')
    cmd = opt.add_subparsers(title='Commands', dest='cmdname')

    # Add each command ..
    for cls in COMMAND.commands:
        name = cls.__name__[1:]

        if hasattr(cls, 'doc'):
            desc = cls.doc.strip()
        elif cls.__doc__:
            desc = cls.__doc__.strip()
        else:
            sys.exit(f'Must define a docstring for command class "{name}".')

        title = desc.splitlines()[0]
        if title[-1] != '.':
            sys.exit(f'Title "{title}" should include full stop.')

        # Code check to ensure we have not defined duplicate aliases
        aliases = cls.aliases if hasattr(cls, 'aliases') else []
        for a in aliases + [name]:
            if a in aliases_all:
                sys.exit(f'command {name}: duplicate alias: {a}')
            aliases_all[a] = name

        options[name] = cmdopt = cmd.add_parser(name, description=desc,
                                help=title, aliases=aliases)

        # Set up this commands own arguments, if it has any
        if hasattr(cls, 'init'):
            cls.init(cmdopt)

        # Set the function to call
        cmdopt.set_defaults(func=cls.run)

    if completion:
        argcomplete.autocomplete(opt)

    # Merge in default args from user config file. Then parse the
    # command line.
    cnffile = CNFFILE.expanduser()
    if cnffile.is_file():
        with cnffile.open() as fp:
            lines = [re.sub(r'#.*$', '', line).strip() for line in fp]
        cnflines = ' '.join(lines).strip()
    else:
        cnflines = ''

    args = opt.parse_args(shlex.split(cnflines) + sys.argv[1:])

    if args.version:
        try:
            from importlib.metadata import version
        except ImportError:
            from importlib_metadata import version

        try:
            ver = version(PROG)
        except Exception:
            ver = 'unknown'

        print(ver)
        return

    if args.completion:
        if not completion:
            sys.exit('You must "pip install argcomplete" to '
                    'use shell TAB completion.')

        subprocess.run(f'register-python-argcomplete {PROG}'.split())
        return

    # Just print out device names if asked
    if args.device == 'list':
        print(DEVICE_NAMES)
        return

    if 'func' not in args:
        opt.print_help()
        return

    # Set up path to mpremote program
    set_mp_prog(opt.prog, args)

    # Run required command
    args.func(args)
    doexit(args)

@COMMAND.add
class _get(COMMAND):
    'Copy one or more files from device to local directory.'
    aliases = ['g']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('src', nargs='+',
                help='name of source file[s] on device')
        opt.add_argument('dst',
                help='name of local destination dir on PC, or "-" for stdout')

    @classmethod
    def run(cls, args: Namespace) -> None:
        if args.dst == '-':
            # Output to stdout
            dst = None
        else:
            dst = Path(args.dst)
            # Ensure target dir exists
            parent = dst.parent if args.file else dst
            parent.mkdir(exist_ok=True, parents=True)

        for src in args.src:
            src = infer_path(src)
            if src:
                if dst:
                    filedst = dst if args.file else dst / Path(src).name
                    mpcmd(args, f'cp :{src} {filedst}')
                else:
                    mpcmd(args, f'cat {src}')

@COMMAND.add
class _put(COMMAND):
    'Copy one or more local files to directory on device.'
    aliases = ['p']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('-r', '--recursive', action='store_true',
                help='copy local directory recursively to / on device')
        opt.add_argument('src', nargs='+',
                help='name of local source file[s] on PC')
        opt.add_argument('dst',
                help='name of destination dir on device')

    @classmethod
    def run(cls, args: Namespace) -> None:
        dst = Path(infer_path(args.dst, dest=True))

        for src in args.src:
            src = Path(src)

            if not src.exists():
                sys.exit(f'"{src}" does not exist.')

            filedst = str(dst if args.file else dst / src.name)
            arg = 'cp'

            if args.recursive:
                if not src.is_dir() or filedst != '/':
                    sys.exit('mpremote requires source must be directory '
                            'and target must be "/"')
                arg += ' -r'
            elif src.is_dir():
                sys.exit(f'Can not copy directory "{src}."')

            mpcmd(args, f'{arg} {src} :{filedst}')

@COMMAND.add
class _copy(COMMAND):
    'Copy one of more remote files to a directory on device.'
    aliases = ['c']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('src', nargs='+',
                help='name of source file[s] on device')
        opt.add_argument('dst',
                help='name of destination dir on device')

    @classmethod
    def run(cls, args: Namespace) -> None:
        dst = Path(infer_path(args.dst), dest=True)

        for src in args.src:
            src = infer_path(src)
            if src:
                filedst = str(dst if args.file else dst / Path(src).name)
                mpcmd(args, f'cp :{src} :{filedst}')

@COMMAND.add
class _ls(COMMAND):
    'List directory on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('dir', nargs='?', default='/',
                help='name of dir (default: %(default)s)')

    @classmethod
    def run(cls, args: Namespace) -> None:
        path = infer_path(args.dir, dest=True)
        if path:
            mpcmd(args, f'ls {path}')

@COMMAND.add
class _mkdir(COMMAND):
    'Create the given directory[s] on device.'
    aliases = ['mkd']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('dir', nargs='+', help='name of dir[s]')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for path in args.dir:
            path = infer_path(path, dest=True)
            if path:
                mpcmd(args, f'mkdir {path}', args.quiet)

@COMMAND.add
class _rmdir(COMMAND):
    'Remove the given directory[s] on device.'
    aliases = ['rmd']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('dir', nargs='+', help='name of dir[s]')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for path in args.dir:
            path = infer_path(path, dest=True)
            if path:
                mpcmd(args, f'rmdir {path}', args.quiet)

@COMMAND.add
class _rm(COMMAND):
    'Remove the given file[s] on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('file', nargs='+', help='name of file[s]')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for path in args.file:
            path = infer_path(path)
            if path:
                mpcmd(args, f'rm {path}', args.quiet)

@COMMAND.add
class _touch(COMMAND):
    'Touch the given file[s] on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('file', nargs='+', help='name of file[s]')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for path in args.file:
            path = infer_path(path)
            if path:
                mpcmd(args, f'touch {path}')

@COMMAND.add
class _edit(COMMAND):
    '''
    Edit the given file[s] on device.

    Copies the file from device, opens your editor on that local file,
    then copies it back.
    '''
    aliases = ['e']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('file', nargs='+', help='name of file[s]')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for path in args.file:
            path = infer_path(path)
            if path:
                mpcmd(args, f'edit {path}')

@COMMAND.add
class _reset(COMMAND):
    'Soft reset the device.'
    aliases = ['x']

    @classmethod
    def run(cls, args: Namespace) -> None:
        args.reset = None
        mpcmd(args, 'soft-reset')

@COMMAND.add
class _reboot(COMMAND):
    'Hard reboot the device.'
    aliases = ['b']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('delay_ms', type=int, nargs='?',
                help='optional delay before reboot (millisecs)')

    @classmethod
    def run(cls, args: Namespace) -> None:
        args.reset = None
        arg = f' {args.delay_ms}' if args.delay_ms else ''
        mpcmd(args, 'reset' + arg)

@COMMAND.add
class _repl(COMMAND):
    'Enter REPL on device.'
    aliases = ['r']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-e', '--escape-non-printable', action='store_true',
                help='print non-printable bytes/chars as hex codes')
        opt.add_argument('-c', '--capture',
                help='capture output of the REPL session to given file')
        opt.add_argument('-x', '--inject-code',
                help='characters to inject at the REPL when Ctrl-J is pressed')
        opt.add_argument('-i', '--inject-file',
                help='file to inject at the REPL when Ctrl-K is pressed')

    @classmethod
    def run(cls, args: Namespace) -> None:
        mpcmd_wrap(args)

@COMMAND.add
class _list(COMMAND):
    'List currently connected devices.'
    aliases = ['l', 'devs']

    @classmethod
    def run(cls, args: Namespace) -> None:
        mpcmd(args, 'devs')

@COMMAND.add
class _run(COMMAND):
    'Run the given local scripts on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('script', nargs='+',
                help='script to run')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for script in args.script:
            mpcmd(args, f'run "{script}"')

@COMMAND.add
class _eval(COMMAND):
    'Evaluate and print the given strings on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('string', nargs='+',
                help='string to evaluate')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for string in args.string:
            mpcmd(args, f'eval "{string}"')

@COMMAND.add
class _exec(COMMAND):
    'Execute the given strings on device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('string', nargs='+',
                help='string to execute')

    @classmethod
    def run(cls, args: Namespace) -> None:
        for string in args.string:
            mpcmd(args, f'exec "{string}"')

@COMMAND.add
class _mip(COMMAND):
    'Run mip to install packages on device.'
    aliases = ['m']

    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-n', '--no-mpy', action='store_true',
                help='download .py files, not compiled .mpy files')
        opt.add_argument('-t', '--target',
                help='destination directory on device')
        opt.add_argument('-i', '--index',
                help='package index to use, default="micropython-lib"')
        opt.add_argument('command',
                help='mip command: "install" or "list"')
        opt.add_argument('package', nargs='*',
                help='package specifications, e.g. "name", "name@version", '
                         '"github.org/repo", "github.org/repo@branch"')

    @classmethod
    def run(cls, args: Namespace) -> None:
        if args.command == 'list':
            mip_list(args)
        else:
            if not args.package:
                sys.exit('Must specify package.')
            mpcmd_wrap(args)

@COMMAND.add
class _bootloader(COMMAND):
    'Enter bootloader on device.'

@COMMAND.add
class _df(COMMAND):
    'Show flash usage on device.'

@COMMAND.add
class _rtc(COMMAND):
    'Get/set the Real Time Clock (RTC) time from/to device.'
    @classmethod
    def init(cls, opt: ArgumentParser) -> None:
        opt.add_argument('-s', '--set', action='store_true',
                         help='set the RTC to the current PC time, '
                         'default is to get the time')

    @classmethod
    def run(cls, args: Namespace) -> None:
        mpcmd_wrap(args)

@COMMAND.add
class _version(COMMAND):
    'Show mpremote version.'

@COMMAND.add
class _config(COMMAND):
    doc = f'Open the {PROG} configuration file with your editor.'
    aliases = ['cf']

    @classmethod
    def run(cls, args: Namespace) -> None:
        editor = os.getenv('VISUAL') or os.getenv('EDITOR') or 'vi'
        subprocess.run(f'{editor} {cnffile}'.split())

if __name__ == '__main__':
    main()
