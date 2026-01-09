import os
from dotenv import load_dotenv

import streamlit as st
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="AI Assistant Agent", page_icon="🤖")
st.title("🤖 AI Assistant Agent")

# --- Sidebar diagnostics ---
st.sidebar.header("Diagnostics")
api_key = os.getenv("OPENAI_API_KEY", "")
st.sidebar.write("API key loaded:", bool(api_key) and api_key.startswith("sk-"))
model = st.sidebar.text_input("Model", value="gpt-4o-mini")

if st.sidebar.button("Clear chat"):
    st.session_state.pop("messages", None)
    st.rerun()

if not api_key:
    st.error("OPENAI_API_KEY not found. Make sure .env is in the project root and contains OPENAI_API_KEY=sk-...")
    st.stop()

client = OpenAI(api_key=api_key)

# --- Chat state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hey! Ask me anything."}
    ]

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
user_input = st.chat_input("Ask me something...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Print to terminal for debugging
                print("Calling OpenAI model:", model)

                resp = client.chat.completions.create(
                    model=model,
                    messages=st.session_state.messages,
                    timeout=30,  # prevents infinite hang
                )

                assistant_text = (resp.choices[0].message.content or "").strip()

                if not assistant_text:
                    assistant_text = "I got an empty response from the API. Try again, or switch the model in the sidebar."

                st.write(assistant_text)
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})

            except Exception as e:
                # Show full error in UI + terminal
                print("OpenAI API error:", repr(e))
                st.error(f"OpenAI API error: {repr(e)}")


