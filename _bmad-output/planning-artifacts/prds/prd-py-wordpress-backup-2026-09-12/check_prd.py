#!/usr/bin/env python3
"""Consistency checks for the wpbackup2 PRD.

Scope is derived from the document itself - the set of FR definitions, the set of
Q entries, the set of [ASSUMPTION] tags - never from a hand-kept list here, so a
requirement added later cannot quietly escape these checks.
"""
import re, sys, pathlib

P = pathlib.Path(__file__).with_name("prd.md")
text = P.read_text()
fail = []

# --- source of truth: the FR headings themselves ---
defined = {int(m) for m in re.findall(r"^#### FR-(\d+):", text, re.M)}
referenced = {int(m) for m in re.findall(r"FR-(\d+)", text)}

# 1. every referenced FR is defined
dangling = referenced - defined
if dangling:
    fail.append(f"referenced but never defined: {sorted('FR-%d' % n for n in dangling)}")

# 2. FR numbering is contiguous from 1 (no silent gaps)
gaps = set(range(1, max(defined) + 1)) - defined
if gaps:
    fail.append(f"gaps in FR numbering: {sorted('FR-%d' % n for n in gaps)}")

# 3. the S0 range claim matches reality
claim = re.search(r"numbered globally \(FR-1…FR-(\d+)\)", text)
if not claim:
    fail.append("S0 no longer states an FR range - the coverage claim vanished")
elif int(claim.group(1)) != max(defined):
    fail.append(f"S0 claims FR-1…FR-{claim.group(1)} but the document defines through FR-{max(defined)}")

# 4. every defined FR is placed in exactly one release phase in S13.2
i, j = text.find("### 13.2 Release Phasing"), text.find("## 14. Success Metrics")
phasing = text[i:j]
phases = {}
for name in ("Release A", "v1.0 —", "v1.0.1 —", "v1.1"):
    k = phasing.find("#### " + name)
    phases[name] = k
order = sorted((k, n) for n, k in phases.items() if k != -1)
if len(order) != 4:
    fail.append(f"expected 4 release phases in S13.2, found {len(order)}")
else:
    placed = {}
    for idx, (k, name) in enumerate(order):
        end = order[idx + 1][0] if idx + 1 < len(order) else len(phasing)
        # A placement is a bullet. Prose in a phase block may cross-reference an FR
        # placed elsewhere ("FR-24 moves to v1.1"); counting those as placements made
        # every such cross-reference a false duplicate. Restricting to list items is
        # stricter, not looser: an FR named only in prose now falls out as unplaced.
        bullets = "\n".join(l for l in phasing[k:end].splitlines() if l.lstrip().startswith("- "))
        for n in {int(m) for m in re.findall(r"FR-(\d+)", bullets)}:
            placed.setdefault(n, []).append(name)
    unplaced = defined - set(placed)
    if unplaced:
        fail.append(f"defined but in no release phase: {sorted('FR-%d' % n for n in unplaced)}")
    CARRY = {"Release A", "v1.0 —"}   # Release A ships first; v1.0 re-states what it must keep enforcing
    multi = {n: v for n, v in placed.items() if len(v) > 1 and set(v) != CARRY}
    if multi:
        fail.append("in more than one phase: " + ", ".join(f"FR-{n} ({'/'.join(v)})" for n, v in sorted(multi.items())))

# 4b. success metrics: same contiguity rule as FRs, since S14 is renumbered by hand too
sm_defined = {int(m) for m in re.findall(r"\*\*SM-(\d+) ·", text)}
sm_referenced = {int(m) for m in re.findall(r"SM-(\d+)", text)}
if sm_defined:
    sm_gaps = set(range(1, max(sm_defined) + 1)) - sm_defined
    if sm_gaps:
        fail.append(f"gaps in SM numbering: {sorted('SM-%d' % n for n in sm_gaps)}")
    sm_dangling = sm_referenced - sm_defined
    if sm_dangling:
        fail.append(f"SM referenced but never defined: {sorted('SM-%d' % n for n in sm_dangling)}")
smc_defined = {int(m) for m in re.findall(r"\*\*SM-C(\d+) ·", text)}
if smc_defined:
    smc_gaps = set(range(1, max(smc_defined) + 1)) - smc_defined
    if smc_gaps:
        fail.append(f"gaps in counter-metric numbering: {sorted('SM-C%d' % n for n in smc_gaps)}")

# 5. every Q referenced in the body has an entry in S15
s15 = text[text.find("## 15."):text.find("## 16.")]
q_defined = set()
for head in re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", s15, re.M):
    q_defined.update(int(m) for m in re.findall(r"Q-(\d+)", head))
q_referenced = {int(m) for m in re.findall(r"Q-(\d+)", text)}
q_dangling = q_referenced - q_defined
if q_dangling:
    fail.append(f"Q referenced but not listed in S15: {sorted('Q-%d' % n for n in q_dangling)}")

# 6. every [ASSUMPTION] tag in the body is accounted for in S16
# S0 describes the tagging convention; only S1 onward actually uses it
body, s16 = text[text.find("## 1. Vision"):text.find("## 16.")], text[text.find("## 16."):]
tags = len(re.findall(r"\[ASSUMPTION", body))
m = re.search(r"\*\*Still open, and tagged in the body:\*\*\n(.*?)\n\n\*\*", s16, re.S)
if not m:
    fail.append("S16 lost its open-assumption section")
else:
    listed = len(re.findall(r"^- ", m.group(1), re.M))
    if listed != tags:
        fail.append(f"S16 lists {listed} open assumptions but the body carries {tags} [ASSUMPTION] tags")

print(f"FRs: {len(defined)} (FR-1…FR-{max(defined)})   SMs: {len(sm_defined)}+{len(smc_defined)} counter   Qs listed: {len(q_defined)}   open [ASSUMPTION] tags: {tags}")
if fail:
    print("\nFAIL")
    for f in fail:
        print("  - " + f)
    sys.exit(1)
print("PASS - all checks green")
