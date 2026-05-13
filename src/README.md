# Retail analytics MCP server

This is a reference implementation of a simple retail analytics MCP server using the FastMCP framework. The intent is to demonstrate how to build a retail analytics decision support agent.

## Deployment

The quickest deployment path is to use [FastMCP Cloud](https://fastmcp.cloud/) to deploy this repository as a remote MCP server:

1. Fork this repository
2. Sign up for a free [FastMCP Cloud](https://fastmcp.cloud/) account.
3. [FastMCP Cloud](https://fastmcp.cloud/) will ask for access to your forked repository. It will deploy as a remote MCP server, and return the MCP endpoint.

![alt text](./img/mcp_img1.png)

## Usage

Once the server is successfully deployed, it can be used with any of the GenAI providers that allow a remote MCP server to be used as a tool. For example, Claude desktop:

1. On the Claude Desktop UI, select the "Search and Tools" button:
2. On the context menu, scroll down to "Manage Connectors"
3. Select "Add custom connector". On the "Add custom connector" form, add a name for the MCP server, and add the URL to the MCP server provided by FastMCP Cloud. 

## Testing

1. Once connected, you can use the natural language chat interface to help develop and execute analytic reports. See below for some sample prompts.

![alt text](./img/mcp_claude_img2.png)

![alt text](./img/mcp_claude_img3.png)