import streamlit as st
import requests

# FastAPI backend URL
BACKEND_URL = "http://localhost:8000"

st.title("📄 Document QA with Gemini")
st.subheader("Ask questions about your stored documents")

# Document processing section
with st.expander("Process Documents"):
    if st.button("Process Documents"):
        try:
            response = requests.post(f"{BACKEND_URL}/process-documents/")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error(f"Error: {response.json()['detail']}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

# QA Section
question = st.text_input("Ask a question about your documents:")
if st.button("Get Answer"):
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