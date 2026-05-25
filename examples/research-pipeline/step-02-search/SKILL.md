# Search all queries in parallel

Read `queries` from state (list of 5 search query strings).

## Parallel dispatch

In a single response, call dispatch_task once for each query — all at the same time.
The runner will execute all 5 sub-tasks concurrently and return their results together.

For each query, use this pattern:

```
dispatch_task(
  task: "Search the web and summarize findings",
  name: "search-<short-slug>",   ← short kebab-case label, e.g. "search-fundamentals"
  skill: "Use web_search to search for: '<QUERY>'. Read the top results. Write a file called results.md with your findings (key points and sources). Return a JSON object with exactly these keys: query (the search string), key_points (list of 3-5 factual bullet points from the results), sources (list of up to 3 source titles or URLs).",
  context: { query: "<QUERY>" }
)
```

Replace `<QUERY>` with the actual query string. Give each dispatch a distinct `name` that reflects the query angle (e.g. `search-fundamentals`, `search-recent-news`, `search-applications`).

## After results arrive

You will receive an array of 5 result objects. Collect them all.

Save to state:
- `search_results`: the full array of result objects from all sub-tasks
- `handoff`: "Searched 5 queries in parallel. Results ready for synthesis."
