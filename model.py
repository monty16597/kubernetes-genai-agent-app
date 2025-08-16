import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = "kubernetes_resources"


def get_dynamodb_table():
    """Initialize and return DynamoDB table resource."""
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            endpoint_url="http://localhost:8000"  # Remove for real AWS
        )
        table = dynamodb.Table(TABLE_NAME)
        table.load()
        return table
    except ClientError as e:
        raise RuntimeError(f"DynamoDB ClientError: {e.response['Error']['Message']}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to DynamoDB: {e}")


def save_item_to_db(table, name: str, instructions: str, resources: dict | str) -> bool:
    """Save or update an item in DynamoDB."""
    try:
        table.put_item(Item={
            'name': name,
            'instructions': instructions,
            'resources': resources
        })
        return True
    except ClientError as e:
        raise RuntimeError(f"Could not save item: {e.response['Error']['Message']}")


def get_all_items(table):
    """Retrieve all items from DynamoDB."""
    try:
        response = table.scan()
        return sorted(response.get('Items', []), key=lambda x: x['name'])
    except ClientError as e:
        raise RuntimeError(f"Could not retrieve items: {e.response['Error']['Message']}")


def get_item(table, name: str):
    """Retrieve a single item from DynamoDB by name."""
    try:
        response = table.get_item(Key={'name': name})
        return response.get('Item')
    except ClientError as e:
        raise RuntimeError(f"Could not retrieve item: {e.response['Error']['Message']}")


def delete_item(table, name: str) -> bool:
    """Delete an item from DynamoDB."""
    try:
        table.delete_item(Key={'name': name})
        return True
    except ClientError as e:
        raise RuntimeError(f"Could not delete item: {e.response['Error']['Message']}")
