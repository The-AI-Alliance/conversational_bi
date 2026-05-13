import builtins
from typing import List

import os

import aws_cdk
from aws_cdk import aws_iam

from datalake_stack.datalake_stack import DataLakeStack
from scratch_stack.scratch_stack import ScratchStack
from config.bucket_attributes import BucketAttributes
from analytics_stack.analytics_stack import AnalyticsStack
from access_stack.access_stack import AccessStack


class RegionalStack(aws_cdk.Stack):
    def __init__(
        self,
        scope,
        application_ci: str,
        source_bucket: BucketAttributes,
        target_buckets: List[BucketAttributes],
        source_scratch_bucket: BucketAttributes,
        target_scratch_buckets: List[BucketAttributes],
        deploy_replication: bool,
        tag: str,
        aws_environment: aws_cdk.Environment,
        id: builtins.str,
        **kwargs,
    ):
        # application_ci=application_ci
        super().__init__(scope, id)

        athena_database_name = os.getenv("AWS_ATHENA_DATABASE_NAME")

        datalake_stack = DataLakeStack(
            self,
            "datalake",
            application_ci=application_ci,
            bucket_name=source_bucket["bucket_name"],
            deploy_replication=deploy_replication,
            target_buckets=target_buckets,
            env=aws_environment,
        )

        scratch_stack = ScratchStack(
            self,
            "scratch",
            application_ci=application_ci,
            bucket_name=source_scratch_bucket["bucket_name"],
            deploy_replication=deploy_replication,
            target_buckets=target_scratch_buckets,
            env=aws_environment,
        )

        analytics_stack = AnalyticsStack(
            self,
            "analytics",
            application_ci=application_ci,
            tag=tag,
            datalake_bucket_name=source_bucket["bucket_name"],
            demo_dataset_name="bike_sales",
            db_name=athena_database_name,
            env=aws_environment,
        )

        access_stack = AccessStack(
            self,
            "access",
            application_ci=application_ci,
            datalake_bucket=datalake_stack.datalake_bucket,
            scratch_bucket=scratch_stack.scratch_bucket,
            database_name=athena_database_name,
            env=aws_environment,
        )
