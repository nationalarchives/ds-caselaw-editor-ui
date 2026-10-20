source .env

# LocalStack + AWS CLI v2 default to eu-west-2 from the host env; buckets must match
# PRIVATE_ASSET_BUCKET_REGION (us-east-1) or the Editor UI S3 client fails oddly.
export AWS_DEFAULT_REGION="${PRIVATE_ASSET_BUCKET_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

awslocal sns create-topic --name caselaw-stg-judgment-updated --region "$AWS_DEFAULT_REGION"
awslocal s3api create-bucket --bucket private-asset-bucket --region "$AWS_DEFAULT_REGION"
awslocal s3api create-bucket --bucket public-asset-bucket --region "$AWS_DEFAULT_REGION"
awslocal sqs create-queue --queue-name dummy-queue --region "$AWS_DEFAULT_REGION"
awslocal sns create-topic --name event-hub --region "$AWS_DEFAULT_REGION"

ACCOUNT=000000000000
SQS_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:${ACCOUNT}:dummy-queue"
EVENT_HUB_ARN="arn:aws:sns:${AWS_DEFAULT_REGION}:${ACCOUNT}:event-hub"
JUDGMENT_UPDATED_ARN="arn:aws:sns:${AWS_DEFAULT_REGION}:${ACCOUNT}:caselaw-stg-judgment-updated"

awslocal sns subscribe --topic-arn "$EVENT_HUB_ARN" --protocol sqs --notification-endpoint "$SQS_ARN" | jq '.SubscriptionArn' | sed s/\"//g

SUBSCRIPTION=$(awslocal sns subscribe --topic-arn "$JUDGMENT_UPDATED_ARN" --protocol sqs --notification-endpoint "$SQS_ARN" | jq '.SubscriptionArn' | sed s/\"//g)
echo $SUBSCRIPTION
awslocal sns set-subscription-attributes --subscription-arn $SUBSCRIPTION --attribute-name FilterPolicy --attribute-value '{"trigger_enrichment": ["1"]}'
