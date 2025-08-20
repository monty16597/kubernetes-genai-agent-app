import re
import asyncio
import streamlit as st
from langchain_core.messages import ToolMessage
from agent_controller import AgentController
from model import get_dynamodb_table, save_item_to_db, get_all_items, delete_item, get_item

st.set_page_config(layout="wide", page_title="Resources Dashboard")


# Cache AgentController
@st.cache_resource
def get_agent_controller():
    return AgentController()


# Initialize DynamoDB table
try:
    table = get_dynamodb_table()
except RuntimeError as e:
    st.error(str(e))
    table = None


def content_writer(placeholder, chunk):
    """Write content to the Streamlit placeholder."""
    if "structured_response" in chunk:
        placeholder.markdown("#### Output")
        placeholder.markdown(f"```\n{chunk['structured_response']}\n```")
        placeholder.markdown("-----")
    elif (
        chunk["messages"][-1]
        and isinstance(chunk["messages"][-1], ToolMessage)
        and chunk["messages"][-1].name == "get_kubernetes_resource_schema"
    ):
        match = re.search(r"KIND:\s*(\S+)", chunk["messages"][-1].content)
        resource_type = match.group(1) if match else None
        placeholder.markdown("#### Schema Retrieved from MCP Tool")
        placeholder.markdown(f"Resource Type: {resource_type}")
        placeholder.markdown("-----")
    else:
        if chunk["messages"][-1].content.strip():
            placeholder.markdown(f"#### {chunk['messages'][-1].type}")
            placeholder.markdown(chunk["messages"][-1].content.strip())
            placeholder.markdown("-----")


async def save_item(name: str, instructions: str, placeholder=None):
    """Save item to DB and process via AgentController."""
    agent_controller = get_agent_controller()
    await agent_controller.init_async()

    if not table:
        st.error("No DynamoDB connection.")
        return False

    try:
        if agent_controller:
            if placeholder:
                placeholder.info(f"Processing '{name}'...")
                async for chunk in agent_controller.invoke_stream(query=instructions):
                    content_writer(placeholder, chunk)
                else:
                    if "structured_response" in chunk:
                        save_item_to_db(table, name, instructions, chunk["structured_response"])
                    else:
                        save_item_to_db(table, name, instructions, chunk["messages"][-1].content)

            placeholder.success(f"Finished processing '{name}' ✅")
            st.rerun()
    except Exception as e:
        st.error(f"Error during save: {e}")
        return False


async def delete_item_from_cluster(item, placeholder=None):
    """Delete an item from the Kubernetes cluster via AgentController with UI updates."""
    agent_controller = get_agent_controller()
    await agent_controller.init_async()

    if not table:
        st.error("No DynamoDB connection.")
        return False

    try:
        if agent_controller:
            if placeholder:
                placeholder.info(f"Deleting resources for '{item['name']}'...")
                async for chunk in agent_controller.invoke_stream(
                    query=f"delete all the newly created resources which are mentioned in: {item}"
                ):
                    content_writer(placeholder, chunk)
                placeholder.success(f"Finished deleting resources for '{item['name']}' ✅")
    except Exception as e:
        st.error(f"Error during delete: {e}")
        return False


# UI rendering
st.title("Resources")

if table:
    # Create New Resource Button
    top_cols = st.columns([0.85, 0.15])
    with top_cols[1]:
        if st.button("➕ Create New Resource", use_container_width=True, type="primary"):
            st.session_state.show_creation_dialog = True

    if "show_creation_dialog" not in st.session_state:
        st.session_state.show_creation_dialog = False

    # New Resource Form
    if st.session_state.show_creation_dialog:
        with st.form("new_resource_form"):
            st.subheader("Create a New Resource")
            new_name = st.text_input("Resource Name", key="new_name")
            new_instructions = st.text_area("Instructions", height=200, key="new_instructions")
            submitted = st.form_submit_button("Save Resource")
            if submitted:
                if not new_name or not new_instructions:
                    st.warning("Name and instructions cannot be empty.")
                else:
                    output_placeholder = st.container()
                    asyncio.run(save_item(new_name, new_instructions, placeholder=output_placeholder))
                    st.session_state.show_creation_dialog = False

    st.markdown("---")

    # Display Items
    try:
        items = get_all_items(table)
    except RuntimeError as e:
        st.error(str(e))
        items = []

    if not items:
        st.info("No resources found.")
    else:
        num_columns = 3
        cols = st.columns(num_columns)
        for i, item in enumerate(items):
            with cols[i % num_columns]:
                with st.container(border=True):
                    header_cols = st.columns([0.8, 0.2])
                    with header_cols[0]:
                        st.subheader(item['name'])
                    with header_cols[1]:
                        with st.popover("⋮"):
                            if st.button("Delete", key=f"delete_{item['name']}", type="secondary", use_container_width=True):
                                output_placeholder = st.container()
                                try:
                                    item_data = get_item(table, item['name'])
                                except RuntimeError as e:
                                    st.error(str(e))
                                    item_data = None
                                if item_data:
                                    asyncio.run(delete_item_from_cluster(item_data, placeholder=output_placeholder))
                                    try:
                                        delete_item(table, item['name'])
                                        st.toast(f"Resource '{item['name']}' deleted. 🗑️", icon="👋")
                                    except RuntimeError as e:
                                        st.error(str(e))
                                    st.rerun()

                    st.write(item['instructions'])
                    st.write(item['resources'])

else:
    st.error("Application cannot start without DynamoDB.")
