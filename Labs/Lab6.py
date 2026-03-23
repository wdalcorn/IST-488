import streamlit as st
from openai import OpenAI
from pydantic import BaseModel

class ResearchSummary(BaseModel):
    main_answer: str
    key_facts: list[str]
    source_hint: str

def lab6():
    st.title("Lab 6 - OpenAI Responses API Agent")
    st.write("A multi-turn research agent powered by the OpenAI Responses API.")

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    st.sidebar.caption("ℹ️ This agent has web search enabled.")
    use_structured = st.sidebar.checkbox("Return structured summary")
    use_streaming = st.sidebar.checkbox("Enable streaming")

    
    user_question = st.text_input("Enter your question:")

    if user_question:
        if use_structured:
            response = client.responses.parse(
                model="gpt-4o",
                instructions="You are a helpful research assistant. Cite your sources.",
                input=user_question,
                tools=[{"type": "web_search_preview"}],
                text_format=ResearchSummary,
            )
            st.session_state.last_response_id = response.id
            result = response.output_parsed
            st.markdown(f"**Answer:** {result.main_answer}")
            st.markdown("**Key Facts:**")
            for fact in result.key_facts:
                st.write(f"- {fact}")
            st.caption(f"Source hint: {result.source_hint}")
        else:
            if use_streaming:
                stream = client.responses.create(
                    model="gpt-4o",
                    instructions="You are a helpful research assistant. Cite your sources.",
                    input=user_question,
                    tools=[{"type": "web_search_preview"}],
                    stream=True,
                )
                response_text = ""
                placeholder = st.empty()
                for event in stream:
                    if event.type == "response.output_text.delta":
                        response_text += event.delta
                        placeholder.markdown(response_text)
                    elif event.type == "response.completed":
                        st.session_state.last_response_id = event.response.id
            else:
                response = client.responses.create(
                    model="gpt-4o",
                    instructions="You are a helpful research assistant. Cite your sources.",
                    input=user_question,
                    tools=[{"type": "web_search_preview"}],
                )
                st.markdown(response.output_text)
                st.session_state.last_response_id = response.id

    if st.session_state.get("last_response_id"):
        st.divider()
        st.subheader("Ask a Follow-Up")
        follow_up = st.text_input("Follow-up question:", key="follow_up_input")

        if follow_up:
            follow_response = client.responses.create(
                model="gpt-4o",
                instructions="You are a helpful research assistant. Cite your sources.",
                input=follow_up,
                tools=[{"type": "web_search_preview"}],
                previous_response_id=st.session_state.last_response_id,
            )

            st.session_state.last_response_id = follow_response.id
            st.markdown(follow_response.output_text)