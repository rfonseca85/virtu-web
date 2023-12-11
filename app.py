import time
import streamlit as st
import asyncio
from multiprocessing import Pool
import asyncio
from pyppeteer import launch
import base64
import os
from openai import OpenAI
import json

model = OpenAI()
model.timeout = 15    

#################### OpenAI ####################
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    with st.sidebar:
        api_key = st.text_input("Please enter your OpenAI API key")
        if api_key:
            model.api_key = api_key




#################### Functions ####################

# Define the function to be run in a separate process since it is async
def run_pyppeteer(url):
    # Start the event loop and run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(capture_screenshots(url))
    loop.close()
    return result

# Get the url from prompt using GPT3.5
def get_url_from_prompt(prompt):

    messages = [
        {
            "role": "system",
            "content": "You are a web crawler. Your job is to give the user a URL to go to in order to find the answer to the question. Go to a direct URL that will likely have the answer to the user's question. Respond in the following JSON fromat: {\"url\": \"<put url here>\"}",
        },
        {
            "role": "user",
            "content": prompt,
        }
    ]

    response = model.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        max_tokens=1024,
        response_format={"type": "json_object"},
        seed=2232,
    )

    message = response.choices[0].message
    message_json = json.loads(message.content)
    url = message_json["url"]

    messages.append({
        "role": "assistant",
        "content": message.content,
    })

    return url

# Capture screenshots from url using pyppeteer
async def capture_screenshots(url):

        browser = await launch()
        page = await browser.newPage()

        await page.setViewport({'width': 1920, 'height': 1080})
        await page.goto(url)
        screenshots_dict = {}
        screenshot_counter = 1

        while True:
            screenshot = await page.screenshot()
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
            screenshot_key = f"screenshot_{screenshot_counter}"
            screenshots_dict[screenshot_key] = screenshot_base64

            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            scroll_top = await page.evaluate("window.scrollY")
            scroll_height = await page.evaluate("document.body.scrollHeight")
            inner_height = await page.evaluate("window.innerHeight")

            if scroll_top + inner_height >= scroll_height:
                break

            screenshot_counter += 1

        await browser.close()
        return screenshots_dict
  
def scrape_images_using_gtpVision(prompt, screenshot):

    messages = [
		{
			"role": "user",
			"content": prompt,
		}
	]
    response = model.chat.completions.create(
		model="gpt-4-vision-preview",
		messages=[
			{
				"role": "system",
				"content": "Your job is to answer the user's question based on the given screenshot only with more than 95% certainty. Answer the user as an assistant, but don't tell that the information is from a screenshot or an image. Pretend it is information that you know. If you can't answer the question, dont look for another answer, simply respond with the code `ANSWER_NOT_FOUND` and nothing else. Thats extreame important that you dont try to find the answer from another source",
			}
		] + messages[1:] + [
			{
				"role": "user",
				"content": [
					{
						"type": "image_url",
						"image_url": f"data:image/png;base64,{screenshot}",
					},
					{
						"type": "text",
						"text": prompt,
					}
				]
			}
		],
		max_tokens=1024,
	)
    message = response.choices[0].message
	
    return  message.content

#################### Streamlit app ####################
def app():
    st.title("💬 Virtu.web")
    st.caption("🚀 A web scraper using AI (GPT4Vision + Pyppeteer) by Virtu.ai")

    prompt = st.text_input("Your question?", key="search_q")
    if prompt:

        # Check if API key is provided
        if not api_key:
            st.error("Please enter your OpenAI API key or set it as an environment variable")
            st.code("Add the line below to ~/.bashrc or ~/.zshrc" + "\n" + "export OPENAI_API_KEY=your_openai_key" + "\n" + "source ~/.bashrc or source ~/.zshrc")
            st.stop()
            
        with st.status("🤖 I'm looking for the answer... Follow the process in the meantime", expanded=True) as status:
            
            start_time = time.time()
            
            st.write("Searching for a url using gpt3.5...")
            url = get_url_from_prompt(prompt)
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
                gptVision_return_message = scrape_images_using_gtpVision(prompt, screenshot)
                st.write("Scraping image using GPT4Vision... Image " + str(i) + " of " + str(len(screenshots_dict)) + " processed")

                binary_image = base64.b64decode(screenshot)

                if "ANSWER_NOT_FOUND" in gptVision_return_message:
                    st.write("Answer not found on current screenshot below, I'll keep looking in the same website")
                    st.image(binary_image)
                    continue
                else:
                    st.write("Answer found on screenshot below")
                    st.image(binary_image)

                st.session_state["messages"] = [{"role": "assistant", "content": gptVision_return_message}]
                
                end_time = time.time()

                status.update(label="Search took - {:.2f} seconds".format(end_time - start_time), state="complete", expanded=False)

                break
            
        st.write(gptVision_return_message)    
    
app()