import tempfile, os, sys
import subprocess

def bash(cmd, cwd=None):
    # print("+ bash:", cwd, cmd)
    return subprocess.run(["bash", "-c", cmd], #stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE, check=True, cwd=cwd).stdout # returns binary


def repo_content(path):
    return bash("find -L -type f | grep -v '\\.git' | sort | xargs tail -n 1000", path)


def clean_clone_content(repo, rev):
    with tempfile.TemporaryDirectory() as tmpdir:
        bash(f"git clone {os.path.abspath('git1')} {tmpdir}")
        bash(f"git checkout {rev}", tmpdir)
        bash(f"git submodule update --init --recursive --jobs 4", tmpdir)
        content = repo_content(tmpdir)
        return content


def repo_diff(path_a, path_b):
    a_content = repo_content(path_a)
    b_content = repo_content(path_b)

    if a_content != b_content:
        with open("a.diff", "wb") as a_file, open("b.diff", "wb") as b_file:
            a_file.write(a_content)
            b_file.write(b_content)
        bash("diff a.diff b.diff > ab.diff ; /bin/true")
        diff_lines = bash("wc -l ab.diff").decode("ASCII").strip()
        print("Repos differ: ", diff_lines, "lines don't match")
        print("   check the files: a.diff, b.diff & ab.diff")
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 repo_diff.py repo1 repo2")
        exit(1)
    exit(not repo_diff(sys.argv[1], sys.argv[2]))


# git submodule foreach --recursive git clean -ffd
