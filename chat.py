import os
import openai
import time
import streamlit as st
from dotenv import load_dotenv
import boto3
import time
from io import BytesIO
import json

# Read parameters from JSON file
with open('assistant_params.json', 'r') as json_file:
    assistant_params = json.load(json_file)

# Load environment variables from .env file
load_dotenv()

# Set AWS credentials from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

# Create an S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Create a client instance
client = openai.Client()

# main assistant
mainAssistant = client.beta.assistants.retrieve(os.getenv('MAIN_ASSISTANT_ID'))

if "created_Assistant" not in st.session_state:
    st.session_state.created_Assistant = ""

if "file_ids" not in st.session_state:
    st.session_state.file_ids = ""

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

def retrieve_from_s3_and_send_to_openai(file_name):
    try:
        local_file_path = os.path.join(os.getcwd(), file_name)  # Get current working directory
        s3_client.download_file(AWS_BUCKET_NAME, file_name, local_file_path)

        # Send file path to OpenAI
        with open(local_file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="assistants"
            )
        # Check the response or handle it accordingly
        if isinstance(response, str):
            print(response)  # Print the error message
        else:
            st.session_state.file_ids = response.id  # Store the file ID if needed
        
        os.remove(local_file_path)

        return "The file has beed retrieved and is ready"
    except Exception as e:
        print(f"Error: {str(e)}")

def get_the_file(assistant_id):
    # Check if 'messages' key is not in session_state
    if "messages" not in st.session_state:
    # If not present, initialize 'messages' as an empty list
        st.session_state.messages = []
    # Iterate through messages in session_state
    for message in st.session_state.messages:
    # Display message content in the chat UI based on the role
        with st.chat_message(message["role"]):
            st.markdown(message["content"])    
    # Get user input from chat and proceed if a prompt is entered
    if prompt := st.chat_input("Enter your message here"):
        # Add user input as a message to session_state
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user's message in the chat UI
        with st.chat_message("user"):
            st.markdown(prompt)
        # Process the assistant's response
        assistant_retrieve_file(assistant_id, prompt)


def assistant_retrieve_file(assistant_id, prompt):
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
    thread_id = st.session_state.thread_id    

    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content= prompt,
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        )

    while True:
        # Wait for 5 seconds
        time.sleep(5)

        # Retrieve the run status
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        # If run is completed, get messages
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread_id
            )
            break
        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            import json
            for action in required_actions["tool_calls"]:
                func_name = action['function']['name']
                arguments = json.loads(action['function']['arguments'])
            
                if func_name == "retrieve_from_s3_and_send_to_openai":
                    output = retrieve_from_s3_and_send_to_openai(arguments['fileName'])
                    tool_outputs.append({
                        "tool_call_id": action['id'],
                        "output": output
                    })
                else:
                    raise ValueError(f"Unknown function: {func_name}")
            
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        else:
            time.sleep(5)

    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    last_message = messages.data[0].content[0].text.value

    createdAssistant = client.beta.assistants.create(
        instructions=assistant_params['instructions'],
        name=assistant_params['name'],
        tools=assistant_params['tools'],
        model=assistant_params['model']
    )
    assistant_file = client.beta.assistants.files.create(
        assistant_id=createdAssistant.id,
        file_id=st.session_state.file_ids
    )
    st.session_state.created_Assistant = createdAssistant.id
    st.session_state.file_uploaded = True

    st.session_state.messages.append({"role": "assistant", "content": last_message})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(last_message)

def getAssistantResponse(assistant_id):
    # Check if 'messages' key is not in session_state
    if "messages" not in st.session_state:
    # If not present, initialize 'messages' as an empty list
        st.session_state.messages = []
    # Iterate through messages in session_state
    for message in st.session_state.messages:
    # Display message content in the chat UI based on the role
        with st.chat_message(message["role"]):
            st.markdown(message["content"])    
    # Get user input from chat and proceed if a prompt is entered
    if prompt := st.chat_input("Enter your message here"):
        # Add user input as a message to session_state
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user's message in the chat UI
        with st.chat_message("user"):
            st.markdown(prompt)
        # Process the assistant's response
        getAssistantRetriavalResponse(assistant_id, prompt)

def getAssistantRetriavalResponse(assistant_id, prompt):
    if "thread_file_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_file_id = thread.id
    thread_file_id = st.session_state.thread_file_id

    message = client.beta.threads.messages.create(
        thread_id=thread_file_id,
        role="user",
        content= prompt,
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_file_id,
        assistant_id=assistant_id,
        )

    while True:  # Change to an infinite loop to continually check for completion
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_file_id,
            run_id=run.id
        )
        if run.status == "completed":
            break  # Exit the loop once the run is completed
        time.sleep(0.5)
    
    messages = client.beta.threads.messages.list(
        thread_id=thread_file_id
    )

    last_message = messages.data[0].content[0].text.value

    st.session_state.messages.append({"role": "assistant", "content": last_message})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(last_message)
def main():
    st.title('GPT ChatBot')

    if not st.session_state.file_uploaded:
        get_the_file(mainAssistant.id)
    else:
        getAssistantResponse(st.session_state.created_Assistant)
        
# Call the main function to run the app
if __name__ == "__main__":
    main()
