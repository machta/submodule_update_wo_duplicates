import unittest, sys, os
import tempfile

import repo_diff

sys.path.append(os.path.abspath(__file__ + "/../.."))
from submodule_update_wo_duplicates import bash, update_one_level

def git_commit(repo, commit):
    bash("git add -A", repo)
    bash(f"git commit -m {commit}", repo)
    bash(f"git tag {commit}", repo)

def init_repo(repo):
    bash(f"git init {repo}")
    bash(f"echo 'repo {repo}' > file", repo)
    git_commit(repo, "c1")
    bash(f"echo 'repo {repo}' > file2", repo)
    git_commit(repo, "c2")

def add_submod(repo, sub_path, submod):
    bash(f"git submodule add {os.path.abspath(submod)} {sub_path}", repo)
    git_commit(repo, f"add-{submod}")

def make_3_repos():
    init_repo("git1")
    init_repo("git2")
    init_repo("git3")

    add_submod("git2", "libs/git3", "git3")
    add_submod("git1", "libs/git3", "git3")
    add_submod("git1", "libs/git2", "git2")


def call_update(repo):
    os.chdir(repo)
    update_one_level()
    os.chdir("..")


class TestBasic(unittest.TestCase):

    def setUp(self):
        self.tmpdiro = tempfile.TemporaryDirectory()
        self.tmpdir = self.tmpdiro.name
        # unlike TemporaryDirectory() doesn't remove the dir in dtor
        # self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

        make_3_repos()

        print()
        print("========================================>")
        print()

    def tearDown(self):
        print()
        print("<========================================")
        print()
        print(bash(f"tree {self.tmpdir}"))
        pass


    def test_basic_wo_modules(self):
        bash(f"git clone {os.path.abspath('git1')} clone_git1")

        bash(f"git checkout c2", "clone_git1")
        call_update("clone_git1")

        linked_content = repo_diff.repo_content("clone_git1")
        expected_content = repo_diff.clean_clone_content("git1", "c2")
        self.assertEqual(linked_content, expected_content)


    def test_basic_w_modules(self):
        bash(f"git clone {os.path.abspath('git1')} clone_git1")

        bash(f"git checkout add-git2", "clone_git1")
        call_update("clone_git1")

        linked_content = repo_diff.repo_content("clone_git1")
        expected_content = repo_diff.clean_clone_content("git1", "add-git2")
        self.assertEqual(linked_content, expected_content)


    """
    Tests that if a previously linked repo can be turned into a real module again.
    This requires force for update() because the link made previously makes the repo 'dirty'.
    """
    def test_submod_downgrade(self):
        bash(f"git checkout c1", "git2/libs/git3")
        git_commit("git2", "downgrade-git3")

        bash(f"git fetch", "git1/libs/git2")
        bash(f"git checkout downgrade-git3", "git1/libs/git2")
        git_commit("git1", "downgrade-git3")

        bash(f"git clone {os.path.abspath('git1')} clone_git1")

        bash(f"git checkout add-git2", "clone_git1")
        call_update("clone_git1")
        bash(f"git checkout downgrade-git3", "clone_git1")
        call_update("clone_git1")

        linked_content = repo_diff.repo_content("clone_git1")
        expected_content = repo_diff.clean_clone_content("git1", "downgrade-git3")
        self.assertEqual(linked_content, expected_content)


    """
    The same as test_submod_downgrade but adds an extra step that goes back to the
    state when the repo is linked again.
    """
    def test_submod_link_update_link(self):
        bash(f"git checkout c1", "git2/libs/git3")
        git_commit("git2", "downgrade-git3")

        bash(f"git fetch", "git1/libs/git2")
        bash(f"git checkout downgrade-git3", "git1/libs/git2")
        git_commit("git1", "downgrade-git3")

        bash(f"git clone {os.path.abspath('git1')} clone_git1")

        bash(f"git checkout add-git2", "clone_git1")
        call_update("clone_git1")
        bash(f"git checkout downgrade-git3", "clone_git1")
        call_update("clone_git1")
        bash(f"git checkout add-git2", "clone_git1")
        call_update("clone_git1")

        linked_content = repo_diff.repo_content("clone_git1")
        expected_content = repo_diff.clean_clone_content("git1", "add-git2")
        self.assertEqual(linked_content, expected_content)


    """
    Tests that a cloned repo, subsequently replaced by a link, can be cloned again.
    This makes update() fail when the submod 'already exists' in .git/modules directory.

    This used to be a bug on an early version of this tool. An extra step is necessary
    when unlinking to make sure the appropriate directory in .git/modules is cleaned as well.
    """
    def test_submod_update_link_update(self):
        bash(f"git checkout c1", "git2/libs/git3")
        git_commit("git2", "downgrade-git3")

        bash(f"git fetch", "git1/libs/git2")
        bash(f"git checkout downgrade-git3", "git1/libs/git2")
        git_commit("git1", "downgrade-git3")

        bash(f"git clone {os.path.abspath('git1')} clone_git1")

        bash(f"git checkout downgrade-git3", "clone_git1")
        call_update("clone_git1")
        bash(f"git checkout add-git2", "clone_git1")
        call_update("clone_git1")
        bash(f"git checkout downgrade-git3", "clone_git1")
        call_update("clone_git1")

        linked_content = repo_diff.repo_content("clone_git1")
        expected_content = repo_diff.clean_clone_content("git1", "downgrade-git3")
        self.assertEqual(linked_content, expected_content)


if __name__ == '__main__':
    unittest.main()
