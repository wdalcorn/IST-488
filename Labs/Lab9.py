import streamlit as st
import json
import os
from openai import OpenAI
 
# - constants
MEMORY_FILE = 'memories.json'
MAIN_MODEL = 'gpt-4.1-mini'
EXTRACTION_MODEL = 'gpt-4.1-nano'
 
 
def lab9():
    st.title('Chatbot with Long-Term Memory')
 
    # - set up openai client
    client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
 
    # -------------------------
    # Part B: Memory system
    # -------------------------
 
    def load_memories():
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        return []
 
    def save_memories(memories):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memories, f)
 
    # - sidebar: display memories
    st.sidebar.header('Long-Term Memories')
    memories = load_memories()
 
    if memories:
        for memory in memories:
            st.sidebar.write(f'• {memory}')
    else:
        st.sidebar.write('No memories yet. Start chatting!')
 
    if st.sidebar.button('Clear All Memories'):
        save_memories([])
        st.rerun()
 
    # -------------------------
    # Part C: Chatbot
    # -------------------------
 
    # - initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
 
    # - display chat history
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.write(message['content'])
 
    # - build system prompt with injected memories
    def build_system_prompt():
        base_prompt = 'You are a helpful assistant with long-term memory about the user.'
        memories = load_memories()
        if memories:
            memory_str = '\n'.join(f'- {m}' for m in memories)
            return (
                f'{base_prompt}\n\n'
                f'Here are things you remember about this user from past conversations:\n'
                f'{memory_str}'
            )
        return base_prompt
 
    # - extract new memories from the exchange
    def extract_memories(user_message, assistant_response, existing_memories):
        existing_str = '\n'.join(f'- {m}' for m in existing_memories) if existing_memories else 'None'
        extraction_prompt = (
            'You analyze conversations to extract personal facts worth remembering about the user.\n'
            'Extract only NEW facts not already in the existing memories (name, preferences, interests, location, major, job, hobbies, etc.).\n'
            'If there are no new facts, return an empty list.\n'
            'Return ONLY a valid JSON list of strings. No explanation, no markdown, no backticks.\n\n'
            f'Existing memories:\n{existing_str}\n\n'
            f'User message: {user_message}\n'
            f'Assistant response: {assistant_response}'
        )
        try:
            response = client.chat.completions.create(
                model=EXTRACTION_MODEL,
                messages=[{'role': 'user', 'content': extraction_prompt}],
            )
            raw = response.choices[0].message.content.strip()
            new_facts = json.loads(raw)
            if isinstance(new_facts, list):
                return [str(f) for f in new_facts]
        except Exception:
            pass
        return []
 
    # - chat input
    if user_input := st.chat_input('Chat with me...'):
        # - add user message to history
        st.session_state.messages.append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.write(user_input)
 
        # - build messages list with system prompt
        system_prompt = build_system_prompt()
        api_messages = [{'role': 'system', 'content': system_prompt}] + st.session_state.messages
 
        # - stream response
        with st.chat_message('assistant'):
            stream = client.chat.completions.create(
                model=MAIN_MODEL,
                messages=api_messages,
                stream=True,
            )
            assistant_response = st.write_stream(stream)
 
        # - add assistant response to history
        st.session_state.messages.append({'role': 'assistant', 'content': assistant_response})
 
        # - extract and save new memories
        current_memories = load_memories()
        new_facts = extract_memories(user_input, assistant_response, current_memories)
        if new_facts:
            updated_memories = current_memories + new_facts
            save_memories(updated_memories)
            st.rerun()
 
 
lab9()