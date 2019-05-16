# Contributing to IndexTools

We welcome contributions of bug reports, feature requests, code, and documentation from the community.

* All code and documentation contributions must be via pull request.
* By submitting a pull request, you agree to donate your contribution under the terms of this project's [license](https://github.com/dnanexus/IndexTools/LICENSE).

## Conventions

* Format code according to [black](https://github.com/python/black) style.
* Use type annotations in all function signatures and anywhere else they are necessary to resolve ambiguity.
* Write [Google-style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) docstrings for all functions.
* Write [self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code), commenting where necessary to explain complex functionality.

## Process

IndexTools development follows the [GitFlow](https://nvie.com/posts/a-successful-git-branching-model) development process. In summary:

* Fork the repository
* Change to the `develop` branch: `git checkout develop`
* Create a new feature branch: `git checkout -b <feature name>`
    * If the feature is based on an issue, prefix the branch name with the issue ID, e.g. `git checkout -b 4_cram_support`.
* Commit your changes. We suggest making small, focused commits with informative messages"
* Write tests for any new or modified functionality.
* When all tests pass, submit a PR with a detailed message.
    * The [code owner(s)](https://github.com/dnanexus/IndexTools/CODEOWNERS) will automatically be added as reviewers on the PR.

## Collaborators

Any contributor who has previously made a pull request to this project may apply to become a Collaborator by submitting an issue to this effect.

The development process for Contributors and Collaborators is the same, with the exception that:

* Collaborators can create branches and submit PRs directly on this project, rather than via forking, and
* Collaborators are considered as "Authors," both for purposes of copyright and for inclusion on any manuscript submitted for publication.

Your first PR after being added as a Collaborator should be to add yourself to the [authors](https://github.com/dnanexus/IndexTools/AUTHORS.md) file.