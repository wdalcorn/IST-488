import streamlit as st
import Labs.Lab1 as Lab1
import Labs.Lab2 as Lab2
import HW.HW1 as HW1
import HW.HW2 as HW2

# Set up the navigation with separate sections
pg = st.navigation([
    st.Page(Lab2.lab2, title="Lab 2 - Document Summarizer", icon="📄", default=True),
    st.Page(Lab1.lab1, title="Lab 1", icon="🔬"),
    st.Page(HW2.hw2, title="HW 2 - URL Summarizer", icon="🌐"),
    st.Page(HW1.hw1, title="HW 1", icon="📝")
])

# Run the selected page
pg.run()