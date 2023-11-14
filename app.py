import os
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import time

# env variables
load_dotenv()
my_key = os.getenv('OPENAI_API_KEY')

# OpenAI API
client = AsyncOpenAI(api_key=my_key)


async def create_assistant():
    # List all files in the 'data/' directory
    file_ids = []
    for file_name in os.listdir('data/'):
        if file_name.endswith('.pdf'):  # Assuming you only want to upload PDF files
            file_path = os.path.join('data/', file_name)
            with open(file_path, 'rb') as file:
                uploaded_file = await client.files.create(
                    file=file,
                    purpose='assistants'
                )
                file_ids.append(uploaded_file.id)

    # Create the assistant
    if file_ids:  # Only create the assistant if there are files uploaded
        assistant = await client.beta.assistants.create(
            name="Retrieval_Assistant_Multi-File",
            instructions="You are a company assistant. You are to help employees with their queries.",
            model="gpt-4-1106-preview",
            tools=[{"type": "retrieval"}],
            file_ids=file_ids
        )

        return assistant
    else:
        print("No files were uploaded.")
        return None

async def add_message_to_thread(thread_id, user_question):
    # Create a message inside the thread
    message = await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content= user_question
    )
    return message


async def get_answer(assistant_id, thread):
    print("Thinking...")
    # run assistant
    print("Running assistant...")
    run =  await client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # wait for the run to complete
    while True:
        runInfo = await client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if runInfo.completed_at:
            # elapsed = runInfo.completed_at - runInfo.created_at
            # elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            print(f"Run completed")
            break
        print("Waiting 1sec...")
        time.sleep(1)

    print("All done...")
    # Get messages from the thread
    messages = await client.beta.threads.messages.list(thread.id)
    message_content = messages.data[0].content[0].text.value
    return message_content


if __name__ == "__main__":
    async def main():
        # Colour to print
        class bcolors:
            HEADER = '\033[95m'
            OKBLUE = '\033[94m'
            OKCYAN = '\033[96m'
            OKGREEN = '\033[92m'
            WARNING = '\033[93m'
            FAIL = '\033[91m'
            ENDC = '\033[0m'
            BOLD = '\033[1m'
            UNDERLINE = '\033[4m'
    
        # Create assistant and thread before entering the loop
        assistant = await create_assistant()
        print("Created assistant with id:" , f"{bcolors.HEADER}{assistant.id}{bcolors.ENDC}")
        thread = await client.beta.threads.create()
        print("Created thread with id:" , f"{bcolors.HEADER}{thread.id}{bcolors.ENDC}")
        while True:
            question = input("How may I help you today? \n")
            if "exit" in question.lower():
                break
            
            # Add message to thread
            await add_message_to_thread(thread.id, question)
            message_content = await get_answer(assistant.id, thread)
            print(f"FYI, your thread is: , {bcolors.HEADER}{thread.id}{bcolors.ENDC}")
            print(f"FYI, your assistant is: , {bcolors.HEADER}{assistant.id}{bcolors.ENDC}")
            print(message_content)
        print(f"{bcolors.OKGREEN}Thanks and happy to serve you{bcolors.ENDC}")
    asyncio.run(main())

