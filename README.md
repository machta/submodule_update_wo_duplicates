# Submodule Update without Duplicates

Replacement for `git submodule update --init --recursive` that saves space by symlinking duplicate repositories.

**Usage:**

Just run `submodule_update_wo_duplicates.py` from the root directory of your Git repo like so:

```bash
$ python3 submodule_update_wo_duplicates.py
```

Or you can install it into your path under a name starting with `git-`. Example (assuming `$HOME/bin` is in your path):

```bash
$ FILE_NAME=~/bin/git-dedup_sub_update ; echo -e > "$FILE_NAME" '#!/bin/sh\npython3 ~/path/to-file/submodule_update_wo_duplicates.py' && chmod +x "$FILE_NAME"
```

Then you can use it like a regular git command:

```bash
$ git dedup_sub_update
```

**Prerequisites:**

```bash
$ pip3 install gitpython
```

## Motivation

If you use a lot of recursive submodules, you might notice that your project grows unreasonably big over time. You might have *hundreds* of submodules even though in total there are only a few unique repositories involved. Obviously this is very wasteful in terms of disk usage, network traffic and even CPU.

This simple tool helps mitigate this problem by updating the submodules "smartly". It is very close in functionality to `git submodule update --init --recursive --force`. It will recursively initiate, pull & checkout all submodules, but it will try to reuse previously cloned repos whenever possible.

## A Few Non-obvious Points About What the Script Does

* For a submodule to be reused it has to have the same remote URL and be pointed to the same commit (i.e. the same repo can still be cloned twice but in different versions).
* The direct submodules of the root repository will be always fully cloned. You can switch them to a different version as you need. Then just run `submodule_update_wo_duplicates.py` to update the linked submodules to the proper versions again.
* Changes in srcrevs of submodules that are *staged* (i.e. green on `git status`) will be taken into account the same way as regular submodule update does: they will not be overwritten.
* `submodule_update_wo_duplicates.py` is much more aggressive than your regular submodule update. Notice the `--force` above. It replaces submodule directories with links which Git considers as changes. The submodules will be marked as *dirty*. In order for `submodule_update_wo_duplicates.py` to work repeatedly it needs to overwrite these changes. This will also affect any changes made by the user. **So be warned: `submodule_update_wo_duplicates.py` will discard all changes made in all submodules (including unpushed commits), and it will reset submodules to the proper commits!**. If you need to work on multiple, dependent projects at once, either clone them separately (which is a good idea anyway), or be very careful.
* The result on a newly cloned repository should be identical to what submodule update does (i.e. if you expand all the links and compare all the files, the content should match exactly). On repeated runs the behavior regarding submodules that "disappear" might be a little different. Regular submodule update might leave the content behind. `submodule_update_wo_duplicates.py` will probably remove the untracked files.

## Tests

Run `pytest-3`, or just `pytest` if that's your name. It won't work unless you have Linux.

## Feedback

If run into some problems while using the tool, please let me know. Send me the output (the exception), some description how to reproduce it, that sort of thing. Thanks.
