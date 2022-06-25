## MPR - Wrapper for MicroPython mpremote tool

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

So [mpr][mpr] presents an alternative "git-like" interface which wraps
[mpremote][mpremote] and behaves like a conventional Linux command line
tool where only a single command is accepted (although note there are
global options to connect an explicit device and/or mount a local
directory before that command). Unlike [mpremote][mpremote], multiple
file/directory arguments can be specified for a command, allowing you to
exploit your shell wildcard abilities. Full in-built usage help is
available for the tool, and each of it's commands (see [Usage](#usage)
section below). It also provides a novel shortcut mechanism to infer
target device directories based on where on your local PC you are
copying files from or to. There are a few other nice features. The
following session shows small examples of [mpr][mpr] in use.

```
$ tree
./
├── boot.py
├── main.py
├── package_a.py
└── package_b/
    ├── file1.py
    └── file2.py

# View the inbuild usage/help for the put command:
$ mpr put -h
usage: mpr put [-h] [-f] src [src ...] dst

Copy one or more local files to directory on device.

positional arguments:
  src         name of source file[s] on PC
  dst         name of destination dir on device

options:
  -h, --help  show this help message and exit
  -f, --file  destination is file, not directory

# Copy all Python files to root on device:
$ mpr put *.py /
cp boot.py :boot.py
cp main.py :main.py
cp package_a.py :package_a.py

# Create package_b dir and copy all package_b Python files:
$ mpr mkdir package_b
mkdir :package_b
$ cd package_b
# The following exploits mpr's directory inference feature, see later section
$ mpr put *.py //
cp file1.py :package_b/file1.py
cp file2.py :package_b/file2.py

# Connect to explicit 1st port, mount local dir, and then import main.py:
$ mpr -d id:0001 -m . exec 'import main'
...
```

I have developed this tool on Linux. The latest version and
documentation is available at https://github.com/bulletmark/mpr.

[mpr]: https://github.com/bulletmark/mpr
[upy]: https://micropython.org/
[mpremote]: https://docs.micropython.org/en/latest/reference/mpremote.html

## Installation or Upgrade

Arch Linux users can install [mpr from the
AUR](https://aur.archlinux.org/packages/mpr/).

Python 3.6 or later is required. The [mpremote][mpremote] program must
be installed. Note [mpr is on PyPI](https://pypi.org/project/mpr/) so
just ensure that `python3-pip` and `python3-wheel` are installed then
type the following to install (or upgrade):

```
$ sudo pip3 install -U mpr
```

Or, to install from this source repository:

```
$ git clone http://github.com/bulletmark/mpr
$ cd mpr
$ sudo pip3 install -U .
```

To upgrade from the source repository:

```
$ cd mpr # i.e. to git source dir above
$ git pull
$ sudo pip3 install -U .
```
## Usage

Type `mpr` or `mpr -h` to view the following usage summary:

```
usage: mpr [-h] [-d DEVICE] [-l] [-m MOUNT] [-M MOUNT_UNSAFE_LINKS] [-r]
              [-s] [-p PATH_TO_MPREMOTE] [-c] [-v]
              {get,g,put,p,ls,mkdir,mkd,rmdir,rmd,rm,reset,x,repl,r,list,l,devs,run,eval,exec,bootloader,df,setrtc,version,edit}
              ...

This is a command line tool to wrap the MicroPython mpremote tool and provide
a more conventional command line interface. Multiple arguments can be
specified for commands and inbuilt usage help is provided for all commands.

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        serial port/device to connect to, default is "auto"
  -l, --list-device-names
                        just list out device mnemonics that can be used for
                        -d/--device
  -m MOUNT, --mount MOUNT
                        mount local directory on device before command
  -M MOUNT_UNSAFE_LINKS, --mount-unsafe-links MOUNT_UNSAFE_LINKS
                        mount local directory and allow external links
  -r, --reset-hard      do hard reset after command
  -s, --reset-soft      do soft reset after command
  -p PATH_TO_MPREMOTE, --path-to-mpremote PATH_TO_MPREMOTE
                        path to mpremote program, default = "mpremote"
  -c, --completion      output shell TAB completion code
  -v, --verbose         print executed commands (for debug)

Commands:
  {get,g,put,p,ls,mkdir,mkd,rmdir,rmd,rm,reset,x,repl,r,list,l,devs,run,eval,exec,bootloader,df,setrtc,version,edit}
    get (g)             Copy one or more files from device to local directory.
    put (p)             Copy one or more local files to directory on device.
    ls                  List directory on device.
    mkdir (mkd)         Create the given directory[s] on device.
    rmdir (rmd)         Remove the given directory[s] on device.
    rm                  Remove the given file[s] on device.
    reset (x)           Hard or soft reset the device.
    repl (r)            Enter REPL on device.
    list (l, devs)      List currently available devices.
    run                 Run the given local scripts on device.
    eval                Evaluate and print the given strings on device.
    exec                Execute the given strings on device.
    bootloader          Enter bootloader on device.
    df                  Show flash usage on device.
    setrtc              Set the Real Time Clock (RTC) on device.
    version             Show version of mpremote tool.
    edit                Open the mpr configuration file with your $VISUAL
                        editor.

Type "mpr <command> -h" to see specific help/usage for any of the above
commands. Note you can set default options in ~/.config/mpr.conf. Use "mpr
edit" to conveniently change the file.
```

Type `mpr <command> -h` to see specific help/usage for any
individual command:

### Command `get`

```
usage: mpr get [-h] [-f] src [src ...] dst

Copy one or more files from device to local directory.

positional arguments:
  src         name of source file[s] on device
  dst         name of local destination dir on PC, or "-" for stdout

options:
  -h, --help  show this help message and exit
  -f, --file  destination is file, not directory

aliases: g
```

### Command `put`

```
usage: mpr put [-h] [-f] src [src ...] dst

Copy one or more local files to directory on device.

positional arguments:
  src         name of local source file[s] on PC
  dst         name of destination dir on device

options:
  -h, --help  show this help message and exit
  -f, --file  destination is file, not directory

aliases: p
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
usage: mpr rmdir [-h] [-q] dir [dir ...]

Remove the given directory[s] on device.

positional arguments:
  dir          name of dir[s]

options:
  -h, --help   show this help message and exit
  -q, --quiet  supress normal and error output

aliases: rmd
```

### Command `rm`

```
usage: mpr rm [-h] [-q] file [file ...]

Remove the given file[s] on device.

positional arguments:
  file         name of file[s]

options:
  -h, --help   show this help message and exit
  -q, --quiet  supress normal and error output

aliases: <none>
```

### Command `reset`

```
usage: mpr reset [-h] [-s] [delay_ms]

Hard or soft reset the device.

positional arguments:
  delay_ms    optional delay before reset (millisecs)

options:
  -h, --help  show this help message and exit
  -s, --soft  Do soft reset instead of hard reset

aliases: x
```

### Command `repl`

```
usage: mpr repl [-h] [-c CAPTURE] [-x INJECT_CODE] [-i INJECT_FILE]

Enter REPL on device.

options:
  -h, --help            show this help message and exit
  -c CAPTURE, --capture CAPTURE
                        capture output of the REPL session to given file
  -x INJECT_CODE, --inject-code INJECT_CODE
                        characters to inject at the REPL when Ctrl-J is
                        pressed
  -i INJECT_FILE, --inject-file INJECT_FILE
                        file to inject at the REPL when Ctrl-K is pressed

aliases: r
```

### Command `list`

```
usage: mpr list [-h]

List currently available devices.

options:
  -h, --help  show this help message and exit

aliases: l, devs
```

### Command `run`

```
usage: mpr run [-h] script [script ...]

Run the given local scripts on device.

positional arguments:
  script      script to run

options:
  -h, --help  show this help message and exit

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

### Command `exec`

```
usage: mpr exec [-h] string [string ...]

Execute the given strings on device.

positional arguments:
  string      string to execute

options:
  -h, --help  show this help message and exit

aliases: <none>
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

### Command `setrtc`

```
usage: mpr setrtc [-h]

Set the Real Time Clock (RTC) on device.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `version`

```
usage: mpr version [-h]

Show version of mpremote tool.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

### Command `edit`

```
usage: mpr edit [-h]

Open the mpr configuration file with your $VISUAL editor.

options:
  -h, --help  show this help message and exit

aliases: <none>
```

## Compatibility Notes

This section describes differences that users transitioning from
[mpremote][mpremote] to [mpr][mpr] should be aware of.

The usage/arguments of individual mpremote commands are not easily
discoverable. mpr overcomes this by providing in-built full usage help
for every individual command:

```
# See overall help:
$ mpr (or mpr -h)

# See help for a specific command:
$ mpr mkdir -h
```

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

All device full path names and mpremote defined shortcut mnemonics can
be used for the `-d/--device` option. For convenience, you can type `mpr
-l` to print out the standard mpremote device mnemonics and names which
can be used.

The `cp` command in mpremote is implemented with explicit `get` and
`put` commands in mpr so there is no need for the user to use a `:` char
to infer direction.

With mpremote all commands that take an argument only accept a single
argument whereas with mpr all commands can accept multiple arguments
(which mpr implements internally by executing mpremote multiple times).
Most specifically, this allow you to exploit wildcard file selection
with your shell. E.g to copy all the Python files from your local
directory you simply do:

```
$ mpr put *.py /
```

With mpremote, you would have to do the above with individual commands,
one for each file.

mpr provides shortcut aliases for the most commonly used longer
commands, e.g. `r` for `repl`, `p` for `put`, and `g` for `get`. See the
main help/usage for a list of all commands and their aliases. So the
above command can be tersely typed as:

```
$ mpr p *.py /
```

Note that mpr `get` and `put` functions always expect the specified
target to be a directory, so if you want to rename a file when you copy
it then you must explicitly indicate the target to be a file, e.g.

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

`soft-reset` is not implemented as a separate command in mpr, it is
implemented using the `-s/--soft` option on the `reset` command.

The `cat` command is not implemented. Instead type `mpr get file.py -`
to pipe a file to standard output.

The `disconnect`, `resume`, and `umount` commands are appropriate for
use with "chained" commands which are not relevant to mpr so are not
implemented.

You can not define shortcuts/macros with mpr, although all the standard
macros within mpremote are available in mpr.

## Default Arguments

You can set default starting options for your user in
`~/.config/mpr.conf`. E.g. use this to set a default
`--path-to-mpremote` setting so it does not have to be specified each
time. Blank lines and anything after a `#` on any line is ignored.

E.g. create `~/.config/mpr.conf` with contents:

```
--path-to-mpremote ~/.local/bin/mpremote
```

Now you need only specify the command, e.g. `mpr ls` and it will use
that specified `~/.local/bin/mpremote` program.

You can use the `mpr edit` command to conveniently change this file
(merely as a shortcut to explicitly specifying your editor and the path
to the file). You can keep commented out configurations for a number of
different settings in your file (e.g. various `--device` and/or
`--mount` options) and switch between them by un-commenting the lines
you want to use.

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

To avoid this verbose typing, you can simply type the following instead:

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

## Shell Tab Completion

If you install the Python 3 [argcomplete](https://kislyuk.github.io/argcomplete/) package:

```
$ sudo pip3 install -U argcomplete
```

Then mpr will automatically use this to enable [shell tab
completion](https://en.wikipedia.org/wiki/Command-line_completion) on
mpr commands and options. You merely need to type the following to
source the necessary shell code into your current terminal session (or
add this line to your `~/.bashrc` to enable it permanently):

```
$ . <(mpr -c)
```

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

<!-- vim: se ai syn=markdown: -->
