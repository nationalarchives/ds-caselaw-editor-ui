source .env

awslocal sns create-topic --name caselaw-stg-judgment-updated
awslocal s3api create-bucket --bucket private-asset-bucket
awslocal s3api create-bucket --bucket public-asset-bucket
