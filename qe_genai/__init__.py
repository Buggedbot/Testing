"""GenAI toolkit for QE teams whose only AI access is GitHub Copilot in the IDE.

Every tool follows the same three-step pattern (no LLM API calls, no network):

1. A script assembles the relevant context (failure logs, JUnit results, git
   diffs, specs) into a structured, ready-to-paste prompt file.
2. A QE pastes the prompt into GitHub Copilot Chat (or any chat assistant)
   and reads the answer.
3. The answer is applied by the human -- filed in Azure DevOps, committed as
   a fixture, used to pick which tests to run, etc.

This package is deliberately independent of `self_healing_locator` and of any
test framework: everything that consumes test results does so via JUnit XML,
which Selenium (pytest/TestNG), Playwright, and Azure DevOps pipelines can
all produce, so teams on other stacks can use it unchanged.
"""

__version__ = "0.1.0"
