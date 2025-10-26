# Instance Profile vs Container Role

This tests whether or not the LLM will detect the difference between the permissions needed between an ECS Container role and it's corresponding Instance Profile

## Before

Empty

## After

Two IAM roles, one for a container role and the other for an instance profile

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/instance-profile-vs-container-role/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/instance-profile-vs-container-role/before \
--head demos/instance-profile-vs-container-role/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Overly Permissive IAM": "Understand the types of policies that should be in an instance profile vs a container role. And flag when a user is putting policies that should be intended for one into the other."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Overly Permissive IAM

### Container role includes policies intended for an instance profile (EC2 Describe* and ECR pull actions). (Severity: medium)

**Location**: `main.tf:1`

**Explanation**:
* The container/application role (aws_iam_role.test_role_container) is granted managed policies that include EC2 Describe* (policy_one) and ECR image pull permissions (policy_three).
* EC2 Describe* and ECR image pull permissions are typically required by the host/instance profile or task execution role, not by the application container role.
* Assigning these to the container role broadens its permissions beyond what the application should need and mixes responsibilities between container and instance/execution roles.

---

### Instance profile role includes policies intended for a container/application role (broad S3 write on all buckets). (Severity: high)

**Location**: `main.tf:7`

**Explanation**:
* The instance profile role (aws_iam_role.test_role_instance_profile) is granted a managed policy (policy_two) that includes "s3:Write*" on Resource "*".
* Broad S3 write access is typically application-specific and should be granted to the container/task role with least privilege to specific buckets, not to the instance profile.
* Placing this on the instance profile unnecessarily elevates the host's privileges and mixes responsibilities between instance and container roles.

---

### Both roles are attached to the exact same set of managed policies, indicating role boundary violations. (Severity: medium)

**Location**: `main.tf:1`

**Explanation**:
* The container role and the instance profile role are both attached to the same three managed policies.
* This suggests a conflation of responsibilities between an instance/execution role and an application/container role.
* Security should verify and realign policies so that: (1) host/instance/execution responsibilities (e.g., EC2 Describe*, ECR image pull) are on the instance/execution role only, and (2) application data access (e.g., S3 write) is scoped and placed on the container role only.
```
