import streamlit as st
from openai import OpenAI
import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

# A fix for working with ChromaDB on Streamlit Community Cloud
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

def hw4():

    #### Using ChromaDB with OpenAI Embeddings for Student Orgs ####

    # Create OpenAI Client
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

    # ===================================================================
    # FUNCTION: Add a document to the ChromaDB collection
    # ===================================================================
    # Same as Lab 4 — generates an embedding and stores it with the text
    def add_to_collection(collection, text, doc_id):
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=text,
            model='text-embedding-3-small'
        )
        embedding = response.data[0].embedding

        collection.add(
            documents=[text],
            ids=[doc_id],
            embeddings=[embedding]
        )

    # ===================================================================
    # FUNCTION: Extract organization data from an HTML file
    # ===================================================================
    # Each HTML file contains a JSON blob in window.initialAppState
    # with all the org info. We parse the JSON and extract useful fields.
    def extract_org_data(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the JSON blob in the script tag
        match = re.search(r'window\.initialAppState\s*=\s*({.*?});\s*</script>', content, re.DOTALL)
        if not match:
            return None

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        org = data.get('preFetchedData', {}).get('organization')
        if not org:
            return None

        # Clean HTML tags from the description field using BeautifulSoup
        raw_description = org.get('description', '') or ''
        clean_description = BeautifulSoup(raw_description, 'html.parser').get_text(separator=' ').strip()

        # Extract contact info
        contact = org.get('primaryContact', {}) or {}
        contact_info_list = org.get('contactInfo', []) or []
        social = org.get('socialMedia', {}) or {}

        # Build contact details string
        contact_parts = []
        if contact.get('firstName') or contact.get('lastName'):
            name = f"{contact.get('preferredFirstName') or contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
            contact_parts.append(f"Primary Contact: {name}")
        if org.get('email'):
            contact_parts.append(f"Email: {org['email']}")
        if contact_info_list:
            ci = contact_info_list[0]
            if ci.get('phoneNumber'):
                contact_parts.append(f"Phone: {ci['phoneNumber']}")
            addr_parts = [ci.get('street1', ''), ci.get('city', ''), ci.get('state', ''), ci.get('zip', '')]
            address = ', '.join(p.strip() for p in addr_parts if p and p.strip())
            if address:
                contact_parts.append(f"Address: {address}")
        if social.get('externalWebsite'):
            contact_parts.append(f"Website: {social['externalWebsite']}")
        social_links = []
        for platform in ['instagramUrl', 'facebookUrl', 'twitterUrl', 'linkedInUrl', 'youtubeUrl']:
            if social.get(platform):
                social_links.append(social[platform])
        if social_links:
            contact_parts.append(f"Social Media: {', '.join(social_links)}")

        return {
            'name': org.get('name', 'Unknown'),
            'short_name': org.get('shortName', ''),
            'summary': org.get('summary', '') or '',
            'description': clean_description,
            'status': org.get('status', ''),
            'org_type': (org.get('organizationType', {}) or {}).get('name', ''),
            'contact_details': '\n'.join(contact_parts),
            'file_name': Path(html_path).stem  # filename without extension
        }

    # ===================================================================
    # CHUNKING STRATEGY: Split each org into 2 mini-documents
    # ===================================================================
    # Method: Semantic chunking — splitting by content type
    #
    # Chunk 1 (Identity & Description): Contains the org's name, type,
    #   status, summary, and full description. This chunk answers
    #   "what is this organization?" and "what do they do?"
    #
    # Chunk 2 (Contact & Details): Contains the org's name (repeated
    #   for context), contact person, email, phone, address, website,
    #   and social media. This chunk answers "how do I reach them?"
    #
    # WHY this method: Semantic chunking groups related information
    # together, so vector search returns the most relevant chunk for
    # a given question type. A simple midpoint split could break a
    # sentence in half or mix unrelated info. With 513 orgs (1026
    # chunks), keeping chunks focused improves search accuracy.

    def chunk_org_data(org_data):
        name = org_data['name']
        short = f" ({org_data['short_name']})" if org_data['short_name'] else ""

        # Chunk 1: Identity & Description
        chunk1_parts = [
            f"Organization: {name}{short}",
            f"Type: {org_data['org_type']}" if org_data['org_type'] else "",
            f"Status: {org_data['status']}" if org_data['status'] else "",
            f"Summary: {org_data['summary']}" if org_data['summary'] else "",
            f"Description: {org_data['description']}" if org_data['description'] else "",
        ]
        chunk1 = '\n'.join(p for p in chunk1_parts if p)

        # Chunk 2: Contact & Details
        chunk2_parts = [
            f"Organization: {name}{short}",
            org_data['contact_details'] if org_data['contact_details'] else "No contact information available.",
        ]
        chunk2 = '\n'.join(p for p in chunk2_parts if p)

        return chunk1, chunk2

    # ===================================================================
    # FUNCTION: Load all HTML files into the collection
    # ===================================================================
    def load_html_to_collection(folder_path, collection):
        html_folder = Path(folder_path)
        html_files = list(html_folder.glob('*.html'))
        loaded = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, html_file in enumerate(html_files):
            org_data = extract_org_data(html_file)
            if org_data:
                chunk1, chunk2 = chunk_org_data(org_data)
                file_id = org_data['file_name']

                # Add both chunks with unique IDs
                add_to_collection(collection, chunk1, f"{file_id}_identity")
                add_to_collection(collection, chunk2, f"{file_id}_contact")
                loaded += 1

            # Update progress
            progress_bar.progress((i + 1) / len(html_files))
            status_text.text(f"Processing {i + 1}/{len(html_files)} files...")

        progress_bar.empty()
        status_text.empty()
        return loaded

    # ===================================================================
    # CREATE / RETRIEVE THE CHROMADB COLLECTION
    # ===================================================================
    # Only create the vector DB if it does not already exist.
    # This avoids re-embedding 1026 chunks on every app rerun.
    if 'HW4_VectorDB' not in st.session_state:
        chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_HW4')
        collection = chroma_client.get_or_create_collection('HW4Collection')

        if collection.count() == 0:
            st.info("Building vector database from student org files... This only happens once.")
            loaded = load_html_to_collection('./su_orgs/', collection)
            st.success(f"Loaded {loaded} organizations ({loaded * 2} chunks) into the vector database!")

        st.session_state.HW4_VectorDB = collection

    # ===================================================================
    # MAIN APP — Chat Interface with RAG
    # ===================================================================
    st.title('HW 4: iSchool Chatbot — SU Student Organizations')
    st.caption("Ask me about student organizations at Syracuse University!")

    # Initialize chat history
    if 'hw4_messages' not in st.session_state:
        st.session_state.hw4_messages = []

    # Display previous messages
    for message in st.session_state.hw4_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about SU student organizations..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.hw4_messages.append({"role": "user", "content": prompt})

        # ---- CONVERSATION BUFFER: Keep last 5 interactions ----
        # An "interaction" = 1 user message + 1 assistant response = 2 messages
        # So we keep the last 10 messages (5 pairs)
        buffered_messages = st.session_state.hw4_messages[-10:]

        # ---- RAG: Query the vector DB for relevant context ----
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=prompt,
            model='text-embedding-3-small'
        )
        query_embedding = response.data[0].embedding

        results = st.session_state.HW4_VectorDB.query(
            query_embeddings=[query_embedding],
            n_results=5  # Top 5 chunks for broader coverage
        )

        # Build context from matching chunks
        context = ""
        for i in range(len(results['documents'][0])):
            context += results['documents'][0][i] + "\n\n---\n\n"

        # ---- Send to LLM with RAG context + buffered history ----
        system_prompt = (
            "You are a helpful chatbot that answers questions about student organizations "
            "at Syracuse University. Use the following context retrieved from the student "
            "organization database to answer the user's question. If the context doesn't "
            "contain enough information to fully answer, say so honestly. Be friendly and "
            "helpful.\n\n"
            "CONTEXT:\n" + context
        )

        messages_to_send = [
            {"role": "system", "content": system_prompt},
        ]
        messages_to_send.extend(buffered_messages)

        # Stream the response
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_to_send,
                stream=True
            )
            response_text = st.write_stream(stream)

        st.session_state.hw4_messages.append({"role": "assistant", "content": response_text})