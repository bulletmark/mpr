#!/usr/bin/python3
'''
This is a command line tool to wrap the MicroPython mpremote tool and
provide a more conventional command line interface. Multiple arguments
can be specified for commands and inbuilt usage help is provided for all
commands.
'''
import os
import sys
import argparse
import shlex
import subprocess
import re
from pathlib import Path

DEVICE_NAMES = '''
Devices can be specified via -d/--device using any of the following
names/mnemonics:

auto - connect automatically to first available device. This is the
       default if nothing is specified.

a0, a1, a2, a3 - connect to /dev/ttyACM?
u0, u1, u2, u3 - connect to /dev/ttyUSB?
c0, c1, c2, c3 - connect to COM?

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

PROG = Path(__file__).stem
CNFFILE = Path(os.getenv('XDG_CONFIG_HOME', '~/.config'), f'{PROG}.conf')
CWD = Path.cwd()
commands = []
options = {}
aliases_all = set()
cnffile = None

def get_editor():
    'Return editor for this user'
    return os.getenv('VISUAL') or os.getenv('EDITOR') or 'vi'

def infer_root(path, *, dest=False):
    'Infer leading directory path'
    def _parse(path, dest):
        base = path.lstrip('/')
        count = len(path) - len(base)

        if not dest and not base:
            if count == 1:
                infer_root.lead = '/'
            elif count > 1:
                infer_root.lead = '/' + '/'.join(CWD.parts[(1 - count):]) + '/'

            return None

        if count <= 1:
            return infer_root.lead + path

        end = path[count:]
        if end:
            end = '/' + end

        return path[0] + '/'.join(CWD.parts[(1 - count):]) + end

    return [_parse(p, dest) for p in path] \
            if isinstance(path, list) else _parse(path, dest)

infer_root.lead = ''

def infer_path(path):
    'Get inferred path'
    ipath = infer_root(path)
    return None if ipath is None else Path(ipath)

def doexit(args, code_or_msg=0):
    'Exit but check if final hard/soft reset is required'
    if args.reset:
        reset_val = args.reset
        args.reset = None
        mpcmd(args, 'soft-reset' if reset_val == 1 else 'reset')

    sys.exit(code_or_msg)

def mpcmd(args, cmdstr, quiet=False):
    'Send mpremote cmdstr to device'
    # Only build main command text the first time
    if mpcmd.cmdtext is None:
        arglist = [str(Path(args.path_to_mpremote).expanduser())]
        if args.device:
            cmd = 'connect ' if (args.device.startswith('/')
                    or ':' in args.device
                    or args.device.lower() == 'auto') else ''
            arglist.append(f'{cmd}{args.device}')

        if args.mount_unsafe_links:
            arglist.append(f'mount -l {args.mount_unsafe_links}')
        elif args.mount:
            arglist.append(f'mount {args.mount}')

        mpcmd.cmdtext = ' '.join(arglist)

    cmd = f'{mpcmd.cmdtext} {cmdstr}'

    if args.verbose:
        print(cmd)

    out = subprocess.DEVNULL if quiet else None
    res = subprocess.run(cmd, stderr=out, stdout=out, shell=True)
    if res.returncode != 0:
        doexit(args, res.returncode)
    return res.stdout

mpcmd.cmdtext = None

def mpcmd_wrap(args):
    'Extract args/options and send to device'
    opts = options[args.cmdname]
    arglist = [args.cmdname]
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

def main():
    'Main code'
    global cnffile

    # Parse arguments
    opt = argparse.ArgumentParser(description=__doc__,
            epilog=f'Type "{PROG} <command> -h" to see specific help/usage '
            ' for any of the above commands. Note you can set default '
            f'options in {CNFFILE}. '
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
    opt.add_argument('-p', '--path-to-mpremote', default='mpremote',
            help='path to mpremote program, default = "%(default)s"')
    opt.add_argument('-c', '--completion', action='store_true',
            help='output shell TAB completion code')
    opt.add_argument('-v', '--verbose', action='store_true',
            help='print executed commands (for debug)')
    cmd = opt.add_subparsers(title='Commands', dest='cmdname')

    # Add each command ..
    for cls in commands:
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
        for a in aliases:
            if a in aliases_all:
                sys.exit(f'command {name}: duplicate alias: {a}')
            aliases_all.add(a)

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
    cnflines = ''
    cnffile = CNFFILE.expanduser()
    if cnffile.exists():
        with cnffile.open() as fp:
            cnflines = [re.sub(r'#.*$', '', line).strip() for line in fp]
        cnflines = ' '.join(cnflines).strip()

    args = opt.parse_args(shlex.split(cnflines) + sys.argv[1:])

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

    # Run required command
    args.func(args)
    doexit(args)

def command(cls):
    'Append command to internal list'
    commands.append(cls)

class COMMAND:
    'Base class for all commands'
    def run(args):
        mpcmd(args, args.cmdname)

@command
class _get(COMMAND):
    'Copy one or more files from device to local directory.'
    aliases = ['g']

    def init(opt):
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('src', nargs='+',
                help='name of source file[s] on device')
        opt.add_argument('dst',
                help='name of local destination dir on PC, or "-" for stdout')

    def run(args):
        if args.dst == '-':
            # Output to stdout
            dst = None
        else:
            dst = Path(args.dst)
            # Ensure target dir exists
            parent = dst.parent if args.file else dst
            parent.mkdir(exist_ok=True, parents=True)

        for argsrc in args.src:
            src = infer_path(argsrc)
            srcstr = src and str(src).lstrip('/')
            if srcstr:
                if dst:
                    filedst = dst if args.file else dst / src.name
                    mpcmd(args, f'cp :{srcstr} {filedst}')
                else:
                    mpcmd(args, f'cat {srcstr}')

@command
class _put(COMMAND):
    'Copy one or more local files to directory on device.'
    aliases = ['p']

    def init(opt):
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('-r', '--recursive', action='store_true',
                help='copy local directory recursively to / on device')
        opt.add_argument('src', nargs='+',
                help='name of local source file[s] on PC')
        opt.add_argument('dst',
                help='name of destination dir on device')

    def run(args):
        dst = Path(infer_root(args.dst, dest=True))

        for argsrc in args.src:
            src = Path(argsrc)

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

            filedst = filedst.lstrip('/')
            mpcmd(args, f'{arg} {src} :{filedst}')

@command
class _copy(COMMAND):
    'Copy one of more remote files to a directory on device.'
    aliases = ['c']

    def init(opt):
        opt.add_argument('-f', '--file', action='store_true',
                help='destination is file, not directory')
        opt.add_argument('src', nargs='+',
                help='name of source file[s] on device')
        opt.add_argument('dst',
                help='name of destination dir on device')

    def run(args):
        dst = Path(infer_root(args.dst, dest=True))

        for argsrc in args.src:
            src = Path(argsrc)
            filedst = str(dst if args.file else dst / src.name).lstrip('/')
            mpcmd(args, f'cp :{src} :{filedst}')

@command
class _ls(COMMAND):
    'List directory on device.'
    def init(opt):
        opt.add_argument('dir', nargs='?', default='/',
                help='name of dir (default: %(default)s)')

    def run(args):
        path = infer_root(args.dir, dest=True)
        if path:
            mpcmd(args, f'ls {path}')

@command
class _mkdir(COMMAND):
    'Create the given directory[s] on device.'
    aliases = ['mkd']

    def init(opt):
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('dir', nargs='+', help='name of dir[s]')

    def run(args):
        for path in args.dir:
            path = infer_root(path)
            if path:
                mpcmd(args, f'mkdir {path}', args.quiet)

@command
class _rmdir(COMMAND):
    'Remove the given directory[s] on device.'
    aliases = ['rmd']

    def init(opt):
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('dir', nargs='+', help='name of dir[s]')

    def run(args):
        for path in args.dir:
            path = infer_root(path)
            if path:
                mpcmd(args, f'rmdir {path}', args.quiet)

@command
class _rm(COMMAND):
    'Remove the given file[s] on device.'
    def init(opt):
        opt.add_argument('-q', '--quiet', action='store_true',
                help='supress normal and error output')
        opt.add_argument('file', nargs='+', help='name of file[s]')

    def run(args):
        for path in args.file:
            path = infer_root(path)
            if path:
                mpcmd(args, f'rm {path}', args.quiet)

@command
class _touch(COMMAND):
    'Touch the given file[s] on device.'

    def init(opt):
        opt.add_argument('file', nargs='+', help='name of file[s]')

    def run(args):
        mpcmd_wrap(args)

@command
class _edit(COMMAND):
    '''
    Edit the given file[s] on device.

    Copies the file from device, opens your editor on that local file,
    then copies it back.
    '''
    aliases = ['e']

    def init(opt):
        opt.add_argument('file', nargs='+', help='name of file[s]')

    def run(args):
        mpcmd_wrap(args)

@command
class _reset(COMMAND):
    'Soft reset the device.'
    aliases = ['x']

    def run(args):
        args.reset = None
        mpcmd(args, 'soft-reset')

@command
class _reboot(COMMAND):
    'Hard reboot the device.'
    aliases = ['b']

    def init(opt):
        opt.add_argument('delay_ms', type=int, nargs='?',
                help='optional delay before reboot (millisecs)')

    def run(args):
        args.reset = None
        arg = f' {args.delay_ms}' if args.delay_ms else ''
        mpcmd(args, 'reset' + arg)

@command
class _repl(COMMAND):
    'Enter REPL on device.'
    aliases = ['r']

    def init(opt):
        opt.add_argument('-c', '--capture',
                help='capture output of the REPL session to given file')
        opt.add_argument('-x', '--inject-code',
                help='characters to inject at the REPL when Ctrl-J is pressed')
        opt.add_argument('-i', '--inject-file',
                help='file to inject at the REPL when Ctrl-K is pressed')

    def run(args):
        mpcmd_wrap(args)

@command
class _list(COMMAND):
    'List currently connected devices.'
    aliases = ['l', 'devs']

    def run(args):
        mpcmd(args, 'devs')

@command
class _run(COMMAND):
    'Run the given local scripts on device.'

    def init(opt):
        opt.add_argument('script', nargs='+',
                help='script to run')

    def run(args):
        for script in args.script:
            mpcmd(args, f'run "{script}"')

@command
class _eval(COMMAND):
    'Evaluate and print the given strings on device.'

    def init(opt):
        opt.add_argument('string', nargs='+',
                help='string to evaluate')

    def run(args):
        for string in args.string:
            mpcmd(args, f'eval "{string}"')

@command
class _exec(COMMAND):
    'Execute the given strings on device.'

    def init(opt):
        opt.add_argument('string', nargs='+',
                help='string to execute')

    def run(args):
        for string in args.string:
            mpcmd(args, f'exec "{string}"')

@command
class _mip(COMMAND):
    'Run mip to install packages on device.'
    aliases = ['m']

    def init(opt):
        opt.add_argument('-n', '--no-mpy', action='store_true',
                help='download .py files, not compiled .mpy files')
        opt.add_argument('-t', '--target',
                help='destination directory on device')
        opt.add_argument('-i', '--index',
                help='package index to use, default="micropython-lib"')
        opt.add_argument('command',
                help='mip command, e.g. "install"')
        opt.add_argument('package', nargs='+',
                help='package specifications, e.g. "name", "name@version", '
                         '"github.org/repo", "github.org/repo@branch"')

    def run(args):
        mpcmd_wrap(args)

@command
class _bootloader(COMMAND):
    'Enter bootloader on device.'

@command
class _df(COMMAND):
    'Show flash usage on device.'

@command
class _setrtc(COMMAND):
    'Set the Real Time Clock (RTC) on device.'

@command
class _version(COMMAND):
    'Show version of mpremote tool.'

@command
class _config(COMMAND):
    doc = f'Open the {PROG} configuration file with your editor.'
    aliases = ['cf']

    def run(args):
        subprocess.run(f'{get_editor()} {cnffile}'.split())

if __name__ == '__main__':
    main()
