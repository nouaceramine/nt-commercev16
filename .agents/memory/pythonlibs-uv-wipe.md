---
name: Python env (.pythonlibs) uv-wipe hazard
description: How a uv-based package install can wipe the backend Python env in this repl, and how to recover.
---

# .pythonlibs uv-wipe hazard

This repl's backend Python deps live in `.pythonlibs` (driven by `PYTHONUSERBASE=.pythonlibs`; original installs were `pip install --user`). The env also sets `UV_PROJECT_ENVIRONMENT=.pythonlibs` and `UV_PYTHON_PREFERENCE=only-system`.

**Hazard:** a uv-based package install (e.g. the platform packager running `uv init` + `uv add`) creates a root `pyproject.toml` with `dependencies = []`. Because `UV_PROJECT_ENVIRONMENT` points at `.pythonlibs`, `uv sync` then **deletes every package in `.pythonlibs`** to match the empty deps list, and the subsequent add can crash (it tried to write into the read-only nix-store python), leaving `.pythonlibs` completely empty. The running backend keeps serving only because its process already imported modules into memory — it dies on next restart.

**Recovery that worked:**
1. `rm -f main.py pyproject.toml uv.lock .python-version` at repo root (revert the uv project pollution; none existed before).
2. Reinstall with `pip install --user -r backend/requirements.txt` (lands in `.pythonlibs` via `PYTHONUSERBASE`). Run it backgrounded — ~150 pkgs exceeds the 2-min bash timeout.
3. Restart the `Backend API` workflow.

**Why:** prefer plain `pip --user` here over the uv packager — uv is misconfigured for this env and destroys `.pythonlibs`.

**Unintallable deps to keep OUT of requirements.txt:** `emergentintegrations` (private index, never pip-installable; all code already imports it inside try/except) and `litellm` (firewall 403 block, only a transitive dep of emergentintegrations, not imported in code). Both were removed after the AI service was rewired to AsyncOpenAI.
