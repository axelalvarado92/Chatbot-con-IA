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

def guardar_business_config(
    bucket_name,
    business_file,
    business_config
):

    s3.put_object(
        Bucket=bucket_name,
        Key=business_file,
        Body=json.dumps(
            business_config,
            indent=2,
            ensure_ascii=False
        ).encode("utf-8"),
        ContentType="application/json"
    )

    print("Business config actualizado correctamente.")

    