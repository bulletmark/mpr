## MPR - Wrapper for MicroPython mpremote tool
[![PyPi](https://img.shields.io/pypi/v/mpr)](https://pypi.org/project/mpr/)
[![AUR](https://img.shields.io/aur/version/mpr)](https://aur.archlinux.org/packages/mpr/)

The [mpremote][mpremote] command line tool is used to interact with a
[MicroPython][upy] device over a USB/serial connection. It's an official
part of [MicroPython][upy], well featured, and it works more reliably
than competing tools. However, [mpremote][mpremote] exhibits an
unconventional and slightly awkward Linux command line interface.
[mpremote][mpremote] allows "chaining" of multiple sequential commands
but the vast majority of users merely want to copy/delete files etc and
unfortunately the [mpremote][mpremote] user interface compromises
usability for those most common use-cases. Also, users expect in-built
help for all commands so they can easily see usage and expected
arguments (e.g. like [git](https://git-scm.com/) provides).

So [mpr][mpr] presents an alternative interface which wraps
[mpremote][mpremote] to make it appear like a conventional Linux
command line tool where only a single command is accepted (although
there are global options to connect an explicit device; and/or mount a
local directory before that command; and/or reset/reboot after the
command). Unlike [mpremote][mpremote], [mpr][mpr] always allows you to
exploit your shell wildcard abilities to pass multiple file/directory
arguments to commands. Full in-built usage help is available for the
tool, and each of it's commands (see [Usage](#usage) section below). It
also provides a novel shortcut mechanism to [infer target device
directories](#directorypath-inference) based on where on your local PC
you are copying files from or to. There are a few other nice
[features](#compatibility-notes). The following session shows small
examples of [mpr][mpr] in use.

```
$ tree
./
├── Makefile
├── boot.py
├── main.py
├── package_a.py
└── package_b/
    ├── file1.py
    └── file2.py

# View the inbuild usage/help for the put command (Note you can just type
# mpr without any arguments to see all available commands, see Usage
# section below):
$ mpr put -h
usage: mpr put [-h] [-f] [-r] src [src ...] dst

Copy one or more local files to directory on device.

positional arguments:
  src              name of local source file[s] on PC
  dst              name of destination dir on device

options:
  -h, --help       show this help message and exit
  -f, --file       destination is file, not directory
  -r, --recursive  copy local directory recursively to / on device

# Copy all Python files to root on device:
$ mpr put *.py /
cp boot.py :boot.py
cp main.py :main.py
cp package_a.py :package_a.py

# Create package_b dir and copy all package_b Python files:
$ mpr mkdir package_b
mkdir :package_b
$ cd package_b
# The following exploits mpr's directory inference feature to save typing
# the target directory, see Directory/Path Inference section below:
$ mpr put *.py //
cp file1.py :package_b/file1.py
cp file2.py :package_b/file2.py

# Connect to explicit 1st port, mount local dir, and then import main.py:
$ mpr -d id:0001 -m . exec 'import main'
...
```

I have developed this tool on Linux. The latest version and
documentation is available at https://github.com/bulletmark/mpr.

## Installation

Arch Linux users can install [mpr from the
AUR](https://aur.archlinux.org/packages/mpr/).

Python 3.7 or later is required. The [mpremote][mpremote] program must be
[installed](#path-to-mpremote). If you want to use the `xrun` command then you
also need to install the [mpy-cross][mpy-cross] program.

Note [mpr][mpr-py], [mpremote][mpremote-py], and [mpy-cross][mpy-cross] are
all available on [PyPI](https://pypi.org/) and so the easiest way to install them is to use
[`uv tool`][uvtool] (or [`pipx`][pipx] or [`pipxu`][pipxu]). I.e:

To install:

```sh
$ uv tool install mpr
$ uv tool install mpremote
$ uv tool install mpy-cross  # if needed, for xrun command
```

To upgrade:

```sh
$ uv tool upgrade mpr mpremote mpy-cross
```

To uninstall:

```sh
$ uv tool uninstall mpr mpremote mpy-cross
```

## Usage

Type `mpr` or `mpr -h` to view the usage summary:

```
usage: mpr [-h] [-d DEVICE] [-m MOUNT] [-M MOUNT_UNSAFE_LINKS] [-x]
                   [-b] [-p PATH_TO_MPREMOTE] [-X PATH_TO_MPY_CROSS]
                   [--mip-list-url MIP_LIST_URL] [-v] [-V]
                   {get,g,put,p,copy,c,ls,mkdir,mkd,rmdir,rmd,rm,touch,edit,e,reset,x,reboot,b,repl,r,list,l,devs,run,xrun,xr,exec,eval,mip,m,bootloader,df,rtc,version,config,cf} ...

This is a command line tool to wrap the MicroPython mpremote tool and provide
a more conventional command line interface. Multiple arguments can be
specified for commands and inbuilt usage help is provided for all commands.

options:
  -h, --help            show this help message and exit
  -d, --device DEVICE   serial port/device to connect to, default is "auto".
                        Specify "-d list" to print out device mnemonics that
                        can be used.
  -m, --mount MOUNT     mount local directory on device before command
  -M, --mount-unsafe-links MOUNT_UNSAFE_LINKS
                        mount local directory and allow external links
  -x, --reset           do soft reset after command
  -b, --reboot          do hard reboot after command
  -p, --path-to-mpremote PATH_TO_MPREMOTE
                        path to mpremote program. Assumes same directory as
                        this program, or then just "mpremote"
  -X, --path-to-mpy-cross PATH_TO_MPY_CROSS
                        path to mpy-cross program (for xrun command). Assumes
                        same directory as mpremote, or then just "mpy-cross"
  --mip-list-url MIP_LIST_URL
                        mip list url for packages,
                        default="https://micropython.org/pi/v2/index.json"
  -v, --verbose         print mpremote execution command line (for debug)
  -V, --version         print mpr version

Commands:
  {get,g,put,p,copy,c,ls,mkdir,mkd,rmdir,rmd,rm,touch,edit,e,reset,x,reboot,b,repl,r,list,l,devs,run,xrun,xr,exec,eval,mip,m,bootloader,df,rtc,version,config,cf}
    get (g)             Copy one or more files from device to local directory.
    put (p)             Copy one or more local files to directory on device.
    copy (c)            Copy one of more remote files to a directory on
                        device.
    ls                  List directory on device.
    mkdir (mkd)         Create the given directory[s] on device.
    rmdir (rmd)         Remove the given directory[s] on device.
    rm                  Remove the given file[s] on device.
    touch               Touch the given file[s] on device.
    edit (e)            Edit the given file[s] on device.
    reset (x)           Soft reset the device.
    reboot (b)          Hard reboot the device.
    repl (r)            Enter REPL on device.
    list (l, devs)      List currently connected devices.
    run                 Run the given local program on device.
    xrun (xr)           Tool to compile and run a local application/program on
                        device.
    exec                Execute the given strings on device.
    eval                Evaluate and print the given strings on device.
    mip (m)             Install packages from micropython-lib or third-party
                        sources.
    bootloader          Enter bootloader on device.
    df                  Show flash usage on device.
    rtc                 Get/set the Real Time Clock (RTC) time from/to device.
    version             Show mpremote version.
    config (cf)         Open the mpr configuration file with your editor.

Type "mpr <command> -h" to see specific help/usage for any of the above
commands. Some commands offer a short alias as seen in parentheses above. Note
you can set default options in ~/.config/mpr.conf (e.g. for --path-to-mpremote
or --mip-list-url). Use "mpr config" to conveniently change the file.
```

Type `mpr <command> -h` to see specific help/usage for any
individual command:

### Command `get`

```
usage: mpr get [-h] [-f] [-r] [-F] src [src ...] dst

Copy one or more files from device to local directory.

positional arguments:
  src              name of source file[s] on device
  dst              name of local destination dir on PC, or "-" for stdout

options:
  -h, --help       show this help message and exit
  -f, --file       destination is file, not directory
  -r, --recursive  copy directory recursively
  -F, --force      force recursive copy to overwrite identical files

aliases: g
```

### Command `put`

```
usage: mpr put [-h] [-f] [-r] [-F] src [src ...] dst

Copy one or more local files to directory on device.

positional arguments:
  src              name of local source file[s] on PC
  dst              name of destination dir on device

options:
  -h, --help       show this help message and exit
  -f, --file       destination is file, not directory
  -r, --recursive  copy directory recursively
  -F, --force      force recursive copy to overwrite identical files

aliases: p
```

### Command `copy`

```
usage: mpr copy [-h] [-f] [-r] [-F] src [src ...] dst

Copy one of more remote files to a directory on device.

positional arguments:
  src              name of source file[s] on device
  dst              name of destination dir on device

options:
  -h, --help       show this help message and exit
  -f, --file       destination is file, not directory
  -r, --recursive  copy directory recursively
  -F, --force      force recursive copy to overwrite identical files

aliases: c
```

### Command `ls`

```
usage: mpr ls [-h] [dir]

List directory on device.

positional arguments:
  dir         name of dir (default: /)

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `mkdir`

```
usage: mpr mkdir [-h] [-q] dir [dir ...]

Create the given directory[s] on device.

positional arguments:
  dir          name of dir[s]

options:
  -h, --help   show this help message and exit
  -q, --quiet  supress normal and error output

aliases: mkd
```

### Command `rmdir`

```
usage: mpr rmdir [-h] [-q] [--rf] [-d DEPTH] dir [dir ...]

Remove the given directory[s] on device.

positional arguments:
  dir                name of dir[s]

options:
  -h, --help         show this help message and exit
  -q, --quiet        supress normal and error output
  --rf               force remove given directories and files recursively and
                     quietly
  -d, --depth DEPTH  use with --rf to remove paths recursively to given depth
                     only, 1="/*", 2="/*/*", etc. Default is no limit.

aliases: rmd
```

### Command `rm`

```
usage: mpr rm [-h] [-q] [--rf] [-d DEPTH] file [file ...]

Remove the given file[s] on device.

positional arguments:
  file               name of file[s]

options:
  -h, --help         show this help message and exit
  -q, --quiet        supress normal and error output
  --rf               force remove given directories and files recursively and
                     quietly
  -d, --depth DEPTH  use with --rf to remove paths recursively to given depth
                     only, 1="/*", 2="/*/*", etc. Default is no limit.

aliases: <none>
```

### Command `touch`

```
usage: mpr touch [-h] file [file ...]

Touch the given file[s] on device.

positional arguments:
  file        name of file[s]

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `edit`

```
usage: mpr edit [-h] file [file ...]

Edit the given file[s] on device. Copies the file from device, opens your
editor on that local file, then copies it back.

positional arguments:
  file        name of file[s]

options:
  -h, --help  show this help message and exit

aliases: e
```

### Command `reset`

```
usage: mpr reset [-h]

Soft reset the device.

options:
  -h, --help  show this help message and exit

aliases: x
```

### Command `reboot`

```
usage: mpr reboot [-h] [delay_ms]

Hard reboot the device.

positional arguments:
  delay_ms    optional delay before reboot (millisecs)

options:
  -h, --help  show this help message and exit

aliases: b
```

### Command `repl`

```
usage: mpr repl [-h] [-e] [-c CAPTURE] [-x INJECT_CODE]
                        [-i INJECT_FILE]

Enter REPL on device.

options:
  -h, --help            show this help message and exit
  -e, --escape-non-printable
                        print non-printable bytes/chars as hex codes
  -c, --capture CAPTURE
                        capture output of the REPL session to given file
  -x, --inject-code INJECT_CODE
                        characters to inject at the REPL when Ctrl-J is
                        pressed
  -i, --inject-file INJECT_FILE
                        file to inject at the REPL when Ctrl-K is pressed

aliases: r
```

### Command `list`

```
usage: mpr list [-h]

List currently connected devices.

options:
  -h, --help  show this help message and exit

aliases: l, devs
```

### Command `run`

```
usage: mpr run [-h] [-f] script [script ...]

Run the given local program on device.

positional arguments:
  script           script to run

options:
  -h, --help       show this help message and exit
  -f, --no-follow  do not keep following output, return immediately

aliases: <none>
```

### Command `xrun`

```
usage: mpr xrun [-h] [-f] [-D DEPTH] [-o] [-C] [-e EXCLUDE]
                        [--map MAP] [-1]
                        [prog] [args ...]

Tool to compile and run a local application/program on device. Displays
program output in your local terminal using mpremote and, in parallel, it
waits watching for edits/changes to Python source files in the associated
directory tree on your host. When changes are detected then new .mpy bytecode
files for changed files are compiled using mpy-cross in a hidden cache
directory on your host and then copied to the device. The specified program is
then restarted and redisplayed in your local terminal. Command line arguments
on the host can be passed to the program via sys.argv on the device. Only .mpy
bytecode files are copied to the device, never .py source files, and the
specified prog[.py] is imported to run as a .mpy file. So you run this utility
in one terminal window while you edit your source files in other windows and
your program will be automatically restarted and redisplayed each time you
save your changes. Since all bytecode compilation is done on your host, not on
the remote device, your development workflow is faster to build, load, and
run; and device memory usage and fragmentation is significantly reduced. Note
that you can specify default options for this command locally in your working
directory in mpr-xrun.conf, or globally in ~/.config/mpr-xrun.conf.

positional arguments:
  prog                  name of .py module to run, e.g. "main.py". If not
                        specified then new .mpy files are merely compiled and
                        copied to the device.
  args                  optional arguments to pass in sys.argv to started
                        program. Separate with -- if switch options are passed

options:
  -h, --help            show this help message and exit
  -f, --flush           flush cache and force update of all .mpy files at
                        start
  -D, --depth DEPTH     directory depth limit, 1 = current directory only
  -o, --only            only monitor the specified program file, not the whole
                        directory/tree
  -C, --compile-only    just compile new .mpy files, don't copy to device or
                        run any program
  -e, --exclude EXCLUDE
                        exclude specified directory or file from monitoring.
                        Can specify this option multiple times. If you exclude
                        a directory then all files/dirs below it are also
                        excluded. Default excludes are "main.py" and
                        "boot.py". Any specified runnable "prog" file is
                        removed from the excludes list.
  --map MAP             map specified source name to different target name
                        when run as main prog, e.g. "main:main1" to map
                        main.py -> main1.mpy on target and "main1" will be
                        run. Can specify this option multiple times, e.g. may
                        want to map main.py and boot.py permanently for when
                        you run either as prog.
  -1, --once            run once only

aliases: xr
```

### Command `exec`

```
usage: mpr exec [-h] [-f] string [string ...]

Execute the given strings on device.

positional arguments:
  string           string to execute

options:
  -h, --help       show this help message and exit
  -f, --no-follow  do not keep following output, return immediately

aliases: <none>
```

### Command `eval`

```
usage: mpr eval [-h] string [string ...]

Evaluate and print the given strings on device.

positional arguments:
  string      string to evaluate

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `mip`

```
usage: mpr mip [-h] [-n] [-t TARGET] [-i INDEX]
                       {install,list} [package ...]

Install packages from micropython-lib or third-party sources.

positional arguments:
  {install,list}       mip command
  package              package specifications, e.g. "name", "name@version",
                       "github.org/repo", "github.org/repo@branch"

options:
  -h, --help           show this help message and exit
  -n, --no-mpy         download .py files, not compiled .mpy files
  -t, --target TARGET  destination directory on device, default="/lib"
  -i, --index INDEX    package index to use, default="micropython-lib"

aliases: m
```

### Command `bootloader`

```
usage: mpr bootloader [-h]

Enter bootloader on device.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `df`

```
usage: mpr df [-h]

Show flash usage on device.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `rtc`

```
usage: mpr rtc [-h] [-s]

Get/set the Real Time Clock (RTC) time from/to device.

options:
  -h, --help  show this help message and exit
  -s, --set   set the RTC to the current PC time, default is to get the time

aliases: <none>
```

### Command `version`

```
usage: mpr version [-h]

Show mpremote version.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `config`

```
usage: mpr config [-h]

Open the mpr configuration file with your editor.

options:
  -h, --help  show this help message and exit

aliases: cf
```

## Compatibility Notes

This section describes differences that users transitioning from
[mpremote][mpremote] to [mpr][mpr] should be aware of.

The usage/arguments of individual mpremote commands are not easily
discoverable. mpr overcomes this by providing in-built full
[usage](#usage) help for every individual command:

```
# See overall help:
$ mpr (or mpr -h)

# See help for a specific command:
$ mpr mkdir -h
```

Unlike mpremote, mpr implements each command as a standard Pythog
[Argparse
subparser](https://docs.python.org/3/library/argparse.html#sub-commands)
which means the help output is automatically generated from the software
code so the user can be confident the help output is complete, and the
individual command descriptions are syntactically accurate.

Most mpremote commands are available, but some are implemented in a
different manner. Commands can not be chained, but that is usually only
required for the mpremote `connect` and `mount` commands. In mpr, these
two commands are available as global command line options, not as
explicit commands. So for example, to connect to a specific device and
mount your local directory before importing a module in mpremote you can
do the following:

```
$ mpremote connect id:0001 mount . exec 'import test'
```

The equivalent mpr command is:

```
$ mpr -d id:0001 -m . exec 'import test'
```

All device full path names and mpremote defined [shortcut
names](#device-shortcut-names) can be used for the `-d/--device`
option. For convenience, you can type `mpr -d list` to print out the
standard mpremote device names and shortcuts.

The `cp` command in mpremote is implemented with explicit `get` and
`put` commands in mpr so there is no need for the user to use a `:` char
to infer direction.

mpr provides shortcut aliases for the most commonly used longer
commands, e.g. `r` for `repl`, `p` for `put`, and `g` for `get`. See the
main help/usage for a list of all commands and their aliases. E.g,
the command `mpr put *.py /` can instead be tersely typed as: `mpr p *.py /`.

Note that the mpr `get`, `put`, and `copy` commands always expect the
specified target argument to be a directory, so if you want to rename a
file when you copy it then you must explicitly indicate the target to be
a file using the `-f/--file` option, e.g.

```
$ mpr get file.py newfile.py

# The above will fetch file.py to file.py/newfile.py which is not what
# you want. Add -f switch to specify that the target is a file:

$ mpr get -f file.py newfile.py
```

Commands `mkdir`, `rmdir`, and `rm` have a `-q/--quiet` option added to
suppress normal and error output. E.g. you could use this in a script to
ignore a `mkdir` error when the directory already exists.

The `fs` command is redundant in mpremote so is not implemented in mpr.

`soft-reset` is implemented in mpr as `reset`. Hardware reset is
implemented in mpr as `reboot`. Mpr also adds global options to reset
(`-x/--reset`) or reboot (`-b/--reboot`) after the specified command is
run.

The `cat` command is implemented differently. Instead type `mpr get
file.py -` to pipe a file to standard output.

The `disconnect`, `resume`, and `umount` commands are appropriate for
use with "chained" commands which are not relevant to mpr so are not
implemented.

You can not define shortcuts/macros with mpr, although all the standard
macros within mpremote are available in mpr. Of course you can create
standard shell based aliases and/or scripts invoking mpr if you want.

The `mip` command in mpremote currently only offers an `install`
sub-command but `mpr` also offers a `list` sub-command which fetches all
package descriptions from micropython.org and then prints their names,
versions, and descriptions.

## Device Shortcut Names

`mpremote` provides shortcut names, e.g:

```
a0, a1, a2, a3 - connect to /dev/ttyACMn
u0, u1, u2, u3 - connect to /dev/ttyUSBn
c0, c1, c2, c3 - connect to COMn
```

However for mpremote this only works for those first 4 devices of each
type (as per this
[bug](https://github.com/micropython/micropython/issues/11422)) so
instead `mpr` converts these shortcuts itself so you can use up to any
number you want, e.g: `mpr -d u10 ls` is a shortcut for `mpr -d
/dev/ttyUSB10 ls`.

Use `mpr -d list` to remind yourself of device and shortcut names.

## Recursive Deletion

`mpremote` allows you to delete one or more specified files but does not
provide a mechanism to recursively delete a whole directory and it's
files. Since this is commonly desired, `mpr` adds a `--rf` option to
both the `rm` and `rmdir` commands. The specified directory and it files
are deleted recursively (although the top/root directory `/` is always
preserved). Some examples:

```
# Remove all files and directories on the device (but preserve '/'):
$ mpr rm --rf /

# Remove /lib/ directory completely (including it's files/dirs):
$ mpr rm --rf /lib

# Remove the top level files but preserve any directories:
$ mpr rm --rf --depth 1 /
```

## Remote Compilation and Development

`mpremote` (and thus `mpr`) provides the `run` command to run a single
python file on the connected device. However, this proves inadequate
when developing any significant application which is comprised of
multiple files, and sometimes in various package directories. So `mpr`
adds an `xrun` command (think extended `run`).

Running the `xrun` command in an application's directory runs that program and
displays program output in your local terminal. In parallel, it waits watching
for edits/changes to Python source files in that directory tree on your host.
When changes are detected then new `.mpy` bytecode files for changed files are
compiled using [`mpy-cross`][mpy-cross] in a hidden cache directory on your
host and then copied to the device. The specified program is then restarted and
redisplayed in your local terminal. Command line arguments on the host can be
passed to the program via `sys.argv` on the device. Only `.mpy` bytecode files
are copied to the device, never `.py` source files, and the specified
`prog[.py]` is imported to run as a `.mpy` file. So you run this utility in one
terminal window while you edit your source files in other windows and your
program will be automatically restarted and redisplayed each time you save your
changes. Since all bytecode compilation is done on your host, not on the remote
device, your development workflow is faster to build, load, and run; and device
memory usage and fragmentation is significantly reduced.

Note that `mpr` does not automatically create the required mirror of
directories for your files on the device. You are expected to initially
create/update these manually using the `mpr mkdir` and/or `mpr rmdir`
commands.

Note that you can specify default options for the `xrun` command locally
in your working directory in `mpr-xrun.conf`, or globally in
`~/.config/mpr-xrun.conf`.

## Default Options

You can set default global starting options for your user in
`~/.config/mpr.conf`. E.g. use this to set a default
`--path-to-mpremote` setting so it does not have to be specified each
time. Blank lines and anything after a `#` on any line is ignored.

E.g. create `~/.config/mpr.conf` with contents:

```
--path-to-mpremote ~/.local/bin/mpremote
```

Now you need only specify the command, e.g. `mpr ls` and it will use
that specified `~/.local/bin/mpremote` program.

You can use the `mpr config` command to conveniently change this file
(merely as a shortcut to explicitly specifying your editor and the path
to the file). You can keep commented out configurations for a number of
different settings in your file (e.g. various `--device` and/or
`--mount` options) and switch between them by un-commenting the lines
you want to use.

Note that the `xrun` command can be independently set with it's own
default options as described in the previous section.

## Directory/Path Inference

For the following discussion, assume you have a project structured as
follows on your local machine and the same directory hierarchy is used
on your target device.

```
./
├── file1.py
├── file2.py
└── mymodule/
    ├── file3.py
    ├── file4.py
    └── templates/
        ├── file5.tpl
        └── file6.tpl
```

mpr automatically appends the target file name when appropriate, e.g.
if you are sitting in the root of the above tree, you only need to type
`mpr put file1.py /` instead of `mpr put file1.py /file1.py`. For this
reason, you can copy multiple files with `mpr put file1.py file2.py /`
or `mpr put *.py /`. Further to this, mpr can also infer the
appropriate target directory as described next.

If you are currently sitting in the directory `mymodule/templates/` on
your local machine and you want to copy `file5.tpl` to the
`/mymodule/templates/` on the target device then the command you would
naively use is:

```
$ mpr put file5.tpl /mymodule/templates
```

To avoid this verbose typing, mpr allows you to instead use the
following shortcut because mpr can "infer" the full target path based on
your current local directory:

```
$ mpr put file5.tpl ///
```

To then remove that same file from the target device:

```
$ mpr rm ///file5.tpl
```

I.e., mpr intercepts the two redundant lead slashes for the above two
cases and automatically inserts the parent and current directory names
in the path string (determined from the current directory on your local
machine). To be clear, if you are sitting one level above in the
`mymodule` directory then the command to copy to that same directory on
the target device is:

```
$ mpr put file3.py //
```

You can also use this shorthand for source files/dirs by inserting a
sequence of leading slashes as a "dummy" argument. Once set, that dummy
argument sets the default directory for the following arguments. E.g. if
you are sitting in the local `templates` directory then to delete all
the `*.tpl` files in the same directory on the target you can type:

```
$ mpr rm /// file5.tpl file6.tpl
```
or just:

```
$ mpr rm /// *.tpl
```

Note the 2nd "trick" above exploits the wildcard file list generated by
your shell to pass those local file names to the remote device. It
assumes those same names exist in the analogous directory there (and
arguably this trick should be avoided!).

## Path to mpremote

Many using this program possibly also have downloaded the MicroPython
source tree for building firmware images. E.g. the source installed at
`/opt/micropython/` also includes mpremote at
`/opt/micropython/tools/mpremote/mpremote.py`. So for this reason mpr
does not require mpremote to be explicitly installed as a formal
package.

Mpr first looks for a `mpremote` program in the same directory as it's
own executable `mpr` self, otherwise mpr assumes `mpremote` is somewhere
in your PATH (e.g. at `/usr/bin/mpremote`). Alternatively, you can
specify the option `--path-to-mpremote` to explicitly specify the path,
e.g. if you have the MicroPython source installed somewhere then you
don't need to formally install mpremote and can instead just set e.g.
`--path-to-mpremote /opt/micropython/tools/mpremote/mpremote.py` in your
`~/.config/mpr.conf` as a [default option](#default-options) as
described in a previous [section](#default-options).

Note, similar to above, you can also specify the path to the `mpy-cross`
program using the `--path-to-mpy-cross` option.

## Command Line Tab Completion

Command line shell [tab
completion](https://en.wikipedia.org/wiki/Command-line_completion) is
automatically enabled on `mpr` commands and options using
[`argcomplete`](https://github.com/kislyuk/argcomplete). You may need to
first (once-only) [activate argcomplete global
completion](https://github.com/kislyuk/argcomplete#global-completion).

## Troubleshooting

Note that mpr is essentially just a thin wrapper around mpremote and
exists merely to provide a simpler, and hopefully more consistent and
familiar command line interface, particularly for Linux shell command
line users.

This means that most execution problems you may encounter will likely
due to mpremote, not mpr. So if you think your find a problem in mpr,
always run mpr with the `-v` option to see the command line being
executed with mpremote. If that command line looks ok, but mpremote is
not doing what you expect, then run mpremote manually with those same
mpremote options + arguments to prove to yourself that mpremote is
exhibiting that issue, not mpr.

If you run mpr with the `-v` option and see a wrong or unexpected
mpremote command being executed, then certainly raise an mpr [discussion
thread](https://github.com/bulletmark/mpr/discussions), or
[issue](https://github.com/bulletmark/mpr/issues) about that.

## License

Copyright (C) 2022 Mark Blakeney. This program is distributed under the
terms of the GNU General Public License.
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or any later
version.
This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License at <http://www.gnu.org/licenses/> for more details.

[mpr]: https://github.com/bulletmark/mpr
[upy]: https://micropython.org/
[mpremote]: https://docs.micropython.org/en/latest/reference/mpremote.html
[mpr-py]: https://pypi.org/project/mpr/
[mpremote-py]: https://pypi.org/project/mpremote/
[mpy-cross]: https://pypi.org/project/mpy-cross/
[pipx]: https://github.com/pypa/pipx
[pipxu]: https://github.com/bulletmark/pipxu
[uvtool]: https://docs.astral.sh/uv/guides/tools/#installing-tools

<!-- vim: se ai syn=markdown: -->
