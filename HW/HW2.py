def hw2():
    import streamlit as st
    from openai import OpenAI
    import anthropic
    import requests
    from bs4 import BeautifulSoup

    # Function to read URL content
    def read_url_content(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text()
        except requests.RequestException as e:
            st.error(f"Error reading {url}: {e}")
            return None

    # Show title and description
    st.title("HW 2 - URL Summarizer with Multiple LLMs")
    st.write("Enter a URL to summarize web content using different LLMs and languages.")

    # URL input
    url = st.text_input("Enter a URL:", placeholder="https://example.com")

    # Get API keys from secrets
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]

    # Sidebar for options
    st.sidebar.header("Summary Options")

    # Language selection
    language = st.sidebar.selectbox(
        "Select language:",
        ["English", "Spanish", "French", "German", "Chinese"]
    )

    # Summary type selection
    summary_type = st.sidebar.selectbox(
        "Select summary format:",
        [
            "Summarize the document in 100 words",
            "Summarize the document in 2 connecting paragraphs",
            "Summarize the document in 5 bullet points"
        ]
    )

    # LLM selection
    st.sidebar.header("LLM Selection")
    
    llm_provider = st.sidebar.selectbox(
        "Choose LLM provider:",
        ["OpenAI", "Anthropic (Claude)"]
    )
    
    use_advanced = st.sidebar.checkbox("Use advanced model", value=False)
    
    # Set model based on provider and checkbox
    if llm_provider == "OpenAI":
        model = "gpt-4o" if use_advanced else "gpt-4o-mini"
    else:  # Anthropic
        model = "claude-opus-4-5-20251101" if use_advanced else "claude-sonnet-4-5-20250929"
    
    st.sidebar.info(f"Using model: {model}")

    # Process URL
    if url:
        if st.button("Generate Summary", type="primary"):
            with st.spinner("Fetching URL content..."):
                content = read_url_content(url)
            
            if content:
                # Truncate if too long
                if len(content) > 10000:
                    content = content[:10000]
                    st.info("Content truncated to 10,000 characters")
                
                # Build the prompt
                prompt = f"""Summarize the following web page content.
{summary_type}
Output your response in {language}.

Content:
{content}
"""
                
                # Generate summary based on selected LLM
                with st.spinner(f"Generating summary with {llm_provider}..."):
                    try:
                        if llm_provider == "OpenAI":
                            client = OpenAI(api_key=openai_api_key)
                            stream = client.chat.completions.create(
                                model=model,
                                messages=[{"role": "user", "content": prompt}],
                                stream=True,
                            )
                            st.write_stream(stream)
                        
                        else:  # Anthropic
                            client = anthropic.Anthropic(api_key=anthropic_api_key)
                            
                            with client.messages.stream(
                                model=model,
                                max_tokens=1024,
                                messages=[
                                    {"role": "user", "content": prompt}
                                ],
                            ) as stream:
                                response_text = ""
                                response_placeholder = st.empty()
                                for text in stream.text_stream:
                                    response_text += text
                                    response_placeholder.write(response_text)
                    
                    except Exception as e:
                        st.error(f"Error generating summary: {e}")
    else:
        st.info("👆 Enter a URL above to get started!")
