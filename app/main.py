import os
import json
from dotenv import load_dotenv

import streamlit as st
from openai import OpenAI

from app.storage import (
    init_db,
    add_note, list_notes, search_notes,
    add_task, list_tasks, close_task,
    set_memory, all_memory
)

load_dotenv()
init_db()

st.set_page_config(page_title="AI Assistant Agent", page_icon="🤖")
st.title("🤖 AI Assistant Agent")
st.caption("Now with long-term memory + tools (notes + tasks)")

# --- Sidebar: Diagnostics + Tools UI ---
st.sidebar.header("Diagnostics")
api_key = os.getenv("OPENAI_API_KEY", "")
st.sidebar.write("API key loaded:", bool(api_key) and api_key.startswith("sk-"))
model = st.sidebar.text_input("Model", value="gpt-4o-mini")

if not api_key:
    st.error("Missing OPENAI_API_KEY. Ensure .env is in project root with OPENAI_API_KEY=sk-...")
    st.stop()

client = OpenAI(api_key=api_key)

st.sidebar.divider()
st.sidebar.header("Tools")

# Notes tool (manual UI)
with st.sidebar.expander("🗒 Notes", expanded=False):
    note_text = st.text_area("New note", placeholder="Example: My trading rules: only trade 9:30–11:30...", height=100)
    if st.button("Save note"):
        if note_text.strip():
            nid = add_note(note_text)
            st.success(f"Saved note #{nid}")
        else:
            st.warning("Note is empty.")

    q = st.text_input("Search notes")
    if st.button("Search"):
        results = search_notes(q) if q.strip() else list_notes()
        st.write(f"Showing {len(results)} results")
        for r in results:
            st.markdown(f"**#{r['id']}** — {r['content']}")
            st.caption(r["created_at"])

# Tasks tool (manual UI)
with st.sidebar.expander("✅ Tasks", expanded=False):
    task_text = st.text_input("New task", placeholder="Example: Backtest NQ 5m unicorn model 20 trades")
    if st.button("Add task"):
        if task_text.strip():
            tid = add_task(task_text)
            st.success(f"Added task #{tid}")
        else:
            st.warning("Task is empty.")

    open_tasks = list_tasks("open")
    st.write(f"Open tasks: {len(open_tasks)}")
    for t in open_tasks[:15]:
        st.markdown(f"**#{t['id']}** — {t['content']}")
    close_id = st.number_input("Mark task ID done", min_value=0, step=1)
    if st.button("Close task"):
        if close_id > 0 and close_task(int(close_id)):
            st.success(f"Closed task #{int(close_id)}")
        else:
            st.warning("Could not close that task ID.")

# Long-term profile memory (manual view)
with st.sidebar.expander("🧠 Profile Memory", expanded=False):
    mem_rows = all_memory()
    if not mem_rows:
        st.info("No long-term memory saved yet.")
    for r in mem_rows:
        st.markdown(f"**{r['key']}**: {r['value']}")
        st.caption(r["updated_at"])

if st.sidebar.button("Clear chat (session only)"):
    st.session_state.pop("messages", None)
    st.rerun()

# --- Chat state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hey — ask me anything. I can also save notes/tasks. Try: 'remember that I prefer visual learning'."}
    ]

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Tool functions the agent can use ---
def tool_add_note(text: str):
    nid = add_note(text)
    return f"Saved note #{nid}."

def tool_add_task(text: str):
    tid = add_task(text)
    return f"Added task #{tid}."

def tool_list_open_tasks():
    tasks = list_tasks("open")
    if not tasks:
        return "No open tasks."
    lines = [f"#{t['id']}: {t['content']}" for t in tasks[:20]]
    return "Open tasks:\n" + "\n".join(lines)

def tool_search_notes(query: str):
    notes = search_notes(query)
    if not notes:
        return "No notes found."
    lines = [f"#{n['id']}: {n['content']}" for n in notes[:10]]
    return "Matching notes:\n" + "\n".join(lines)

def tool_set_memory(key: str, value: str):
    set_memory(key, value)
    return f"Saved memory: {key} = {value}"

TOOLS = {
    "add_note": tool_add_note,
    "add_task": tool_add_task,
    "list_open_tasks": lambda: tool_list_open_tasks(),
    "search_notes": tool_search_notes,
    "set_memory": tool_set_memory,
}

# --- System prompt to enable simple agent/tool use ---
SYSTEM = """
You are an assistant that can optionally use tools.
If a tool is needed, respond ONLY with valid JSON in this form:

{"tool":"TOOL_NAME","args":{...}}

Available tools:
- add_note: {"text": "..."}
- add_task: {"text": "..."}
- list_open_tasks: {}
- search_notes: {"query": "..."}
- set_memory: {"key":"...","value":"..."}

Use set_memory for durable user preferences or facts.
Otherwise, respond normally in plain text.
"""

user_input = st.chat_input("Ask me something... (or ask me to save a note/task)")

if user_input:
    # show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Build messages: SYSTEM + recent convo
                msgs = [{"role": "system", "content": SYSTEM}] + st.session_state.messages[-20:]

                resp = client.chat.completions.create(
                    model=model,
                    messages=msgs,
                    timeout=30,
                )

                raw = (resp.choices[0].message.content or "").strip()

                # Try tool call (JSON-only)
                tool_result = None
                if raw.startswith("{") and raw.endswith("}"):
                    try:
                        obj = json.loads(raw)
                        tool_name = obj.get("tool")
                        args = obj.get("args", {}) or {}
                        if tool_name in TOOLS:
                            fn = TOOLS[tool_name]
                            tool_result = fn(**args) if args else fn()
                        else:
                            tool_result = f"Unknown tool: {tool_name}"
                    except Exception as e:
                        tool_result = f"Tool parse/exec error: {repr(e)}"

                if tool_result is not None:
                    st.write(tool_result)
                    st.session_state.messages.append({"role": "assistant", "content": tool_result})
                else:
                    # normal assistant response
                    if not raw:
                        raw = "I got an empty response. Try again."
                    st.write(raw)
                    st.session_state.messages.append({"role": "assistant", "content": raw})

            except Exception as e:
                st.error(f"OpenAI API error: {repr(e)}")


