import streamlit as st
from openai import OpenAI
import sys
from pathlib import Path
from PyPDF2 import PdfReader

#A fix for working with ChromaDB on Streamlit Community Cloud

__import__ ('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

def lab4():

    #### Using Chroma DB with OpenAI Embeddings ####

    # Create OpenAI Client
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

    # A function that will add documents to collection
    # Collection = collection, already established
    # text = extracted text from PDF files
    # Embeddings inserted into the collection from OpenAI
    def add_to_collection(collection, text, file_name):

        # Create an embedding
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=text,
            model='text-embedding-3-small'
        )

        # Get the embedding
        embedding = response.data[0].embedding

        #Add embedding and document to ChromaDB
        collection.add(
            documents=[text],
            ids=[file_name],
            embeddings=[embedding]
        )


    #### EXTRACT TEXT FROM PDF ####
    #This function extracts text from each syllabus
    # to passs to add_to_collection
    def extract_text_from_pdf(pdf_path):
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text

    #### POPULATE COLLECTION WITH PDFs ####
    # This function uses extract_text_from_pdf
    # and add_to_collection to put syllabi in ChromaDB collection
    def load_pdfs_to_collection(folder_path, collection):
        pdf_folder = Path(folder_path)
        pdf_files = list(pdf_folder.glob('*.pdf'))

        for pdf_file in pdf_files:
            text = extract_text_from_pdf(pdf_file)
            file_name = pdf_file.name
            add_to_collection(collection, text, file_name)

        return len(pdf_files)

    if 'Lab4_VectorDB' not in st.session_state:
        chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_Lab')
        collection = chroma_client.get_or_create_collection('Lab4Collection')
        
        if collection.count() == 0:
            load_pdfs_to_collection('./Labs/Lab-04-Data/', collection)
        
        st.session_state.Lab4_VectorDB = collection

    #### MAIN APP ####
    st.title('Lab 4: Chatbot using RAG')

    # Initialize chat history
    if 'lab4_messages' not in st.session_state:
        st.session_state.lab4_messages = []

    # Display previous messages
    for message in st.session_state.lab4_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask a question about IST courses..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.lab4_messages.append({"role": "user", "content": prompt})

        # Query the vector DB for relevant context
        client = st.session_state.openai_client
        response = client.embeddings.create(
            input=prompt,
            model='text-embedding-3-small'
        )
        query_embedding = response.data[0].embedding

        results = st.session_state.Lab4_VectorDB.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        # Build context from the top 3 matching documents
        context = ""
        for i in range(len(results['documents'][0])):
            context += results['documents'][0][i] + "\n\n"

        # Send to LLM with context in system prompt
        messages_to_send = [
            {"role": "system", "content": "You are a helpful AI assistant. Use the following context to answer the question. If you are using information from the provided context, make that clear in your response.\n\n" + context},
        ]
        messages_to_send.extend(st.session_state.lab4_messages)

        # Stream the response
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_to_send,
                stream=True
            )
            response_text = st.write_stream(stream)

        st.session_state.lab4_messages.append({"role": "assistant", "content": response_text})
