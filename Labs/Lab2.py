def lab2():
    import streamlit as st
    from openai import OpenAI
    import fitz

    # Show title and description.
    st.title("Lab 2 - Document Summarizer")
    st.write(
        "Upload a document below and ask a question about it – GPT will answer! "
    )

    # Get API key from secrets
    openai_api_key = st.secrets["OPENAI_API_KEY"]


        # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Sidebar for options
    st.sidebar.header("Summary Options")

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

    # Model selection
    use_advanced_model = st.sidebar.checkbox("Use advanced model (GPT-4o)")

    if use_advanced_model:
        model = "gpt-4o"
    else:
        model = "gpt-4o-mini"

        # Let the user upload a file via `st.file_uploader`.
    uploaded_file = st.file_uploader(
            "Upload a document (.txt or .pdf)", type=("txt", "pdf")
        )
    if uploaded_file: 
            # Process the uploaded file
            file_extension = uploaded_file.name.split('.')[-1]
            if file_extension == 'txt':
                document = uploaded_file.read().decode()
            elif file_extension == 'pdf':
                # Read PDF using PyMuPDF
                pdf_bytes = uploaded_file.read()
                pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                document = ""
                for page in pdf_document:
                    document += page.get_text()
            else:
                st.error("Unsupported file type.")
                document = None

    if uploaded_file and document:
    
            messages = [
                {
                    "role": "user",
                    "content": f"{summary_type} in {language}.\n\nDocument:\n{document}",
                }
            ]

            # Generate an answer using the OpenAI API.
            stream = client.chat.completions.create(
                model= model,
                messages=messages,
                stream=True,
            )

            # Stream the response to the app using `st.write_stream`.
            st.write_stream(stream)