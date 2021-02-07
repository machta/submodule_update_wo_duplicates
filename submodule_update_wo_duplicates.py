# Prerequisites:
#   pip3 install gitpython

import subprocess, git, os


# to make the output nice and aligned
LINK_MSG   = "linking  "
UPDATE_MSG = "updating "
UNLINK_MSG = "unlinking"
CLEAR_MSG  = "clearing "


# FIXME to make it portable I need to get rid of this function
def bash(cmd, cwd=None):
    # print("+ bash:", cwd, cmd)
    return subprocess.run(["bash", "-c", cmd], #stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE, check=True, cwd=cwd).stdout.decode('utf-8')


def rm_rf(path):
    bash(f"rm -rf '{path}'")
    # FIXME use shutil.rmtree(path). But it can't remove links.


def replace_by_link(src, dst):
    print(LINK_MSG, dst, "->", src)
    rm_rf(dst)
    bash(f"ln -sr '{src}' '{dst}'")
    # FIXME use os.symlink(src, dst).
    # Figure out how to do 'relative' links (the -r switch).


def submod_git_dir(mod):
    try:
        module = mod.module()
    except:
        module = None # Don't throw if the .git dir for this module isn't available
    if module:
        d = module.git_dir
        if not os.path.exists(d):
            # For some reason it keeps giving me paths like /.git/modules/libs/...
            # Try it with a leading dot as a fallback.
            d = f".{d}"
        if os.path.exists(d):
            return d
    return None


def clear_git_dir(current_mod_path, mod, mod_path):
    git_dir = submod_git_dir(mod)
    if git_dir:
        print(CLEAR_MSG, git_dir)
        # Delete submodule as explained here: https://stackoverflow.com/a/16162000/287933
        # FIXME do the deinit w/ gitpython
        bash(f"git submodule deinit -f -- '{mod_path}'", current_mod_path)
        rm_rf(git_dir)


def find_separate_git_dir_in_exception(gce):
    for a in gce.command:
        sa = a.split("--separate-git-dir=")
        if len(sa) == 2:
            return sa[1]
    return None


def do_update(mod):
    try:
        mod.update(force=True)
    except git.exc.GitCommandError as gce:
        git_dir = find_separate_git_dir_in_exception(gce)
        if git_dir:
            # If we get 'fatal: .git/modules/... already exists', try it again after clearing the dir.
            # This is mostly an imperfection of gitpython. Normally git can overwrite the git dir without a problem.
            rm_rf(git_dir)
            mod.update(force=True)
        else:
            raise


# FIXME doesn't work if change in a direct submodule is only staged, but not committed
def update_one_level(current_mod_path = ".", cloned_mods = None):
    if not cloned_mods:
        # TODO Possible optimization: on the first level do a non-recursive update
        # on the whole repo. You will have to update all of them anyway.
        # Then just save all the hashes and URIs and you're done with the first level.
        # Doing the update in a batch will make it swifter.
        # TODO Possible optimization: If hash before and after the update doesn't change
        # for one repo, you don't have to recurse into the module at all.
        # Do this for both the update at the start and for the recursive ones after that as well.
        cloned_mods = {}
    recurse_into = []
    for mod in git.Repo(current_mod_path).submodules:
        mod_full_path = os.path.join(current_mod_path, mod.path)
        key = (mod.url, mod.hexsha)
        cloned_before = cloned_mods.get(key)
        if cloned_before:
            if not os.path.islink(mod_full_path):
                clear_git_dir(current_mod_path, mod, mod.path)
            replace_by_link(cloned_before, mod_full_path)
        else:
            if os.path.islink(mod_full_path):
                print(UNLINK_MSG, mod_full_path)
                os.unlink(mod_full_path)
            print(UPDATE_MSG, mod_full_path)
            do_update(mod)
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
