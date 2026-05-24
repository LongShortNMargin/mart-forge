# using-mart-forge — Session Bootstrap Skill

**Trigger:** SessionStart hook — fires automatically on every session.

## Behavior

On session start, detect the current lifecycle phase and route to the appropriate skill.

### Phase Detection Logic

```
1. Check: Does a mart directory exist under examples/?
   └── No → Phase A (need BRD first)
   └── Yes → continue

2. Check: Does a BRD exist in the mart directory?
   └── No → Route to mart-brd skill
   └── Yes → continue

3. Check: Is the BRD signed off (contains sign-off stamp)?
   └── No → "BRD exists but needs sign-off. Present to operator for review."
   └── Yes → continue

4. Check: Does a TDD exist in the mart directory?
   └── No → Route to mart-tdd skill
   └── Yes → continue

5. Check: Is the TDD signed off?
   └── No → "TDD exists but needs sign-off. Present to reviewer."
   └── Yes → continue

6. Check: Does a dbt_project.yml exist (scaffold complete)?
   └── No → Route to mart-bootstrap skill
   └── Yes → continue

7. Check: Does dqc_scorecard.json exist and is it current?
   └── No → Route to mart-dqc skill
   └── Yes → "Mart is scaffolded and tested. Use mart-review for readiness check."
```

### Hard Gates

These gates are absolute and cannot be bypassed:

- **No TDD without signed-off BRD.** If an agent or user requests TDD generation and no signed-off BRD exists, refuse and explain why.
- **No scaffold without signed-off TDD.** If scaffold is requested without a signed-off TDD, refuse and explain the gate.
- **No mart.yml before source discovery.** Source discovery, BRD, and TDD precede mart.yml generation.

### Session Output

Report the detected phase and available actions:

```
mart-forge session initialized.
Current phase: {Phase A/B/C/D/E}
Mart: {mart name or "none detected"}
Next action: {recommended skill}
```
