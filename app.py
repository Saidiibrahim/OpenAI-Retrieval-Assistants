# Import necessary libraries
import openai
import streamlit as st
from dotenv import load_dotenv
import os
import time

# env variables
load_dotenv()
my_key = os.getenv('OPENAI_API_KEY')

# Set your OpenAI Assistant ID here
assistant_id = 'asst_1PItSvThr8KfuOSZQzuCbRal'

# Initialize the OpenAI client (ensure to set your API key in the sidebar within the app)
client = openai

# Initialize session state variables for file IDs and chat control
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []

if "start_chat" not in st.session_state:
    st.session_state.start_chat = False

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Set up the Streamlit page with a title and icon
st.set_page_config(page_title="Lab Assistant", page_icon="🔬")


def upload_to_openai(filepath):
    """Upload a file to OpenAI and return its file ID."""
    with open(filepath, "rb") as file:
        response = openai.files.create(file=file.read(), purpose="assistants")
    return response.id

# Create a sidebar for API key configuration and additional features
st.sidebar.header("Configuration")
openai.api_key = my_key

# Sidebar option for users to upload their own files
uploaded_file = st.sidebar.file_uploader("Upload a file to OpenAI", key="file_uploader")

# Button to upload a user's file and store the file ID
if st.sidebar.button("Upload File"):
    # Upload file provided by user
    if uploaded_file:
        with open(f"{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())
        additional_file_id = upload_to_openai(f"{uploaded_file.name}")
        st.session_state.file_id_list.append(additional_file_id)
        st.sidebar.write(f"Additional File ID: {additional_file_id}")

# Display all file IDs
if st.session_state.file_id_list:
    st.sidebar.write("Uploaded File IDs:")
    for file_id in st.session_state.file_id_list:
        st.sidebar.write(file_id)
        # Associate files with the assistant
        assistant_file = client.beta.assistants.files.create(
            assistant_id=assistant_id, 
            file_id=file_id
        )

#TODO: User should be able to start conversation without uploading files
#TODO: User should be able to upload files after starting conversation
#TODO: If no file is uploaded, use the default files associated with the assistant
# Button to start the chat session
if st.sidebar.button("Start Chat"):
    # Check if files are uploaded before starting chat
    if st.session_state.file_id_list:
        st.session_state.start_chat = True
        # Create a thread once and store its ID in session state
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.write("thread id: ", thread.id)
    else:
        st.sidebar.warning("Please upload at least one file to start the chat.")

# Define the function to process messages with citations
def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            # Retrieve the cited file details (dummy response here since we can't call OpenAI)
            cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            # Placeholder for file download citation
            cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

    # Add footnotes to the end of the message content
    full_response = message_content.value + '\n\n' + '\n'.join(citations)
    return full_response



# Main chat interface setup
st.title("Lab Assistant Chat")
st.write("Here to assist you with your lab work.")

# Only show the chat interface if the chat has been started
if st.session_state.start_chat:
    # Initialize the model and messages list if not already in session state
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-4-1106-preview"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display existing messages in the chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input for the user
    if prompt := st.chat_input("What is up?"):
        # Add user message to the state and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add the user's message to the existing thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # Create a run with additional instructions
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            instructions="Please answer the queries using the knowledge provided in the files.When adding other information mark it clearly as such.with a different color"
        )

        # Poll for the run to complete and retrieve the assistant's messages
        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

        # Retrieve messages added by the assistant
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )

        # Process and display assistant messages
        assistant_messages_for_run = [
            message for message in messages 
            if message.run_id == run.id and message.role == "assistant"
        ]
        for message in assistant_messages_for_run:
            full_response = process_message_with_citations(message)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)
else:
    # Prompt to start the chat
    st.write("Please upload files and click 'Start Chat' to begin the conversation.")