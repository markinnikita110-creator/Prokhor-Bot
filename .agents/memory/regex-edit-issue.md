---
name: Regex truncation in Edit tool
description: Backslash sequences like \d, \w in regex patterns get silently truncated when used inside Edit old_string/new_string parameters, corrupting the file.
---

## Rule
Never use the `Edit` tool to insert or modify Python code that contains regex patterns with backslash sequences (e.g. `\d`, `\w`, `\s`, `\d+`, `\d{1,2}`). Use `WriteFile` instead for any file that needs such changes.

**Why:** The Edit tool JSON-encodes its parameters, and `\d` is not a valid JSON escape — the parser silently drops everything after the invalid sequence, producing a truncated string literal in the file. This causes a SyntaxError at startup that is invisible until py_compile or runtime.

**How to apply:**
- If a file needs a regex pattern inserted or changed → use `WriteFile` for the full file.
- For callback_query state-filtered handlers that match `tz_set_<int>`, prefer `F.data.func(lambda d: d.startswith("tz_set_"))` over `F.data.regexp(...)` as an additional guard — it avoids regex in decorator arguments entirely.
- Always run `python -m py_compile <file>` after writing any file with regex content to catch truncation early.
