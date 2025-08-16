#!/bin/bash

# Create the DynamoDB table
aws dynamodb create-table \
    --table-name kubernetes_resources \
    --attribute-definitions AttributeName=name,AttributeType=S \
    --key-schema AttributeName=name,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1 \
    --endpoint-url http://localhost:8000
