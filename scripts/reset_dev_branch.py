"""Push the selected branch to `deploy/dev` branch."""

from ghapi.actions import context_github

from scripts.common import api

print(api.git.update_ref("heads/deploy/dev", sha=context_github.sha, force=True))
