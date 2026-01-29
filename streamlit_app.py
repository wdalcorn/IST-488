import streamlit as st
import Lab1
import Lab2

# Set up the navigation
pg = st.navigation([
    st.Page(Lab2.lab2, title="Lab 2 - Document Summarizer", icon="📄", default=True),
    st.Page(Lab1.lab1, title="Lab 1", icon="🔬")
])

# Run the selected page
pg.run()

