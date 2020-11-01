#!/usr/bin/env python3

from __future__ import print_function
import click
import datetime
import os
import shlex
import subprocess
import sys
import time
from urllib.parse import urlparse

import typer


def sh(*args, **kwargs):
    """ Get subprocess output"""
    return subprocess.check_output(*args, **kwargs).decode().strip()


def get_repo_at(dest):
    if not os.path.exists(os.path.join(dest, ".git")):
        raise ValueError("No repo found at {dest}".format(**locals))

    current_remote = sh(shlex.split("git config --get remote.origin.url"), cwd=dest)

    current_branch = sh(shlex.split("git rev-parse --abbrev-ref HEAD"), cwd=dest)

    return current_remote.lower(), current_branch.lower()


def setup_repo(repo, dest, branch, force):
    """
    Clones `branch` of remote `repo` to `dest`, if it doesn't exist already.
    Raises an error if a different repo or branch is found.
    """
    dest = os.path.expanduser(dest)

    repo_name = urlparse(repo).path

    # if no git repo exists at dest, clone the requested repo
    if not os.path.exists(os.path.join(dest, ".git")):
        output = sh(["git", "clone", "--no-checkout", "-b", branch, repo, dest])
        typer.echo("Cloned ...{repo_name}".format(**locals()))

    else:
        # if there is a repo, make sure it's the right one
        current_remote, current_branch = get_repo_at(dest)
        repo = repo.lower()
        if not repo.endswith(".git"):
            repo += ".git"
        if not current_remote.endswith(".git"):
            current_remote += ".git"
        parsed_remote = urlparse(current_remote)
        parsed_repo = urlparse(repo)

        if (
            parsed_repo.netloc != parsed_remote.netloc
            or parsed_repo.path != parsed_remote.path
        ):
            raise ValueError(
                "Requested repo `...{repo_name}` but destination already "
                "has a remote repo cloned: {current_remote}".format(**locals())
            )

        # and check that the branches match as well
        if branch.lower() != current_branch:
            raise ValueError(
                "Requested branch `{branch}` but destination is "
                "already on branch `{current_branch}`".format(**locals())
            )

        # and check that we aren't going to overwrite any changes!
        # modified_status: uncommited modifications
        # ahead_status: commited but not pushed
        modified_status = sh(shlex.split("git status -s"), cwd=dest)
        ahead_status = sh(shlex.split("git status -sb"), cwd=dest)[3:]

        # stash changes if force syncing
        if force:
            sh(["git", "stash", "--all"], cwd=dest)
            typer.echo(f"All chanes from {current_branch} stashed!")
        else:
            if modified_status:
                raise ValueError(
                    "There are uncommitted changes at {dest} that syncing "
                    "would overwrite".format(**locals())
                )
            if "[ahead " in ahead_status:
                raise ValueError(
                    "This branch is ahead of the requested repo and syncing would "
                    "overwrite the changes: {ahead_status}".format(**locals())
                )


def sync_repo(repo, dest, branch, rev):
    """
    Syncs `branch` of remote `repo` (at `rev`) to `dest`.
    Assumes `dest` has already been cloned.
    """
    # fetch branch
    output = sh(["git", "fetch", "origin", branch], cwd=dest)
    click.echo("Fetched {branch}: {output}".format(**locals()))

    # reset working copy
    if not rev:
        output = sh(["git", "reset", "--hard", "origin/" + branch], cwd=dest)
    else:
        output = sh(["git", "reset", "--hard", rev], cwd=dest)

    # clean untracked files
    sh(["git", "clean", "-dfq"], cwd=dest)

    typer.echo("Reset to {rev}: {output}".format(**locals()))

    repo_name = urlparse(repo).path
    typer.echo(
        "Finished syncing {repo_name}:{branch} at {t:%Y-%m-%d %H:%M:%S}".format(
            **locals(), t=datetime.datetime.now()
        )
    )


def main(
    dest: str = typer.Argument(
        os.getcwd(),
        envvar="GIT_SYNC_DEST",
        help="The destination path. Defaults to the current working directory.",
    ),
    wait: int = typer.Option(
        60,
        envvar="GIT_SYNC_WAIT",
        help="The number of seconds to pause after each sync. Defaults to 60.",
    ),
    repo: str = typer.Option(
        "",
        envvar="GIT_SYNC_REPO",
        help="The url of the remote repo to sync. Defaults to inferring from `dest`.",
    ),
    branch: str = typer.Option(
        "",
        envvar="GIT_SYNC_BRANCH",
        help="The branch to sync. Defaults to inferring from `repo` (if already cloned), otherwise defaults to master.",
    ),
    force: bool = typer.Option(
        False,
        envvar="GIT_SYNC_FORCE",
        help="Sync changes forcefully, stashes all the changes first.",
    ),
    rev: str = typer.Option(
        None, envvar="GIT_SYNC_REV", help="The revision to sync. Defaults to HEAD."
    ),
    run_once: bool = typer.Option(
        False,
        envvar="GIT_SYNC_RUN_ONCE",
        help="Run only once (don't loop). Defaults to off (false).",
    ),
    debug: bool = typer.Option(
        False, envvar="GIT_SYNC_DEBUG", help="Print tracebacks on error."
    ),
):
    """
    Periodically syncs a remote git repository to a local directory. The sync
    is one-way; any local changes will be lost.
    """

    if not debug:
        sys.excepthook = lambda etype, e, tb: print("{}: {}".format(etype.__name__, e))

    # infer repo/branch
    if not repo and not branch:
        repo, branch = get_repo_at(dest)
    elif not repo:
        repo, _ = get_repo_at(dest)
    elif not branch:
        branch = "master"

    setup_repo(repo, dest, branch, force)
    while True:
        sync_repo(repo, dest, branch, rev)
        if run_once:
            break
        click.echo("Waiting {wait} seconds...".format(**locals()))
        time.sleep(wait)


if __name__ == "__main__":
    typer.run(main)
