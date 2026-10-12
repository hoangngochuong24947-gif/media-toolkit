# Report template

The host agent fills this in after reading the timestamped text. No script in this skill calls an LLM or writes this prose.

Copy this file to `${MEDIA_OUTPUT_DIR:-./output}/<task>/report.md` and replace the blanks. Write in the user's language. Cite only timestamps that appear in the text files.

```markdown
# <title>

- Task: <task directory>
- Request: <what the user asked>
- Evidence: <list of text files actually read>
- Writer: host agent (not a script)

## Sources

| webpage_url | evidence file | kind |
| :--- | :--- | :--- |
| https://... | text/....txt | manual subtitles / auto captions / local ASR |

## Summary

<the agent writes this from the text it read>

## Timestamped points

- [mm:ss] <point tied to a cue in the text>
- [mm:ss] <point>

## Not established

- <numbers or claims that were not in the text>
```

Rules for the agent:

- One report for the task, not one summary per chunk.
- If the text is split into `part-001.txt`, `part-002.txt`, read them in order, then write the report once.
- Automatic captions and local ASR can mis-hear words. Do not turn a guessed figure into a specification.
- Do not add screenshots unless the user asked for pictures.
