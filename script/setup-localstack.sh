source .env

awslocal sns create-topic --name caselaw-stg-judgment-updated
awslocal s3api create-bucket --bucket private-asset-bucket
awslocal s3api create-bucket --bucket public-asset-bucket
awslocal --endpoint-url=http://localhost:4566 sqs create-queue --queue-name dummy-queue  --region us-east-1 --output table
SUBSCRIPTION=`awslocal --endpoint-url=http://localhost:4566 sns subscribe --topic-arn arn:aws:sns:us-east-1:000000000000:caselaw-stg-judgment-updated --protocol sqs --notification-endpoint http://localstack:4566/000000000000/dummy-queue | jq '.SubscriptionArn' | sed s/\"//g`
echo $SUBSCRIPTION
awslocal sns set-subscription-attributes --subscription-arn $SUBSCRIPTION --attribute-name FilterPolicy --attribute-value '{"trigger_enrichment": "1"}'
