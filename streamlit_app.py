import streamlit as st
import Labs.Lab1 as Lab1
import Labs.Lab2 as Lab2
import Labs.Lab3 as Lab3
import Labs.Lab4 as Lab4
import Labs.Lab5 as Lab5
import Labs.Lab6 as Lab6
import Labs.Lab8 as Lab8
import Labs.Lab9 as Lab9
import HW.HW1 as HW1
import HW.HW2 as HW2
import HW.HW3 as HW3
import HW.HW4 as HW4
import HW.HW5 as HW5
import HW.HW7 as HW7

# Set up the navigation with separate sections
pg = st.navigation({
    "Labs": [
        st.Page(Lab9.lab9, title="Long term Memory Boy", default=True),
        st.Page(Lab8.lab8, title="Lab 8 - Image Captioning Bot 📷"),
        st.Page(Lab6.lab6, title="Lab 6 - Responses AI", icon="👾"),
        st.Page(Lab5.lab5, title="Lab 5 - Weather Chatbot", icon="🌤️"),
        st.Page(Lab4.lab4, title="Lab 4 - Chatbot using RAG", icon="🔍"),
        st.Page(Lab3.lab3, title="Lab 3 - Chatbot", icon="🤖"),
        st.Page(Lab2.lab2, title="Lab 2 - Document Summarizer", icon="📄"),
        st.Page(Lab1.lab1, title="Lab 1", icon="🔬"),
    ],
    "Homework": [
        st.Page(HW7.hw7, title="HW7 - News-Info Chatbot", icon="🗞️"),
        st.Page(HW5.hw5, title="HW5 - Enhanced Chatbot", icon="🧠"),
        st.Page(HW4.hw4, title="HW4 - iSchool Chatbot", icon="👨🏻‍🏫"),
        st.Page(HW3.hw3, title="HW3 - URL Chatbot", icon="🤖"),
        st.Page(HW2.hw2, title="HW 2 - URL Summarizer", icon="🌐"),
        st.Page(HW1.hw1, title="HW 1", icon="📝"),
    ]
})

# Run the selected page
pg.run()
