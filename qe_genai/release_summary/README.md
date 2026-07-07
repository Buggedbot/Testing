# Release / Run Summary

**What it does:** condenses one or more JUnit reports into a summary prompt
with two audience modes — `technical` (for the QE/dev channel: failures
grouped by suspected cause, deltas vs the previous run) and `stakeholder`
(for product/management: plain-language quality statement, risk areas, go/no-
go input, zero stack traces).

## Use case

You already have a summarization agent for test reports — this complements it
with the audience split and the multi-run trend view. End of a sprint or
before a release cut: point it at the run artifacts, generate both versions,
paste each into Copilot Chat, and post the results to the respective Teams
channels. The stakeholder version is the one QE teams usually never write
because translating "34 failed, 12 flaky" into product language is effort.

## How to run

```bash
# single run, for the team channel
qe summary --junit artifacts/test-results.xml --audience technical --out qe_prompts/

# multiple runs (trend), for the release readout
qe summary --junit runs/*.xml --audience stakeholder \
  --context "Release 2024.8 cut is Thursday; checkout redesign shipped this sprint" \
  --out qe_prompts/
```

`--context` is where you tell the model what the release moment is — it
changes what "matters" in the summary.

## What you get

`qe_prompts/release_summary.prompt.md` containing computed pass/fail counts
(the tool does the arithmetic so the model can't get it wrong) plus failure
details, and audience-specific writing instructions.

## Limitations

- The stakeholder version states quality *as evidenced by these tests* — if
  coverage is thin, the summary inherits that blind spot; pair with
  `coverage_gap/` for honesty about what the suite doesn't see.
