# Admin Ports Pulumi

This tests whether or not the LLM will detect an admin port being open with Pulumi configuration

## Before

Empty

## After

One Pulumi security group with port 5432 exposed to the internet

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/admin-ports-pulumi/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/admin-ports-pulumi/before \
--head demos/admin-ports-pulumi/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Disallow Public Admin Ports on Security Groups": "Disallow admin ports being open to the internet in security groups. Cover any edge cases."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Disallow Public Admin Ports on Security Groups

### Security group ingress opens PostgreSQL admin port 5432 to the internet over both IPv4 and IPv6. (Severity: critical)

**Location**: `main.ts:12`

**Explanation**:
* This change adds two aws.vpc.SecurityGroupIngressRule resources that allow inbound TCP traffic on port 5432 (PostgreSQL) from 0.0.0.0/0 (lines 12-18) and ::/0 (lines 19-25).
* Port 5432 is a database administration/service port and opening it to the entire internet violates the policy to disallow public admin ports on security groups.
* The security team should investigate and restrict access to specific trusted CIDRs or security groups, and remove the world-open IPv6 rule if not explicitly required.
```
