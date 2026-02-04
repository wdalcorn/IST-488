import streamlit as st
from openai import OpenAI
from anthropic import Anthropic
import requests
from bs4 import BeautifulSoup

def read_url_content(url):
    """
    Fetch and extract text content from a URL
    """
    if not url or url.strip() == "":
        return ""
    
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    except Exception as e:
        st.error(f"Error fetching URL: {str(e)}")
        return ""

def hw3():
    st.title("🤖 HW3 - Chatbot with URL Context")
    
    # Add description at the top
    st.write("""
    ### How This Chatbot Works
    
    This chatbot allows you to have conversations informed by web content:
    
    - **URL Input**: Provide up to 2 URLs whose content will be used as context
    - **LLM Selection**: Choose between OpenAI GPT-4o and Anthropic Claude Sonnet 4.5
    - **Conversation Memory**: Uses a 6-message buffer (3 user-assistant exchanges) to maintain context
    - **System Prompt**: URL content is embedded in the system prompt and never discarded
    
    The chatbot will answer questions based on the provided URLs while maintaining conversational memory.
    """)
    
    # Initialize API clients from secrets
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("Please add your OPENAI_API_KEY to Streamlit secrets!")
        st.stop()
    
    if "ANTHROPIC_API_KEY" not in st.secrets:
        st.error("Please add your ANTHROPIC_API_KEY to Streamlit secrets!")
        st.stop()
    
    openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    
    # Initialize session state for storing messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar with configuration and controls
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # LLM Vendor Selection
        st.subheader("🤖 LLM Selection")
        llm_vendor = st.selectbox(
            "Select LLM Vendor",
            ["OpenAI (GPT-4o)", "Anthropic (Claude Sonnet 4.5)"],
            help="Choose which AI model to use for responses"
        )
        
        st.divider()
        
        # URL inputs
        st.subheader("📄 Document Context")
        url1 = st.text_input("URL 1 (optional)", 
                             placeholder="https://example.com/article1",
                             help="Paste a URL to use as context")
        url2 = st.text_input("URL 2 (optional)", 
                             placeholder="https://example.com/article2",
                             help="Paste a second URL for additional context")
        
        # Fetch URL content button
        if st.button("📥 Load URL Content"):
            with st.spinner("Fetching content..."):
                if url1:
                    content1 = read_url_content(url1)
                    if content1:
                        st.session_state.url1_content = content1[:3000]  # Limit to 3000 chars
                        st.success("✓ URL 1 loaded")
                
                if url2:
                    content2 = read_url_content(url2)
                    if content2:
                        st.session_state.url2_content = content2[:3000]
                        st.success("✓ URL 2 loaded")
        
        # Show loaded URLs status
        if "url1_content" in st.session_state:
            st.info(f"✓ URL 1 loaded ({len(st.session_state.url1_content)} chars)")
        if "url2_content" in st.session_state:
            st.info(f"✓ URL 2 loaded ({len(st.session_state.url2_content)} chars)")
        
        st.divider()
        
        st.header("💬 Chat Controls")
        st.write(f"**Total messages:** {len(st.session_state.messages)}")
        st.write(f"**Messages in buffer:** {min(4, len(st.session_state.messages))}")
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            # Clear URL content too
            if "url1_content" in st.session_state:
                del st.session_state.url1_content
            if "url2_content" in st.session_state:
                del st.session_state.url2_content
            st.rerun()
    
    # Create system prompt with URL context
    def get_system_prompt():
        prompt = """You are a helpful assistant. Answer questions based on the provided context when relevant."""
        
        if "url1_content" in st.session_state:
            prompt += f"\n\nContext from URL 1:\n{st.session_state.url1_content}"
        
        if "url2_content" in st.session_state:
            prompt += f"\n\nContext from URL 2:\n{st.session_state.url2_content}"
        
        return {"role": "system", "content": prompt}
    
    # Display all previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Function to get buffered messages (last 6 messages = 3 exchanges)
    def get_buffered_messages():
        system_prompt = get_system_prompt()
        buffered = [system_prompt]  # Always include system prompt
        
        # Get last 6 messages (3 user + 3 assistant = 3 exchanges)
        recent = st.session_state.messages[-6:] if len(st.session_state.messages) > 6 else st.session_state.messages
        
        buffered.extend(recent)
        return buffered
    
    # Get user input
    if prompt := st.chat_input("Ask a question about the URLs or anything else..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get buffered messages
        messages_to_send = get_buffered_messages()
        
        # Generate response with streaming based on selected vendor
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            if llm_vendor == "OpenAI (GPT-4o)":
                # OpenAI API call
                stream = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_to_send,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
            else:  # Anthropic Claude
                # Convert messages format for Anthropic (system separate from messages)
                system_content = messages_to_send[0]["content"]
                anthropic_messages = messages_to_send[1:]  # All except system
                
                # Anthropic API call
                with anthropic_client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system_content,
                    messages=anthropic_messages
                ) as stream:
                    for text in stream.text_stream:
                        full_response += text
                        message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    hw3()