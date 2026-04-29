---
layout: default
title: Decision Support: Future State
nav_order: 30
has_children: false
---

# Possible Future Direction Enabled By GenAI

Many LLM based tools, such as Anthropic's Claude Code or Microsoft's CoPilot have demonstrated the ability to assist with coding. In this case, the coding is very specialized - transforming natural language KPI definitions into SQL using the enterprise data model as input. The following examples use Claude Desktop and the supported Opus4.6 model:

![KPI Generation](./assets/images/ClaudeExample1.png)

Similarly, another very specialized set of GenAI assisted coding: Javascript D3 widgets generated using SQL views:

![Visualization Generation](./assets/images/ClaudeExample2.png)

## Two Considerations

Anybody that has ever worked in decision support has been confronted with the dreaded question "Why don't these two reports match?". The unpredictability of GenAI does not lend itself naturally to decision support, as the same KPI posed using natual language may generate different results at different times.

To combat this, the idea of "ground truth" is introduced. Queries and views are developed with GenAI code assist, but are treated as version controlled artifacts that go through a normal review process. In the reference architecture, GitHub can be used as the truth repository, and a simple GenAI workflow can built around it:

![Ground Truth](./docs/images/GroundTruth.png)

Example of the workflow in action:

![Workflow](./docs/images/Workflow.png)


The second consideration: in a retail scenario, can natural language map to exact items or groups of items in the enterprise item hierarchy? An additional data structure - one that helps the LLM map natural language to actual items in the item hierarchy is needed, and will be added to this project demonstrating how this might be addressed in a production environment.

## Reference Implementation - Amazon Web Services (AWS)

This leads to a reference architecture that anyone can build out using Amazon Web Services (AWS):

![Reference Architecture](./docs/images/ReferenceArchitecture.png)

A very inexpensive data warehouse can be simulated using AWS Athena - a serverless SQL engine that only incurrs a job based on how much data is being read. At idle, there is no charge.

Test data can be loaded directly into S3 as .csv files. SAP has open sourced [several test data sets under their Datasphere brand](https://github.com/SAP-samples/datasphere-content/tree/main).

S3 and Athena can be set up easily using the [AWS Cloud Development kit (CDK)](https://aws.amazon.com/cdk/) infrastructure-as-code found in this repository. The root of this is in `./iac/aws/iac`. This consists of several stacks used to build out the project artifacts:
1. **datalake_stack**: A set of S3 buckets in `us-east-1` and `us-east-2` used for storing the `.csv` files.
2. **scratch_stack**: A second set of S3 buckets with a very short retention policy used for the AWS Athena query output.
3. **analytics_stack**: This creates an AWS Athena database, and loads the schema on top of each set of `.csv` files.
4. **access_stack**: This creates an AWS IAM user that can be used as a service account to execute queries against AWS Athena.  

A very simple MCP server using the Python FastMCP is included in `./src/src/retail_analytics_server.py` This MCP server defines two tools:
1. **get_schema** - this returns the DDL for the test schema to the LLM context
2. **execute_sql** - this will execute an Athena SQL statement and return the results to the context 

This MCP server can be deployed directory from the project repository using [Prefect.io](https://horizon.prefect.io/). Since it is a non-production project, it can be deployed for free.

The MCP server will need six environment variables to deploy on **Prefect.io** properly:
1. **AWS_ACCESS_KEY_ID** - From the service account created in the `access_stack` 
2. **AWS_SECRET_ACCESS_KEY**  - From the service account created in the `access_stack`
3. **ANALYTICS_BUCKET** - From the S3 bucket created in the `datalake_stack` above 
4. **AWS_REGION** - If the default settings are used in th CDK deployment above, this should be `us-east-2`
5. **ANALYTICS_OUTPUT_BUCKET**  - From the S3 bucket created in the `scratch_stack` above
6. **RETAIL_DATABASE_NAME** - The Athena database created in the `analytics_stack` above. 

If deployed properly, Prefect.io will provide an endpoint to the server, which you can then easily plug in to Claude desktop using the 'Connectors' context menu.

The second MCP server is the general GitHub MCP server. If this is plugged into Claude, it will allow claude to create issues, add new code to branches, and create pull request which can be assigned to human reviewers.

The final component is a simple Javascript D3 dashboard, which can be deployed as an [AWS Amplify](https://aws.amazon.com/amplify/) application. This can be found under `./ui`. The deployment to Amplify is just as simple as the deployment to Perfect.io - point it at the repository, and AWS Amplify will handle all the deployment details, including when the application in the repository is updated. 