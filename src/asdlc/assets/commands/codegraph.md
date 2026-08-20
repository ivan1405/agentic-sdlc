%%DESC: Build or refresh the code knowledge graph and open its visualizer%%
%%HINT: [optional: path or area to focus on]%%
Build or refresh the code knowledge graph: %%ARG%%

This is the maintenance command for the `codegraph` MCP server (CodeGraphContext)
that `/onboard` first offers to add. Use it any time the graph is stale or you
just want to look at it — it doesn't touch the context file or re-run the rest
of onboarding.

1. Confirm the `codegraph` MCP server is connected (an `mcp__codegraph__*`
   tool in your tool list). If it isn't, tell the user to run `asdlc mcp add
   codegraph` and reconnect/restart their agent tool, then stop — don't add
   it yourself, `/onboard` is the only place that does that.
2. Call `add_code_to_graph` against `.` (or the path from %%ARG%%, if given)
   to index the repo, or refresh it if it's already indexed — check
   `list_indexed_repositories`/`get_repository_stats` first so you know which
   case you're in. Indexing returns a job ID; poll `check_job_status` until
   it finishes before moving on. Only force a from-scratch rebuild if the
   user asks for one.
3. Ask the user: *"Want to open the graph visualizer in your browser?"*
   - If no, stop here — the graph is built/refreshed, nothing else to do.
   - If yes, `cgc visualize` starts a local web server (default
     `http://127.0.0.1:8000`, override with `--repo`/`--host`/`--port`) and
     does not return control on its own — run it as a background process,
     never in the foreground, or it blocks this session.
   - Only hand the user the URL once the server is actually listening — a
     link nothing answers on yet is worse than no link (that's the dead-link
     failure mode this command exists to avoid).
   - Tell the user it keeps running until they stop it, and how to stop the
     background process when they're done.
