# Runbook: Deploying the CCE Tech Challenge

Operational steps to deploy, verify, and tear down the `cce-tech-challenge` stack.

## 1. Prerequisites

- AWS CLI v2 installed (`aws --version`).
- `zip` installed.
- AWS account access configured locally: an IAM user (not root) with an access key, permissions for CloudFormation/Lambda/API Gateway/DynamoDB/S3/IAM, and `aws configure` already run with that key.
- Verify: `aws sts get-caller-identity` should return your account/user ARN.

## 2. Environment preparation

```bash
export AWS_REGION=eu-west-1                     # region to deploy into
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET="cce-tech-challenge-artifacts-${AWS_ACCOUNT_ID}-${AWS_REGION}"

aws s3 mb "s3://$ARTIFACT_BUCKET" --region "$AWS_REGION"   # skip if it already exists

cd src
zip ingest.zip ingest_handler.py
cd ..
aws s3 cp src/ingest.zip "s3://$ARTIFACT_BUCKET/ingest.zip"
```

## 3. Deploy the stack

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name cce-tech-challenge \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      CodeBucket="$ARTIFACT_BUCKET" \
      IngestCodeKey=ingest.zip \
  --region "$AWS_REGION"
```

Re-run the same command after code changes (re-zip and re-upload first) — CloudFormation only updates what changed.

> **Note:** if you re-upload to the *same* S3 key (e.g. `ingest.zip`), CloudFormation won't detect the code changed and will report "No changes to deploy". Force the update directly instead:
> ```bash
> aws lambda update-function-code \
>   --function-name cce-tech-challenge-ingest \
>   --s3-bucket "$ARTIFACT_BUCKET" \
>   --s3-key ingest.zip \
>   --region "$AWS_REGION"
> ```

## 4. Verify the deployment

```bash
# Get the API endpoint
export API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name cce-tech-challenge --region "$AWS_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text)

# Smoke test
curl -s -X POST "$API_ENDPOINT/items" \
  -H "Content-Type: application/json" \
  -d '{"name": "example item", "value": 42}' -w "\nHTTP %{http_code}\n"

# Confirm the item was persisted
aws dynamodb scan --table-name cce-tech-challenge-items --region "$AWS_REGION"
```

Expected result: `HTTP 201` with a JSON body containing an `id`, and the item visible in the DynamoDB scan.

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `aws sts get-caller-identity` fails / session expired | Credentials expired | Re-run `aws configure` (or `aws sso login` if using SSO) |
| `cloudformation deploy` fails with `AccessDenied` | IAM user missing a permission | Check the failing action in the error, add the matching managed policy |
| `403`/`404` on the API call | Stack not deployed yet, or wrong endpoint | Re-check `ApiEndpoint` output, confirm stack status is `CREATE_COMPLETE`/`UPDATE_COMPLETE` |
| Lambda code changes not reflected | Zip not re-uploaded, or S3 key unchanged | CloudFormation only detects a Lambda code change if the S3 object changed; re-upload with a new key or the same key (S3 versioning off means overwrite is picked up on next deploy) |

## 6. Clean up

```bash
aws cloudformation delete-stack --stack-name cce-tech-challenge --region "$AWS_REGION"
aws cloudformation wait stack-delete-complete --stack-name cce-tech-challenge --region "$AWS_REGION"
aws s3 rb "s3://$ARTIFACT_BUCKET" --force
```
