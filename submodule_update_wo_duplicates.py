# Prerequisites:
#   pip3 install gitpython

import subprocess, git, os


def bash(cmd, cwd=None):
    # print("+ bash:", cwd, cmd)
    return subprocess.run(["bash", "-c", cmd], #stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE, check=True, cwd=cwd).stdout.decode('utf-8')

# to make the output nice and aligned
LINK_MSG   = "linking  "
UPDATE_MSG = "updating "
UNLINK_MSG = "unlinking"

def replace_by_link(src, dst):
    print(LINK_MSG, dst, "->", src)
    bash(f"rm -rf '{dst}'")
    # shutil.rmtree(dst) # can't remove links
    bash(f"ln -sr '{src}' '{dst}'")
    # os.symlink(src, dst) # can't do relative links (the -r switch)

# FIXME doesn't work if change in a direct submodule is only staged, but not committed
def update_one_level(mod = ".", cloned_mods = None):
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
    for m in git.Repo(mod).submodules:
        m_path = os.path.join(mod, m.path)
        key = (m.url, m.hexsha)
        cloned_before = cloned_mods.get(key)
        if cloned_before:
            replace_by_link(cloned_before, m_path)
        else:
            if os.path.islink(m_path):
                print(UNLINK_MSG, m_path)
                os.unlink(m_path)
            print(UPDATE_MSG, m_path)
            m.update(force=True)
            cloned_mods[key] = m_path
            recurse_into.append(m_path)
    for m in recurse_into:
        update_one_level(m, cloned_mods)


if __name__ == "__main__":
    update_one_level()

# update() doc:
# https://github.com/gitpython-developers/GitPython/blob/24f75e7bae3974746f29aaecf6de011af79a675d/git/objects/submodule/base.py#L444

# git submodule status --recursive | awk '{print $2}' > /tmp/submod.list
# cat /tmp/submod.list | xargs realpath 2>/dev/null | sort | uniq
# du -hcd1 .
