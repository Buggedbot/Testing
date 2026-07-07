"""Build a runbook-generation prompt from a setup script or pipeline file.
See README.md in this folder for the use case.
"""

from __future__ import annotations

_INSTRUCTIONS = """\
Write a runbook titled "{title}" for the script/config below, aimed at an
engineer new to this team following it for the first time.

Structure:
1. Purpose -- two sentences on what this sets up/runs and when it's needed.
2. Prerequisites -- tools, access, credentials, and versions the script
   assumes (including ones it uses without checking).
3. Steps -- numbered; for each: what to run, WHY it exists, and what success
   looks like (expected output / state to verify).
4. Troubleshooting table -- symptom | likely cause | fix, for the failures
   each step could realistically produce.
5. Hidden assumptions -- everything the script depends on but never
   validates (network access, magic env vars, pre-seeded data). Be thorough
   here; this section replaces tribal knowledge.

Document what the script actually does. If a step looks wrong or risky, add
a "⚠ verify with the team" note rather than silently correcting it.
"""


def build_prompt(script_text: str, title: str) -> str:
    return "\n\n".join(
        [
            _INSTRUCTIONS.format(title=title),
            "## Script / config\n\n```\n" + script_text.strip() + "\n```",
        ]
    )
