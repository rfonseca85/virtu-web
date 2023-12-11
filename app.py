from decouple import config
import time
import streamlit as st
import search
import asyncio
from multiprocessing import Pool
from multiprocessing import Process, Queue
import asyncio
from pyppeteer import launch
import base64


if config('COMPANY_NAME'):
    company_name = config('COMPANY_NAME')
else:
    company_name = "Virtu.web"

if not config('OPENAI_API_KEY'):
    st.write("Please set your OPENAI_API_KEY in .env file or in your environment variables")

#################### Pyppeteer ####################
# Define the function to be run in a separate process
def run_pyppeteer(url):
    # Start the event loop and run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(search.capture_screenshots(url))
    loop.close()
    return result


#################### Chatbot ####################

st.title("💬 " + company_name)
st.caption("🚀 A web scraper using AI (GPT4Vision + Pyppeteer) by Virtu.ai")

prompt = st.text_input("Your question?", key="search_q")


if prompt:
    with st.status("🤖 I'm looking for the answer... Follow the process in the meantime", expanded=True) as status:
        
        start_time = time.time()
        
        st.write("Searching for a url using gpt3.5...")
        url = search.get_url_from_prompt(prompt)
        st.write("Found URL " + url)

        st.write("Retrieving screenshots from url using pyppeteer...")
        # Create a pool of processes
        pool = Pool(processes=1)
        result = pool.apply_async(run_pyppeteer, (url,))
        # Continue with other tasks while waiting for the subprocess to finish
        while not result.ready():
            time.sleep(1)  # You can adjust the sleep interval as needed
        # Get the result from the subprocess
        screenshots_dict = result.get()
        st.write("Screenshots retrieved")

        st.write("Processing images using GPT4Vision...")           
        for i, screenshot in enumerate(screenshots_dict.values(), start=1):

            # Now you can process the result and continue with your Streamlit code
            gptVision_return_message = search.scrape_images_using_gtpVision(prompt, screenshot)
            st.write("Scraping image using GPT4Vision... Image " + str(i) + " of " + str(len(screenshots_dict)) + " processed")

            binary_image = base64.b64decode(screenshot)

            if "ANSWER_NOT_FOUND" in gptVision_return_message:
                st.write("Answer not found on current screenshot below, I'll keep looking in the same website")
                st.image(binary_image)
                continue
            else:
            # # Specify the file path where you want to save the binary data
            # file_path = "output_file.png"

            # # Write the binary data to the file
            # with open(file_path, "wb") as file:
            # 	file.write(binary_data)

                st.write("Answer found on screenshot below")
                st.image(binary_image)

            # chat = st.chat_message("assistant").write(message_text)
            st.session_state["messages"] = [{"role": "assistant", "content": gptVision_return_message}]
            
            end_time = time.time()

            status.update(label="Search took - {:.2f} seconds".format(end_time - start_time), state="complete", expanded=False)

            break
        
    st.write(gptVision_return_message)    

  
  