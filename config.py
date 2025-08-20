from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from typing import Annotated, Any, List
from typing_extensions import TypedDict
import os
import dotenv
dotenv.load_dotenv()

mcp_servers = {
    "kubernetes_operations": {
        "command": "npx",
        "args": ["mcp-server-kubernetes"],
        "transport": "stdio",
    }
}


class KubernetesResourcesFormate(TypedDict):
    resource_name: Annotated[str, "The name of the Kubernetes resource to be created or modified."]
    resource_type: Annotated[str, "The type of Kubernetes resource to be created or modified."]
    namespace: Annotated[str, "The namespace in which the resource resides."]
    manifest_file: Annotated[Any, "Manifest content of the resource, parsed from YAML to dict."]
    error_message: Annotated[str, "Any error message encountered during creation of the resource."] = None


class QueryResponseFormat(TypedDict):
    """
    A Pydantic model to define the expected format of the query response.
    This can be extended based on the specific requirements of the MCP server.
    """
    created_resources: Annotated[List[KubernetesResourcesFormate], "List of Kubernetes resources which have been created in the query. It doesn't include any existing resources."] = []


LLM_MODEL_PROVIDER = os.getenv("LLM_MODEL_PROVIDER", None)
if LLM_MODEL_PROVIDER is None:
    LLM_MODEL_PROVIDER = "google"
elif LLM_MODEL_PROVIDER not in ["google", "huggingface"]:
    raise ValueError(f"Invalid LLM_MODEL_PROVIDER: {LLM_MODEL_PROVIDER}")


def get_llm():
    llm = None
    if LLM_MODEL_PROVIDER == "google":
        if "GOOGLE_API_KEY" not in os.environ:
            raise RuntimeError("GOOGLE_API_KEY environment variable is not set when LLM_MODEL_PROVIDER is 'google'. Check out https://aistudio.google.com/apikey ")
        print("Using Google as LLM provider")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=5,
        )
    elif LLM_MODEL_PROVIDER == "huggingface":
        print("Using HuggingFace as LLM provider")
        print("Make sure you have properlly configured huggingface-cli in your local machine. Checkout https://huggingface.co/docs/huggingface_hub/en/guides/cli#command-line-interface-cli")
        hg = HuggingFaceEndpoint(
            repo_id="openai/gpt-oss-20b",
            temperature=0.7,
            max_length=512,
        )
        llm = ChatHuggingFace(llm=hg)
    return llm
