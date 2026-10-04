# Paired releases

Python and Node.js have one shared version, one root changelog, and one GitHub Release.
Every release publishes both packages, including changes that only affect one implementation.
CI checks both manifests and both lockfiles for version drift.

## Local validation before publishing

Run these commands from the repository root:

```bash
uv sync --project packages/python --group dev
npm ci --prefix packages/nodejs
make check
make test
make build
npm exec --yes --package=./dist/nodejs/radajakub-clankers-3.0.0.tgz -- clankers --version
```

They build and validate both packages without publishing. The npm build installs the actual
archive into a temporary project and checks its CLI, CommonJS/ESM imports, and declarations.
Use the version you built in the archive filename. Archive paths are relative to the current
directory; from `packages/nodejs`, use `../../dist/nodejs/` instead of `./dist/nodejs/`.
See the [Node.js guide](../packages/nodejs/README.md#development-and-releases) to test a notification.

## One-time setup

Keep the existing PyPI trusted publisher:

- Owner: `radajakub`
- Repository: `clankers`
- Workflow: `publish.yml`
- Environment: `pypi`

Create a GitHub environment named `npm`. Verify that your npm account owns the `radajakub`
scope before publishing `@radajakub/clankers`.

npm Trusted Publishing is configured in an existing package's settings. Bootstrap the npm
package once at the current shared version, matching the Python release. After local validation,
the root `dist/nodejs/` directory should contain one archive:

```bash
npm login
npm whoami # Must report radajakub
npm publish dist/nodejs/*.tgz --access public --ignore-scripts
```

Run local validation first, then run these commands from the repository root when ready to publish.
The bootstrap publish fills in the npm counterpart to the Python release; future releases are paired.
If a GitHub Release has already failed at npm publication, use its uploaded `nodejs-dist` artifact
as described below instead of rebuilding the archive.

After bootstrapping, configure the npm package's trusted publisher:

- GitHub owner: `radajakub`
- Repository: `clankers`
- Workflow filename: `publish.yml`
- Environment: `npm`
- Allow direct `npm publish`

Open the npm package page, select **Settings**, find **Trusted Publisher**, and choose
**GitHub Actions**. Enter only `publish.yml`, without `.github/workflows/`, in the workflow field.
The environment must match the job's `environment: npm`. Save the configuration before retrying.
No GitHub `NPM_TOKEN` secret is needed for this workflow. A local `npm login` does not authorize
a GitHub Actions runner.

The npm publish job uses a GitHub-hosted runner, Node.js 24, npm 11.19.1, and `id-token: write`.
It needs no stored npm publish token. Public packages from public repositories receive automatic
provenance with Trusted Publishing. See [npm Trusted Publishing](https://docs.npmjs.com/trusted-publishers/).

## Cutting a release

1. Describe changes under `## [Unreleased]` in the root `CHANGELOG.md`.
2. Commit the implementation and ensure `master` is clean and synchronized with origin.
3. Run `make release-dry-run VERSION=3.1.0` to inspect the steps.
4. Run `make release VERSION=3.1.0` when ready to commit, push, and publish.

Use a stable `X.Y.Z` version greater than the current shared version. Prereleases are not yet
supported by the paired release tool. It checks both existing versions and lockfiles, runs checks
and tests, bumps both versions and lockfiles, builds both packages, updates the changelog, then
commits, tags, pushes, and creates the GitHub Release. A failure before committing leaves local
changes for inspection; it does not reset the working tree.

The dry run does not bump, build, commit, tag, push, or publish. Its repository preflight still
fetches origin to check that local `master` is synchronized.

The release event runs `.github/workflows/publish.yml`. Neither registry publish job starts
until both packages pass validation and their artifacts are uploaded. The npm archive is tested
as an installed package before publication. The PyPI workflow filename is preserved so its
existing trusted publisher remains valid.

## Recovering a partially published release

Publishing to two registries is not atomic. One may succeed while the other fails.
Fix the external configuration issue and rerun the failed publish job for the same release;
do not bump one package or create another tag to repair it.

For a first npm publication that failed because the package and its trusted publisher do not yet
exist, download the original archive from the failed run's **Artifacts** section (`nodejs-dist`).
You can also download it with the GitHub CLI, replacing `RUN_ID` with that run's numeric ID:

```bash
gh run download RUN_ID --repo radajakub/clankers --name nodejs-dist --dir /tmp/clankers-npm-recovery
npm login
npm whoami # Must report radajakub
npm publish /tmp/clankers-npm-recovery/*.tgz --access public --ignore-scripts
```

Use an empty download directory. The `npm publish` command publishes the release artifact for real.
Then configure the trusted publisher in npm settings and use **Re-run failed jobs** on the original
GitHub run. The npm job recognizes the identical manually published archive and skips it. Future
releases authenticate through OIDC.

PyPI skips distributions that already exist. npm checks an existing version's SHA-512 archive
integrity and skips it only if the uploaded archive matches exactly. A different archive fails
rather than silently accepting a mismatched release. Prefer rerunning publish jobs with the
original uploaded artifacts; artifact retention is finite, so repair failures promptly.

A failed network or authentication check does not count as an absent npm version.
