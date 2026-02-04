import streamlit as st
from openai import OpenAI

def lab3():
    st.title("🤖 Lab 3 - Chatbot with Memory")
    
    # Initialize OpenAI client from secrets
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("Please add your OPENAI_API_KEY to Streamlit secrets!")
        st.stop()
    
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    
    # System prompt - tells the bot how to behave
    SYSTEM_PROMPT = {
        "role": "system",
        "content": """You are a helpful assistant that explains things in a way that a 10-year-old can understand. 
        Use simple words and fun examples. 
        
        After answering each question, ALWAYS ask "Do you want more info?"
        
        If the user says yes (or variations like "yeah", "sure", "tell me more"):
        - Provide additional details about the topic
        - Then ask again: "Do you want more info?"
        
        If the user says no (or variations like "nope", "I'm good"):
        - Ask "What else can I help you with?"
        
        Keep your answers friendly, simple, and easy to understand."""
    }
    
    # Initialize session state for storing messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display all previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Function to get buffered messages (last 2 exchanges)
    def get_buffered_messages():
        buffered = [SYSTEM_PROMPT]  # Always include system prompt
        
        # Get last 4 messages (2 user + 2 assistant)
        recent = st.session_state.messages[-4:] if len(st.session_state.messages) > 4 else st.session_state.messages
        
        buffered.extend(recent)
        return buffered
    
    # Get user input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get buffered messages
        messages_to_send = get_buffered_messages()
        
        # Generate response with streaming
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_to_send,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Sidebar with chat controls
    with st.sidebar:
        st.header("💬 Chat Controls")
        st.write(f"**Total messages:** {len(st.session_state.messages)}")
        st.write(f"**Messages in buffer:** {min(4, len(st.session_state.messages))}")
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()