# Tasks — {{TITLE}}

**Change ID:** {{CHANGE_ID}}

<!-- Each task: atomic, verifiable, and tagged with the requirement it serves.
     The traceability gate reads the REQ- tags. Untagged tasks are scope creep. -->

## Implementation
- [ ] (REQ-001) <task — small enough to review in one sitting>
- [ ] (REQ-001) <task>
- [ ] (REQ-002) <task>

## Tests
- [ ] (REQ-001) Unit test: <scenario name from spec.md>
- [ ] (REQ-001) Unit test: <failure scenario>
- [ ] (REQ-002) Integration test: <scenario>
- [ ] Regression: <existing behaviour to re-verify>

## Documentation
- [ ] Update AGENTS.md if conventions changed
- [ ] Update openspec/specs/<capability>/spec.md (living spec)
- [ ] ADR written if an architectural decision was made

## Verification
- [ ] `asdlc verify --stage spec` passes
- [ ] `asdlc verify` passes locally
- [ ] Human reviewed design.md before implementation started
