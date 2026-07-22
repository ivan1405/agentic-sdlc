# Spec — my-first-change

**Change ID:** my-first-change
**Capability:** <!-- REQUIRED if this touches a mapped capability (see .asdlc/policy.yaml).
                     The drift gate reads this line. -->

<!-- The contract. This file is what the agent implements against and what the
     tests assert. Deltas only: describe what changes, not the whole system.
     Mark sections ADDED / MODIFIED / REMOVED. -->

## ADDED Requirements

### REQ-001: <short imperative name>
The system SHALL <normative statement — testable, singular, no "and">.

#### Scenario: <happy path>
- **Given** <starting state>
- **When** <action>
- **Then** <observable outcome>

#### Scenario: <failure / edge case>
- **Given**
- **When**
- **Then**

### REQ-002: <name>
The system SHALL NOT <normative statement>.

#### Scenario: <name>
- **Given**
- **When**
- **Then**

## MODIFIED Requirements
<!-- Quote the previous requirement ID from openspec/specs/<capability>/spec.md,
     then state the new behaviour. -->

## REMOVED Requirements
<!-- Removing a requirement is a breaking change. Say who is affected and how
     they are migrated. -->

## Non-functional requirements
<!-- Only the ones this change actually moves. "Fast" is not a requirement. -->
| Attribute | Requirement | Verified by |
|---|---|---|
| Latency | p95 SHALL be < ___ ms at ___ rps | load test |
| Security | | |
| Accessibility | | |

## Explicitly not guaranteed
<!-- Where an agent must stop and ask rather than infer. -->
