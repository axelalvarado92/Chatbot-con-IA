import json
import boto3

s3 = boto3.client("s3")


def cargar_business_config(bucket, file_key):
    response = s3.get_object(
        Bucket=bucket,
        Key=file_key
    )

    return json.loads(
        response["Body"].read().decode("utf-8")
    )