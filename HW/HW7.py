import streamlit as st
import sys
import json
from openai import OpenAI
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb

def hw7():

    st.title('HW 7: Law Firm News Monitor')
    st.caption("Ask about client news. Try: 'Find the most interesting news' or 'Find news about JPMorgan'")

    # ---- OPENAI CLIENT ----
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

        with st.sidebar:
            st.header("Settings")
            use_advanced = st.checkbox("Use advanced model (GPT-4.1)", value=False)
            model = 'gpt-4.1' if use_advanced else 'gpt-4.1-mini'
            st.caption(f"Current model: {model}")

     # ---- LOAD CHROMADB (only once per session) ----
    if 'HW7_VectorDB' not in st.session_state:
        chroma_client = chromadb.PersistentClient(path='./news_chroma_db')
        collection = chroma_client.get_collection('news_articles')
        st.session_state.HW7_VectorDB = collection

    collection = st.session_state.HW7_VectorDB

    # ---- HELPER: Embed a query string ----
    def embed_query(text):
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=[text],
            model='text-embedding-3-small'
        )
        return response.data[0].embedding

    # ---- HELPER: Format ChromaDB results for the LLM ----
    def format_results(results):
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        output = []
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            output.append(
                f"[Article {i+1}]\n"
                f"Company: {meta['company']}\n"
                f"Date: {meta['date'][:10]}\n"
                f"URL: {meta['url']}\n"
                f"Content: {doc[:500]}\n"
            )
        return "\n---\n".join(output)
    
    def find_interesting_news(n=5):
        query_vec = embed_query(
            "significant legal regulatory financial risk lawsuit controversy scandal"
        )
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=n * 2,
            include=['documents', 'metadatas', 'distances']
        )
        return format_results(results)

    # ---- TOOL: Find news about a specific company or topic ----
    def find_news_about(query, n=5):
        query_vec = embed_query(query)
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=n * 2,
            include=['documents', 'metadatas', 'distances']
        )
        return format_results(results)
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "find_interesting_news",
                "description": "Retrieves the most newsworthy and interesting articles across all clients. Use when the user asks for interesting news, top news, or what's happening.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "n": {"type": "integer", "description": "Number of articles to return (default 5)"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_news_about",
                "description": "Retrieves news articles about a specific company or topic. Use when the user asks about a particular company or subject.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The company name or topic to search for"},
                        "n": {"type": "integer", "description": "Number of articles to return (default 5)"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # ---- SYSTEM PROMPT ----
system_prompt = """You are a news intelligence assistant for a large global law firm.
Your job is to help lawyers stay informed about their clients' recent news.

When asked for news:
- Return a ranked numbered list (most to least newsworthy)
- Briefly explain WHY each article is interesting or legally relevant
- Focus on: lawsuits, regulatory actions, financial risk, scandals, major deals

When asked about a specific company or topic:
- Summarize the relevant articles
- Highlight anything legally significant

Always include the article date and URL for each result.
Be concise and professional."""


# ---- CHAT SESSION STATE ----
if 'hw7_messages' not in st.session_state:
        st.session_state.hw7_messages = []

    # Display chat history
for msg in st.session_state.hw7_messages:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])


# ---- CHAT INPUT ----
    user_input = st.chat_input("Ask about client news...")

    if user_input:
        # Show user message
        st.session_state.hw7_messages.append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.markdown(user_input)

        with st.chat_message('assistant'):
            with st.spinner('Searching news...'):

                # Build messages for LLM
                messages = [{'role': 'system', 'content': system_prompt}]
                messages += st.session_state.hw7_messages

                # First LLM call - may trigger a tool
                client = st.session_state.openai_client
                response = client.chat.completions.create(
                    model= model,
                    messages=messages,
                    tools= tools,
                    tool_choice='auto'
                )

                resp_msg = response.choices[0].message

                # If the LLM wants to call a tool
                if resp_msg.tool_calls:
                    tool_call = resp_msg.tool_calls[0]
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Run the tool (RAG search)
                    if tool_name == 'find_interesting_news':
                        tool_result = find_interesting_news(n=tool_args.get('n', 5))
                    elif tool_name == 'find_news_about':
                        tool_result = find_news_about(
                            query=tool_args['query'],
                            n=tool_args.get('n', 5)
                        )

                    # Second LLM call with tool result
                    messages.append(resp_msg)
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'content': tool_result
                    })

                    final_response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=True
                    )
                    reply = st.write_stream(final_response)

                else:
                    # No tool needed - direct answer
                    reply = resp_msg.content
                    st.markdown(reply)

        st.session_state.hw7_messages.append({'role': 'assistant', 'content': reply})


