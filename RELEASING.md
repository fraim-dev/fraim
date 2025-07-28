 ## Release (pypi.org)

Releases are published automatically to pypi.org for each new [release](https://github.com/fraim-dev/fraim/releases).

 To publish a new release:
 1. Update the version number in `pyproject.toml` to the release version number.
 2. Create a tag with the format `v*` and push to Github.
 3. [Draft](https://github.com/fraim-dev/fraim/releases/new) a new release at that tag.
 4. Update the version number in `pyproject.toml` to whatever the next working version number will be.

  ## Test Release (test.pypi.org)

Test releases are published automatically to test.pypi.org for each new tag with the `v*-test` format.

To publish a new test release:
 1. Create a tag with the format `v*-test` and push to GitHub.
