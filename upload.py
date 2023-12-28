import os
import boto3
import streamlit as st
from dotenv import load_dotenv
from io import BytesIO
import secrets
import string

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

def generate_random_string(length=16):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def upload_to_s3(file):
    original_file_name = file.name
    file_extension = os.path.splitext(original_file_name)[1]  # Extract file extension
    new_file_name = generate_random_string(16) + file_extension

    with st.spinner('Uploading file...'):
        try:
            s3_client.upload_fileobj(file, AWS_BUCKET_NAME, new_file_name)
            st.success(f"The file '{original_file_name}' has been uploaded successfully!")
            st.success(f"Here is your 16 digit passcode for future reference: {new_file_name}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

def main():
    st.title('Upload the file for the ChatBot')

    uploaded_files = st.file_uploader("Choose a file")

    if uploaded_files:
        upload_to_s3(uploaded_files)
            
# Call the main function to run the app
if __name__ == "__main__":
    main()
