%%DESC: Fold a merged change into the living spec and archive it%%
%%HINT: <change-id>%%
Archive the merged change: %%ARG%%

Use the **drift-reconciliation** skill. Confirm the change is merged to main first.

1. Fold the delta into `%%SPECS_DIR%%/<capability>/spec.md`:
   ADDED → append (keep IDs) · MODIFIED → replace in place (keep IDs) → REMOVED → delete and record why.
2. Confirm any ADR is in `docs/adr/` with status `accepted`. ADRs outlive the
   change folder — that reasoning is what the next agent will need.
3. Move the folder to `%%CHANGES_DIR%%/archive/<YYYY-MM-DD>-<change-id>/`.
4. Run `asdlc verify` on the result.
