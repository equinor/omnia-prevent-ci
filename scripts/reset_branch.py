"""Push the selected branch to a branch provided in input This will replace reset_dev_branch."""
import argparse

from ghapi.actions import context_github

from scripts.common import api


def _reset_branch(name: str):
    print(api.git.update_ref(f"heads/{name}", sha=context_github.sha, force=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--branch-name", help="Name of the branch to reset", required=True)

    args = parser.parse_args()
    branch_name = args.branch_name

    _reset_branch(branch_name)
