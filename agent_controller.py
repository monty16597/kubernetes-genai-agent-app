import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import SystemMessage
from langchain.tools import tool
from typing import Annotated
from langgraph.prebuilt import create_react_agent
from config import mcp_servers, get_llm, QueryResponseFormat
from langchain_huggingface import ChatHuggingFace


@tool
def get_kubernetes_resource_schema(
        resource_type: Annotated[str, "The type of Kubernetes resource to get the schema for, e.g., 'deployment', 'service', etc."]
) -> str:
    """
    This tool retrieves the Kubernetes resource schema for the specified resource type. It will return full schema of a resource type which is supported by configured kuberentes servers.
    Use this tool to get detailed information about the structure and fields of a specific Kubernetes resource and when agents need to generate manifest file.
    """
    schema = os.popen(f"kubectl explain {resource_type} --recursive").read()
    return schema


class AgentController:
    """
    A controller class to manage interactions with the MCP (Micro-Control Plane) server
    using the MCPClient and MCPAgent.
    """
    async def init_async(self):
        """
        Initializes the MCPController with the necessary MCPClient and MCPAgent.

        Args:
            config (dict): Configuration dictionary for the MCP server.
        """

        # Create LLM (Language Model)
        self.llm = get_llm()

        self.mcp_client: MultiServerMCPClient = MultiServerMCPClient(mcp_servers)

        self.available_tools = await self._get_available_tools()
        self.agent = create_react_agent(
            self.llm, self.available_tools, debug=False,
            prompt=SystemMessage("""
                You are an autonomous Kubernetes operator. Never wait for user input.
                If a resource already exists, proceed with the next steps without asking.

                Also these below things you must follow no matter what. It defines your system constraints and you should adhere to them:
                - Use binded tools only to perform any operations.
                - If a namespace exists, skip creation.
                - Always pass namespace into manifest file.
                - First check if resources are existing. If not, then only generate schema. To check if a resource exists, use the `kubectl_get` tool.
                - If apply overwrites, that's okay.
                - Always generate a manifest file, If schema does not exist, then raise an error.
                - When user ask to "create a pod", then generate manifest and use kubectl_apply binded tool to create resource, not kubectl_create_tool.
                Your goal is to complete the user request end-to-end without interruptions.
            """),
            response_format=None if isinstance(self.llm, ChatHuggingFace) else QueryResponseFormat
        )
        print("MCPController initialized successfully.")

    async def _get_available_tools(self):
        available_tools = await self.mcp_client.get_tools()
        available_tools.append(get_kubernetes_resource_schema)
        return available_tools

    async def invoke_stream(self, query: str):
        input_messages = [
            {"role": "user", "content": f"{query}"}
        ]
        async for chunk in self.agent.astream({"messages": input_messages}, stream_mode="values", debug=False, config={"recursion_limit": 100}):
            yield chunk
