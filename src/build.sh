#!/bin/bash
uv pip freeze > requirements.txt
docker build --network=host --progress=plain --no-cache -t retail_analytics_mcp_server .
docker tag retail_analytics_mcp_server:latest $ECR_TARGET/mcp-servers/retail_analytics_mcp_server:latest
rm requirements.txt