# Overly Permissive IAM Actions

This tests whether or not the LLM will detect an IAM role with a policy that has "s3:Wri*" in the policy, which will allow all s3 write actions.

## Before

Empty

## After

One IAM role with two policies, one of which has an Action of "s3:Wri*"

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/overly-permissive-iam-actions/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/overly-permissive-iam-actions/before \
--head demos/overly-permissive-iam-actions/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Overly Permissive IAM": "Disallow IAM roles from having a wildcard statement with Write or Create actions."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Overly Permissive IAM

### IAM policy grants wildcard Write permissions (s3:Pu*) on all S3 resources and is attached to a role. (Severity: high)

**Location**: `demos/overly-permissive-iam-actions/main.tf:29`

**Explanation**:
* The change introduces aws_iam_policy.policy_two with an Action of "s3:Pu*" and Resource "*" (lines 29-35), which is attached to aws_iam_role.example via managed_policy_arns.
* The wildcard "Pu*" matches S3 Put* actions (write/create operations), granting broad write permissions across all S3 resources.
* This directly falls under the risk of Overly Permissive IAM where wildcard statements grant Write/Create actions.
* Security should investigate and require least-privilege: replace the wildcard with explicit required actions and scope Resource to specific buckets/ARNS, potentially adding conditions.
```
