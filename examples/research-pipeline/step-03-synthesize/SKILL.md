# Synthesize findings into a research brief

Read from state: `topic`, `search_results`.

Write a structured research brief to `brief.md` using write_file (relative paths land in your step's output folder automatically).
Use this structure:

```
# Research Brief: <topic>

## Overview
2-3 sentence summary of what this topic is.

## Key Findings

### Fundamentals
...

### Recent Developments
...

### Practical Applications
...

### Challenges & Limitations
...

### Alternatives & Comparisons
...

## Sources
Bulleted list of all sources collected across all search results.

## Conclusion
3-4 sentences synthesizing the most important takeaways.
```

Draw all content from `search_results`. Do not add information not present in the results.

After writing the file, save to state:
- `output_path`: "output/step-03-synthesize/brief.md" (for reference by downstream steps)
- `handoff`: "Brief written. Pipeline complete."
