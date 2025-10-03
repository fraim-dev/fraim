# IAM Unnecessary Actions

This tests whether or not the LLM will detect the context an IAM role is being used in and whether or not it's corresponding policies are appropriate or not

## Before

Two IAM roles with policies attached. One of the roles has read access to ECR but also administrative actions on sqs to Create and Delete a Queue.

## After

An EC2 instance that attaches the role with SQS Create / Delete attached to it.

## Run Test Case

1. Checkout the head test branch
```
git checkout demos/iam-unnecessary-actions/after
```

2. Run Fraim
```
fraim run risk_flagger --model openai/gpt-5 --temperature 1 --diff \
--base demos/iam-unnecessary-actions/before \
--head demos/iam-unnecessary-actions/after \
--custom-risk-list-action replace \
--custom-risk-list-json '{"Overly Permissive Role": "Look at any role attached to a cloud resource, and flag it if there is no reason a policy in that role should be attached to that cloud resource. ie destructive permissions to other cloud resources."}'
```

## Results

```
# Security Risk Review Required

The following security risks have been identified and require review:

## Overly Permissive Role

### EC2 instance attaches an IAM instance profile whose role includes destructive and broad permissions (e.g., SQS DeleteQueue on all resources). (Severity: high)

**Location**: `ec2.tf:5`

**Explanation**:
* 1) Trigger: A new aws_instance (app_instance) was created and configured with iam_instance_profile = aws_iam_instance_profile.test_role_instance_profile.name.
* The referenced role (aws_iam_role.test_role_instance_profile in main.tf) has managed_policy_arns including policy_three.
* 2) Relation to risk: policy_three grants SQS management actions, including sqs:CreateQueue and sqs:DeleteQueue, with Resource = "*".
* DeleteQueue is a destructive permission on another cloud resource and is broadly scoped.
* Attaching this to an EC2 instance constitutes an overly permissive role.
* 3) Security implications to investigate: Whether this EC2 instance legitimately requires creating/deleting SQS queues; if not, remove or scope down these actions.
* At minimum, restrict to specific queues (by ARN) and drop DeleteQueue if unnecessary.
* Validate that only required ECR read actions remain and that EC2 Describe* is acceptable..
```
