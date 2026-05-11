#!/bin/bash

# Required:
# 1. aws CLI tools
# 2. aws credentials
# 3. ECR target repository

aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $ECR_TARGET
docker push $ECR_TARGET/$ECR_MCP_TARGET/retail_analytics_mcp_server:latest