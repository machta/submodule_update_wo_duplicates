# Prerequisites:
#   pip3 install gitpython

import subprocess, git, os


# to make the output nice and aligned
LINK_MSG   = "linking    "
UPDATE_MSG = "updating   "
UNLINK_MSG = "unlinking  "
CLEAR_MSG  = "clearing   "
CHECK_MSG  = "checked out"

# export DEBUG_ENABLED=1 to enable extra debug info
def dbg_print(*args):
    if "DEBUG_ENABLED" in os.environ:
        print(*args)


# FIXME to make it portable I need to get rid of this function
def bash(cmd, cwd=None):
    # print("+ bash:", cwd, cmd)
    return subprocess.run(["bash", "-c", cmd], #stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE, check=True, cwd=cwd).stdout.decode('utf-8')


def rm_rf(path):
    bash(f"rm -rf '{path}'")
    # FIXME use shutil.rmtree(path). But it can't remove links.


def replace_by_link(src, dst):
    # If the correct link already exists, skip the rest.
    if os.path.islink(dst) and os.path.realpath(dst) == os.path.realpath(src):
        dbg_print("already linked", dst, "->", src)
        return
    print(LINK_MSG, dst, "->", src)
    rm_rf(dst)
    bash(f"ln -sr '{src}' '{dst}'")
    # FIXME use os.symlink(src, dst).
    # Figure out how to do 'relative' links (the -r switch).


def module_from_submod(submod):
    try:
        return submod.module()
    except:
        return None # Don't throw if the .git dir for this module isn't available


def submod_git_dir(submod):
    module = module_from_submod(submod)
    if module:
        d = module.git_dir
        if not os.path.exists(d):
            # For some reason it keeps giving me paths like /.git/modules/libs/...
            # Try it with a leading dot as a fallback.
            d = f".{d}"
        if os.path.exists(d):
            return d
    return None


def clear_git_dir(current_mod_path, submod, submod_path):
    git_dir = submod_git_dir(submod)
    if git_dir:
        print(CLEAR_MSG, git_dir)
        # Delete submodule as explained here: https://stackoverflow.com/a/16162000/287933
        # FIXME do the deinit w/ gitpython
        bash(f"git submodule deinit -f -- '{submod_path}'", current_mod_path)
        rm_rf(git_dir)


def find_separate_git_dir_in_exception(gce):
    for a in gce.command:
        sa = a.split("--separate-git-dir=")
        if len(sa) == 2:
            return sa[1]
    return None


def do_update(submod):
    try:
        submod.update(force=True)
    except git.exc.GitCommandError as gce:
        git_dir = find_separate_git_dir_in_exception(gce)
        dbg_print("update failed; try again after removing", git_dir)
        if git_dir:
            # If we get 'fatal: .git/modules/... already exists', try it again after clearing the dir.
            # This is mostly an imperfection of gitpython. Normally git can overwrite the git dir without a problem.
            rm_rf(git_dir)
            submod.update(force=True)
        else:
            raise


def checked_out_sha(submod, module=None):
    if not module:
        module = module_from_submod(submod)
    if module:
        return module.commit().hexsha
    else:
        return None


def get_staged_files(index):
    return [ item.a_path for item in index.diff("HEAD") ]


def update_one_level(current_mod_path = ".", cloned_mods = None):
    dbg_print(f"entering update_one_level('{current_mod_path}')")
    repo = git.Repo(current_mod_path)
    index = None
    if not cloned_mods:
        # Special case for the first level recursion (i.e. the root repo)
        index = repo.index
        cloned_mods = {}
    recurse_into = []
    for submod in repo.submodules:
        mod_full_path = os.path.join(current_mod_path, submod.path)
        hexsha = submod.hexsha
        if index and submod.path in get_staged_files(index):
            # If submodule is staged, we use the currently checked out commit instead.
            hexsha = checked_out_sha(submod) or hexsha
        key = (submod.url, hexsha)
        cloned_before = cloned_mods.get(key)
        if cloned_before:
            if not os.path.islink(mod_full_path):
                clear_git_dir(current_mod_path, submod, submod.path)
            replace_by_link(cloned_before, mod_full_path)
        else:
            if os.path.islink(mod_full_path):
                print(UNLINK_MSG, mod_full_path)
                os.unlink(mod_full_path)
            submod_repo = module_from_submod(submod)
            # Do update only if we don't already have the right commit. Saves CPU time & network load.
            if key[1] != checked_out_sha(submod, submod_repo):
                try:
                    # Also try first checking out the commit.
                    submod_repo.head.reset(commit=key[1], index=True, working_tree=True)
                    print(CHECK_MSG, mod_full_path)
                except: # Update will be used as backup, if repo is empty, or checkout fails.
                    print(UPDATE_MSG, mod_full_path)
                    do_update(submod)
            cloned_mods[key] = mod_full_path
            recurse_into.append(mod_full_path)
    for current_mod_path in recurse_into:
        update_one_level(current_mod_path, cloned_mods)


if __name__ == "__main__":
    update_one_level()


# update() doc:
# https://github.com/gitpython-developers/GitPython/blob/24f75e7bae3974746f29aaecf6de011af79a675d/git/objects/submodule/base.py#L444

# git submodule status --recursive | awk '{print $2}' > /tmp/submod.list
# cat /tmp/submod.list | xargs realpath 2>/dev/null | sort | uniq
# du -hcd1 .
