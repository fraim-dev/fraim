# Admin Ports Detect 5938

This tests whether or not the LLM will detect port 5938 (Temaviewer) as an admin port.

## Before

Empty

## After

One security group with port 5938 exposed to the internet

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/admin-ports-detect-5938/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/admin-ports-detect-5938/before \
--head demos/admin-ports-detect-5938/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Disallow Public Admin Ports on Security Groups": "Disallow admin ports being open to the internet in security groups. Cover any edge cases."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Disallow Public Admin Ports on Security Groups

### Security group ingress opens an admin/remote access port (5938/TeamViewer) to the internet over both IPv4 and IPv6. (Severity: high)

**Location**: `main.tf:6`

**Explanation**:
* The change adds an aws_security_group with an ingress rule allowing port 5938 from 0.0.0.0/0 and ::/0.
* Port 5938 is used by TeamViewer (a remote administration/control service).
* Allowing this port from all IPv4 and IPv6 addresses exposes an administrative access channel to the public internet.
* Additionally, protocol "-1" (all protocols) combined with the open CIDRs further broadens exposure.
* The security team should verify whether public access is intended, and if not, restrict to trusted CIDRs or remove the rule.
```
