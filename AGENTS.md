# Project rules

## Privacy is a release requirement

- Treat every tracked file and every commit as potentially public, regardless of repository visibility.
- Never put a person's real name, personal email, phone number, address, account identifier, home-directory path, machine name, device serial number, network name, IP address, MAC address, credentials, tokens, cookies, or private URLs in source, documentation, fixtures, screenshots, commit messages, or release artifacts.
- Use neutral examples and reserved example domains. Generic product names and MIDI note/controller values are fine. Loopback hosts (`localhost`, `127.0.0.1`, `::1`) are portable development defaults, not private network information.
- Keep authentication in external credential stores. Never embed credentials in remotes or URLs. Never print secrets while diagnosing a problem.
- Keep local configuration, raw MIDI captures, logs, session history, screenshots and recordings untracked. `.gitignore` is defense in depth; it does not remove already-tracked files or Git history.
- Only publish calibration fixtures deliberately approved for sharing; remove identifying metadata first. Use synthetic fixtures for routine tests.
- Do not add analytics, telemetry, cloud services or outbound runtime calls. Discover MIDI ports at runtime; do not hard-code a person's port names or network setup.
- Do not write personal information into public files while explaining that it was removed. Scanner reports must identify the rule/location without printing matched secrets.

## A fresh clone must work

- Follow the relative-path setup in README.md. Do not depend on the original developer's filesystem, shell configuration, installed credentials, private package registries or existing local state.
- Keep dependency manifests and the frontend lockfile tracked. Keep virtual environments, dependencies, caches and generated builds untracked.
- Preserve loopback-only local servers. Any future configurable endpoints need neutral defaults and ignored local overrides.
- Document prerequisites and limitations honestly. Distinguish automated tests from user-reported and directly observed hardware verification.
- Keep the prototype scope in README.md; privacy work does not authorize unrelated features.

## Before committing or publishing

1. Inspect the exact staged file list and diff, including new files, documentation and generated artifacts.
2. Run `python3 scripts/check_privacy.py` on the staged snapshot. Fix every finding; do not weaken checks or add broad exceptions to get a commit through.
3. Use a neutral project author or a contributor-chosen public alias and privacy-safe noreply email. Never inherit a personal email silently. Do not change global Git identity.
4. Run `python3 scripts/check_privacy.py --history` before a push. Review commit messages and authors as well as file content.
5. Run checks appropriate to code changes and verify setup from a clean checkout when changing dependencies or setup instructions.
6. If a secret was ever published, stop publishing, revoke/rotate it and coordinate history cleanup. Deleting the latest copy is insufficient. Never rewrite shared history without authorization.

Install the repository hooks with `git config --local core.hooksPath .githooks`. Hooks can be bypassed and automated detectors cannot recognize every name or sensitive fact: manual review remains required. Do not claim a guarantee that no future leak is possible.
