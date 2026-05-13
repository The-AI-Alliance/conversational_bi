import aws_cdk
import json

from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)

from constructs import Construct


class AccessStack(aws_cdk.Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env: aws_cdk.Environment,
        application_ci: str,
        datalake_bucket: s3.Bucket,
        scratch_bucket: s3.Bucket,
        database_name: str,
        **kwargs,
    ) -> None:

        super().__init__(scope, construct_id, env=env, **kwargs)

        service_account_username = f"svc-{application_ci}-{self.region}"

        service_account = iam.User(
            self,
            "IAMUser",
            user_name=service_account_username,
        )

        # TODO: There does not seem to be a secure way to get the access keys
        # for an IAM user and store them in AWS Secrets Manager.
        # You can retreive the access keys as strings, but then they are not
        # "secrets"....
        # Doing this manually via the AWS UI for now.

        # service_account_access_keys = iam.CfnAccessKey(
        #    self, "AccessKeys", user_name=service_account.user_name
        # )

        service_account_access_keys_secret = secretsmanager.Secret(
            self,
            "serviceAccountSecret",
            secret_name=f"{application_ci}/{service_account_username}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=(json.dumps({"aws_access_key_id": "some_junk"})),
                generate_string_key="aws_secret_access_key",
            ),
        )

        service_account_policy = iam.Policy(self, f"{application_ci}BucketReadWrite")

        # Scratch bucket and the data lake bucket...
        service_account_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket"],
                resources=[
                    datalake_bucket.arn_for_objects("*"),
                    scratch_bucket.arn_for_objects("*"),
                    datalake_bucket.bucket_arn,
                    scratch_bucket.bucket_arn,
                ],
            )
        )

        # Scratch bucket only...
        service_account_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[scratch_bucket.arn_for_objects("*")],
            )
        )

        # Base Athena permissions
        service_account_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryResults",
                    "athena:StopQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:ListDatabases",
                    "athena:GetWorkGroup",
                    "athena:ListTableMetadata",
                    "athena:GetTableMetadata",
                    "athena:ListWorkGroups",
                    "athena:GetDataCatalog",
                    "athena:GetDatabase",
                    "athena:ListDataCatalogs",
                ],
                resources=["*"],
            )
        )

        # Glue permissions
        service_account_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "glue:GetDatabase",
                    "glue:GetDatabases",
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetPartition",
                    "glue:GetPartitions",
                    "glue:BatchGetPartition",
                ],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:catalog",
                    f"arn:aws:glue:{self.region}:{self.account}:database/{database_name}",
                    f"arn:aws:glue:{self.region}:{self.account}:table/*/*",
                ],
            )
        )

        service_account.attach_inline_policy(service_account_policy)
