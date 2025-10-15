# Admin Ports CIDR Edge Case

This tests whether or not the LLM will detect the edge case where the user enters CIDR ranges of 0.0.0.0/1 and 128.0.0.0/1 to bypass a check against 0.0.0.0/0

## Before

Empty

## After

One security group with port 5432 exposed to CIDRs 0.0.0.0/1 and 128.0.0.0/1

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/admin-ports-cidr-edge-case/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/admin-ports-cidr-edge-case/before \
--head demos/admin-ports-cidr-edge-case/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Disallow Public Admin Ports on Security Groups": "Disallow admin ports being open to the internet in security groups. Cover any edge cases."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Disallow Public Admin Ports on Security Groups

### Security group opens PostgreSQL (5432) to the public internet using split CIDR blocks (0.0.0.0/1 + 128.0.0.0/1), an edge case equivalent to 0.0.0.0/0. (Severity: high)

**Location**: `main.tf:6`

**Explanation**:
* The change adds an aws_security_group with an ingress rule allowing TCP port 5432 (PostgreSQL) from two CIDR blocks: 0.0.0.0/1 and 128.0.0.0/1.
* These two CIDRs together cover the entire IPv4 internet (equivalent to 0.0.0.0/0), which is an edge-case pattern used to bypass simple 0.0.0.0/0 checks.
* Opening a database administration/service port to the public internet violates the policy to disallow public admin ports on security groups.
* The security team should investigate and restrict access to trusted ranges or remove public exposure.
```
