"""Remove stale PR branches."""

from .common import CURRENT_REF, api

if __name__ == "__main__":
    stale_branches = api.git.list_matching_refs(f"heads/{ CURRENT_REF }-auto-pr-")
    for branch in stale_branches:
        ref = branch.ref.split("/", 1)[-1]
        print("Deleting", ref)
        api.git.delete_ref(ref)
