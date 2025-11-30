# CONTRIBUTING.md
# Contributing to SimpleEdit
 
Thank you for contributing to SimpleEdit. This document describes the project's coding standards, configuration conventions, and a few project-level preferences contributors must follow.
 
## Guidelines

This repository follows a small set of UI and editor behavior invariants that must be preserved by all code changes. The goal is predictable editor UX and avoiding surprising global side-effects caused by syntax preset application.
- Keep changes small and focused. Open a pull request with a clear title and description.
- Add or update tests for non-trivial logic when possible.
- Preserve existing public behavior unless explicitly changing defaults; document any behavioral changes in the PR description.
- Keep UI text and error messages clear and user-friendly.
 
## Coding Standards

- Follow Python idioms consistent with the existing codebase.
- Use 4-space indentation.
- Keep functions small and focused; prefer helper functions for repeated logic.
- Preserve the project's exception-handling style (defensive, best-effort to keep UI responsive).
- Use descriptive variable and function names. Prefer `snake_case` for functions and variables and `CamelCase` for classes.
- Do not modify or remove the mandatory configuration keys unless accompanied by a migration and clear documentation.
- Always keep code style consistent with .editorconfig (when present).
- Avoid global side-effects when making per-tab visual changes. Prefer per-frame / per-widget transient state.

## Configuration and preferences
 
Project-wide runtime settings live in `config.ini` under the `Section1` header. When adding a new configurable behavior, use an explicit key under `Section1` and provide a reasonable default in the code and the `DEFAULT_CONFIG` structure.
 
New preference introduced in this change:
 
-`renderOnOpenExtensions` (Section: `Section1`)
  - Type: comma-separated string
  - Default: `html,htm,md,markdown,php,js`
  - Purpose: lists file extensions (without leading dots) that should default to the "Rendered" view when opened. Files matching these extensions and any URL-like location (http/https/file:// or `www.`) will default to rendered mode unless the user checks the "Open as source" option or the per-tab "Load as source" override.
 
Behavioral notes related to this preference:
 
- When a tab is in Rendered view (i.e. parsed HTML/MD/markup display), the standard worker-driven syntax highlighter is disabled to avoid conflicts with the rendering engine. Users can still toggle between Raw and Rendered view per-tab.
- Changes that alter the default set of extensions should update `DEFAULT_CONFIG` in `functions.py` and the settings UI so users can edit the list via the Settings dialog.
 
## Syntax highlighting policy (critical)

This project enforces a strict rule:

- Syntax highlighting MUST NEVER be applied while a tab is in Rendered view (i.e. when the tab/frame property `_view_raw` is False).

Details:

- "Rendered view" refers to the editor state where parsed HTML/Markdown has been converted to a presentational form and is being displayed. The frame attribute `_view_raw` is used in the codebase to indicate raw/source vs rendered state. When `_view_raw` is False, the tab is Rendered.

- Under no circumstance should any syntax tags (e.g. `string`, `keyword`, `comment`, `html_tag`, `html_attr`, `table`, etc.), transient preset colors, or regex-based highlighting be applied to a Text widget showing Rendered content.

- Detection (auto-detect presets) MAY run in the background for convenience, but it MUST NOT apply presets to widgets in Rendered view. If detection finds a matching preset for a rendered document, the code SHOULD store the detected preset path on the frame (for example `frame._detected_syntax_preset`) or on root for later manual application. It should NOT call functions that configure tags on the Text widget, and it should NOT mutate the global `config` via `apply_syntax_preset` while the tab is rendered.

- When a user switches a rendered tab to Raw/Source view (via toggle), any stored detected preset may be applied at that point (if the user requests it or as explicitly permitted by user-configured options). Only then may transient or persistent syntax tag configs be applied to the Text widget.

- All code paths that open content (file dialog, URL bar, hyperlink click, history/back/refresh, templates) must respect this rule. This includes both immediate application and transient application on new tab creation.

 ## Developer workflow
 
- Branch from `alpha-javascript-support` for JS/HTML related work.
- Run the app and manually test open/save flows for both local files and URLs.
- If adding a new config key, update `DEFAULT_CONFIG` in `functions.py` and add UI to `Settings` where appropriate.
 
## Implementation guidance

When making code changes refer to these concrete rules:

1. apply_syntax_preset_transient(path, text_widget) MUST return without configuring the widget if the target widget's parent frame reports `_view_raw == False`. The function may still record the detected preset on the frame for later application.

2. Any calls to `apply_syntax_preset(...)` (persistent apply to global config) MUST NOT be invoked for content that is opened in rendered mode. Instead, detected presets may be stored for later use (e.g., `frame._detected_syntax_preset`).

3. `manual_detect_syntax()` and UI-driven detection flows must respect the frame's `_view_raw` state and only apply transient/persistent presets when the frame is in Raw/Source mode.

4. `highlight_python_helper`, `safe_highlight_event`, and other highlighter entry points already short-circuit when `_view_raw` is False; ensure no other code path configures tags unconditionally.

5. If a code path currently applies transient presets when opening a URL/file in a new tab (e.g. `open_url_action`, `fetch_and_open_url`, `_open_path`), update it to either:
   - only apply transient presets when the new tab is opened in Raw/Source mode; or
   - store the detected preset on the frame (e.g. `fr._detected_syntax_preset = path`) and set a status message indicating the preset is detected but suppressed for Rendered view.

## JavaScript built-ins (interpreter guidance)

When adding built-in JavaScript objects or functions (e.g., `Array`, `Object`, `Date`) to the toy interpreter, follow these project patterns:
- Implement small, focused native implementations as Python callables or as `JSFunction` instances with a `native_impl` when constructor/`new` semantics are required.
- Attach a plain-dict `prototype` object to `JSFunction` instances and set instance `__proto__` when `new` is used. Store prototype methods as callables on the prototype dict.
- Prefer implementing prototype methods as Python callables and ensure the evaluator passes the correct `this` value when invoking methods (member calls should set `this` to the object).
- Keep behavior conservative and documented: full ECMAScript semantics are not required; implement the subset needed by the libraries you intend to run (e.g., `Array.prototype.push`, `pop`, `length` semantics; `Object.create`, `Object.keys`).
- Add small unit tests for any non-trivial native implementation and document edge-cases in the PR.

### Recommended location and structure for built-ins

For best practices keep the interpreter core (`jsmini.py`) focused on parsing and evaluation. Place built-in implementations in a separate module and register them from `make_context`:

- Create `PythonApplication1/js_builtins.py` and implement a single `register_builtins(context: Dict[str, Any])` function that attaches constructors, prototypes, and static helpers to the provided `context` dict.
- Keep `js_builtins.py` small and dependency-free. Implement each built-in as a `JSFunction` with `native_impl` or as Python callables that the interpreter can call.
- Example layout in `js_builtins.py`:
  - `def register_builtins(context):`
    - create `Arr = JSFunction(..., native_impl=_array_ctor)`
    - attach `Arr.prototype['push'] = JSFunction(..., native_impl=_array_push)`
    - set `context['Array'] = Arr`

- In `jsmini.py` `make_context()` call `from PythonApplication1.js_builtins import register_builtins` and invoke `register_builtins(context_ref)` near the end. This keeps `make_context` readable while keeping built-in logic modular.

- Tests: put unit tests under `tests/` at repo root (preferred) or under `PythonApplication1/tests/`. Example: `tests/test_js_builtins.py` with small scripts executed via `jsmini.run` and assertions of returned or logged values.

- Documentation: document registered built-ins in `CONTRIBUTING.md` (this file) and add small examples in `PythonApplication1/examples/` or `run_jsmini_demo.py`.

## Testing requirements

- Add unit or manual tests validating all open flows (File -> Open modal, native Open, Open URL dialog/toolbar, hyperlink clicks, history/back/refresh) do not apply syntax tags on tabs that end up in Rendered mode.
- Validate that when a preset has been detected for a rendered page it is only applied after switching the tab to Raw/Source view (and not before).
- create Unittest compliant testing scripts in tests, this simplifies testing of changes on multiple vectors. Use python -m unittest discover PythonApplication1/tests to execute
## Rationale

Applying syntax highlighting while the editor is showing a Rendered representation produces confusing UI: highlighting may change the visual appearance of parsed HTML, and persistent config changes can surprise users when following hyperlinks or toggling views. This rule preserves a clear separation between presentational rendering and source-mode editing.

## Style / Formatting

- Follow the project's `.editorconfig` if present (create one if missing with standard Python rules: 4-space indent, UTF-8, LF). If you add or modify `.editorconfig`, ensure it matches the expectations described in this document.
 
## Contact
 
If you're unsure about a change or need help testing, open an issue or contact the maintainers via GitHub.

## Notes for contributors

- If you modify detection or apply flows, update this document accordingly.
- When in doubt, prefer *not applying* highlighting in Rendered mode; store the detected preset for an explicit later application instead.

## Tooling

We maintain a small set of helper scripts in the repository for diagnostic and development tasks. Tools should be small, dependency-free where possible, and placed in the repository root or the `PythonApplication1` package when they import project modules.

- tokendiag.py — A minimal CLI utility to fetch a JS file (HTTP or local path) and run the project's `jsmini` tokenizer/parser diagnostics. Usage example:
  - `python -u tokendiag.py -src=http://example.com/jquery.js`
  - `python -u tokendiag.py -file=path/to/file.js --dump-tokens 215`

Tooling guidelines:
- Prefer using the project's internal diagnostic helpers (e.g., `jsmini.diagnose_parse`) so diagnostics match runtime behavior.
- Keep CLI options simple and document usage in the script header and this file.
- Avoid adding heavy third-party dependencies for small utilities; prefer `urllib.request`, `argparse`, and standard library modules.

## JavaScript built-ins (interpreter guidance)

When adding built-in JavaScript objects or functions (e.g., `Array`, `Object`, `Date`) to the toy interpreter, follow these project patterns:
- Implement small, focused native implementations as Python callables or as `JSFunction` instances with a `native_impl` when constructor/`new` semantics are required.
- Attach a plain-dict `prototype` object to `JSFunction` instances and set instance `__proto__` when `new` is used. Store prototype methods as callables on the prototype dict.
- Prefer implementing prototype methods as Python callables and ensure the evaluator passes the correct `this` value when invoking methods (member calls should set `this` to the object).
- Keep behavior conservative and documented: full ECMAScript semantics are not required; implement the subset needed by the libraries you intend to run (e.g., `Array.prototype.push`, `pop`, `length` semantics; `Object.create`, `Object.keys`).
- Add small unit tests for any non-trivial native implementation and document edge-cases in the PR.

## Tests

Add tests for non-trivial parser or interpreter behavior. When adding a new diagnostic script that becomes part of CI, include a short unit test that verifies basic operation.

## Contribution process

1. Fork the repository and create a feature branch.
2. Make small, focused commits and include tests where appropriate.
3. Ensure `flake8`/`black` (if used by the project) pass locally. Keep formatting consistent with `.editorconfig`.
4. Open a PR with a clear description of changes and rationale. Mention any user-facing behavior changes in the PR body.

---

Thank you for helping improve SimpleEdit.