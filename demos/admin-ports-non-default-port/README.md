# Admin Ports Non Default Port

This tests whether or not the LLM will detect a non-default port in a Redis cluster being used and that corresponding port being open to the public in a security group.

## Before

A Redis Cluster with port 7000 instead of port 6379

## After

One security group with port 7000 exposed to the internet

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/admin-ports-non-default-port/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/admin-ports-non-default-port/before \
--head demos/admin-ports-non-default-port/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Disallow Public Admin Ports on Security Groups": "Disallow admin ports being open to the internet in security groups. Cover any edge cases and cover any non-default ports used in the codebase"}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Disallow Public Admin Ports on Security Groups

### Security group opens port 7000 to the internet over IPv4 and IPv6. (Severity: high)

**Location**: `main.tf:1`

**Explanation**:
* This change introduces an aws_security_group with an ingress rule allowing 0.0.0.0/0 and ::/0 to TCP port 7000.
* The risk to consider is disallowing admin ports being open to the internet.
* In this codebase, port 7000 is used by a Redis service (see redis.tf setting port = 7000), which represents a sensitive administrative/data service port on a non-default number.
* Exposing it publicly over both IPv4 and IPv6 directly violates the policy.
* The security team should verify intent and restrict access (e.g., to specific CIDR ranges, VPC endpoints, or source security groups) or remove public exposure.
```
