"""Check if the deployment is required and if it is safe.

Exits with code 1 if the changes are supposed to be deployed but
some conflicting deployment already exists.

Sets following outputs:

- confirm - `true` if deployment is needed.
- note_raw - the PR title for PRs, or the last commit message
  for other events.
- note_clean - the same as note_raw, but clean for using as a bash
  command input.
"""
import re
import shlex
from textwrap import dedent

from ghapi.all import actions_error, actions_output, context_github, set_git_user

from scripts.common import (
    BOT_EMAILS,
    CURRENT_REF,
    DEPLOY_DEV_BRANCH,
    MAIN_BRANCH_NAME,
    api,
    get_current_commit,
    get_last_commit,
)

RELEASE_PATTERN = re.compile(r"v[0-9]+(\.[0-9]+)*([a-z]+[0-9]+)?")
AUX_PR_PATTERN = re.compile(r"[0-9\s]*Aux:.*", re.IGNORECASE)
AUTO_PR_PATTERN = re.compile("Automatically set version .* of image .* in kustomization.yaml.*")


def get_deploy_note(commit=None):
    """Return a deploy note of current action.

    The note is a PR title for pull_request action,
    and the head commit message for other ones.
    """
    if context_github.event_name == "pull_request" and not commit:
        title = _extract_title(context_github.event.pull_request.title)
        pr_links = context_github.event.pull_request["_links"]
        return f"PR: { title } { pr_links.html.href }"

    if not commit:
        commit = get_current_commit()

    title = _extract_title(commit.message)
    return f"Commit: { title } { commit.get('html_url', commit.url) }"


def _extract_title(text):
    return text.split(r"\n", 1)[0].split(r"\r", 1)[0].splitlines()[0]


def check_deploy_required() -> bool:
    """Return True if a deploy is required for current step."""
    if context_github.event_name == "release" and not RELEASE_PATTERN.match(context_github.event.release.tag_name):
        print("Non-version tag, skipping the release.")
        return False

    if context_github.event_name != "pull_request":
        print("Not a PR, enable the release.")
        return True

    if context_github.event.pull_request.draft:
        print("Skip release for a draft PR.")
        return False

    if AUX_PR_PATTERN.match(context_github.event.pull_request.title):
        print("Skip release for a PR prefixed with `Aux:`.")
        return False

    is_human_commit = _is_human_commit()
    if not is_human_commit:
        print("Skipping the release for a commit created by a bot.")
    return is_human_commit


def _is_human_commit():
    """Check if the commit made is not autogenerated by CI.

    Checking either the current commit, or the commit
    merged into current one.
    """
    cur_commit = get_current_commit()

    if len(cur_commit.parents.items) > 1:
        # It's a merge commit, check the parents
        commits = [api.git.get_commit(c.sha) for c in cur_commit.parents.items]
    else:
        commits = [cur_commit]

    for commit in commits:
        if commit.committer.email in BOT_EMAILS and AUTO_PR_PATTERN.match(commit.message):
            return False

    return True


def check_safe_to_deploy() -> bool:
    """Ensure there are no conflicts with existing dev deploy."""
    if context_github.event_name != "pull_request":
        print("Not a PR, assume it is safe to deploy.")
        return True

    if _is_branch_directly_deployed():
        return True

    last_deploy_commit = get_last_commit(DEPLOY_DEV_BRANCH)
    last_main_commit = get_last_commit(MAIN_BRANCH_NAME)

    for name, commit in (("HEAD", None), (MAIN_BRANCH_NAME, last_main_commit)):
        if last_deploy_commit.committer.email not in BOT_EMAILS:
            continue

        if last_deploy_commit.message.endswith(get_deploy_note(commit)):
            print(f"The deploy seems to be based on { name }.  Allow to override.")
            return True

    return False


def _is_branch_directly_deployed():
    """Check if either current or main branch is set to deploy/dev."""
    for branch in (MAIN_BRANCH_NAME, context_github.head_ref):
        if api.repos.compare_commits(branch, DEPLOY_DEV_BRANCH).status == "identical":
            print(f"{DEPLOY_DEV_BRANCH} is identical to { branch }, allow to override.")
            return True


if __name__ == "__main__":
    set_git_user()

    _deploy_note = get_deploy_note()

    actions_output("note_raw", _deploy_note)
    actions_output("note_clean", shlex.quote(_deploy_note))

    _is_deploy_required = check_deploy_required()
    actions_output("confirm", str(_is_deploy_required).lower())

    if _is_deploy_required and not check_safe_to_deploy():
        actions_error(
            dedent(
                f"""
                The branch "{DEPLOY_DEV_BRANCH}" is not a direct accessor of "{CURRENT_REF}".
                Make sure the conflicting PRs are merged and re-run this job.
                If it did not help, try resetting the {DEPLOY_DEV_BRANCH} branch with
                "Reset deploy/dev branch" action:
                { context_github.event.repository.html_url }/actions/workflows/reset-dev-deploy-branch.yml
                """
            )
        )
        exit(1)