import streamlit as st
from openai import OpenAI
import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

def hw5():

    if 'openai_client' not in st.session_state or 'HW4_VectorDB' not in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_HW4')
        collection = chroma_client.get_or_create_collection('HW4Collection')
        st.session_state.HW4_VectorDB = collection

    def relevant_club_info(query):
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=query,
            model='text-embedding-3-small'
        )
        query_embedding = response.data[0].embedding

        results = st.session_state.HW4_VectorDB.query(
            query_embeddings=[query_embedding],
            n_results=5
        )

        context = ""
        for doc in results['documents'][0]:
            context += doc + "\n\n---\n\n"

        return context
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "relevant_club_info",
                "description": "Search the Syracuse University student organization database for clubs and organizations relevant to the query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant student organizations"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    st.title('HW 5: Enhanced iSchool Chatbot')
    st.caption("Ask me about student organizations at Syracuse University!")

    if 'hw5_messages' not in st.session_state:
        st.session_state.hw5_messages = []

    for message in st.session_state.hw5_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about SU student organizations..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.hw5_messages.append({"role": "user", "content": prompt})

        buffered_messages = st.session_state.hw5_messages[-10:]

        messages_to_send = [
            {"role": "system", "content": "You are a helpful chatbot that answers questions about student organizations at Syracuse University. Use the relevant_club_info function to look up information when needed."},
        ]
        messages_to_send.extend(buffered_messages)

        client = st.session_state.openai_client
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_to_send,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            query = json.loads(tool_call.function.arguments)["query"]
            context = relevant_club_info(query)

            messages_to_send.append(response_message)
            messages_to_send.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": context
            })

            final_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_to_send,
                stream=True
            )

            with st.chat_message("assistant"):
                response_text = st.write_stream(final_response)
        else:
            with st.chat_message("assistant"):
                response_text = response_message.content
                st.markdown(response_text)

        st.session_state.hw5_messages.append({"role": "assistant", "content": response_text})