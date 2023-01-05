"""Common code for Python CI scripts."""
from ghapi.actions import context_github, github_token, user_repo
from ghapi.core import GhApi

DEPLOY_DEV_BRANCH = "deploy/dev"
BOT_EMAILS = ("github-actions[bot]@users.noreply.github.com", "noreply@github.com")
CURRENT_REF = context_github.head_ref or context_github.ref.rsplit("/", 1)[-1]
MAIN_BRANCH_NAME = context_github.event.repository.default_branch
api = GhApi(*user_repo(), token=github_token())


def get_current_commit():
    """Provide a current commit object for a GitHub event."""
    if context_github.event_name == "push":
        return context_github.event.head_commit

    return api.git.get_commit(context_github.sha)


def get_last_commit(branch_name):
    """Get the last commit of given branch."""
    branch = api.git.get_ref(f"heads/{ branch_name }")
    return api.git.get_commit(branch.object.sha)
