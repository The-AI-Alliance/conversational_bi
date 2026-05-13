from aws_cdk import aws_s3, aws_iam, Stack
from constructs import Construct
from typing import List
from config.bucket_attributes import BucketAttributes
from aws_cdk.aws_s3 import CfnBucket


class DataLakeStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        bucket_name: str,
        target_buckets: List[BucketAttributes],
        deploy_replication: bool,
        application_ci: str,
        **kwargs,
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)

        replication_role = aws_iam.Role(
            self,
            "ReplicationRole",
            assumed_by=aws_iam.ServicePrincipal("s3.amazonaws.com"),
        )
        # https://github.com/aws/aws-cdk/issues/29782
        # replication_role.grant_assume_role(aws_iam.ServicePrincipal('batchoperations.s3.amazonaws.com'))

        replication_role.assume_role_policy.add_statements(
            aws_iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                principals=[
                    aws_iam.ServicePrincipal("batchoperations.s3.amazonaws.com")
                ],
            )
        )

        target_bucket_objects = []
        if deploy_replication:
            target_bucket_objects = [
                aws_s3.Bucket.from_bucket_attributes(
                    self,
                    id=tb["id"],
                    account=tb["account"],
                    bucket_name=tb["bucket_name"],
                    region=tb["region"],
                )
                for tb in target_buckets
            ]

        self.datalake_bucket = aws_s3.Bucket(
            self,
            f"{application_ci}DatalakeBucket",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            bucket_name=bucket_name,
            enforce_ssl=True,
            versioned=True,
        )
        if deploy_replication:
            cfn_bucket: CfnBucket = self.datalake_bucket.node.default_child

            cfn_bucket.replication_configuration = (
                aws_s3.CfnBucket.ReplicationConfigurationProperty(
                    role=replication_role.role_arn,
                    rules=[
                        aws_s3.CfnBucket.ReplicationRuleProperty(
                            destination=aws_s3.CfnBucket.ReplicationDestinationProperty(
                                bucket=bucket.bucket_arn
                            ),
                            status="Enabled",
                        )
                        for bucket in target_bucket_objects
                    ],
                )
            )

        replication_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "s3:GetObjectVersionForReplication",
                    "s3:GetObjectVersionAcl",
                    "s3:GetObjectVersionTagging",
                ],
                resources=[
                    self.datalake_bucket.arn_for_objects("*"),
                ],
            )
        )
        replication_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetReplicationConfiguration"],
                resources=[
                    self.datalake_bucket.bucket_arn,
                ],
            ),
        )
        for bucket in target_bucket_objects:
            replication_role.add_to_policy(
                aws_iam.PolicyStatement(
                    actions=[
                        "s3:ReplicateObject",
                        "s3:ReplicateDelete",
                        "s3:ReplicateTags",
                    ],
                    resources=[
                        bucket.arn_for_objects("*"),
                    ],
                ),
            )
