import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://finance-rag-bot-19bf4c184612.herokuapp.com")

st.title("📄 Finance RAG bot")
st.subheader("Ask questions about your stored documents")

# Document processing section
with st.expander("Create Index"):
    if st.button("Start Processing"):
        try:
            response = requests.post(f"{BACKEND_URL}/process-documents/")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error(f"Error: {response.json()['detail']}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

# QA Section
question = st.text_input("Ask a question:")
if st.button("Answer"):
    if not question:
        st.warning("Please enter a question")
    else:
        try:
            response = requests.post(
                f"{BACKEND_URL}/ask-question/",
                json={"question": question}
            )
            
            if response.status_code == 200:
                answer = response.json()["answer"]
                st.markdown(f"**Answer:** {answer}")
            else:
                st.error(f"Error: {response.json()['detail']}")
                
        except Exception as e:
            st.error(f"Could not connect to API: {str(e)}")
