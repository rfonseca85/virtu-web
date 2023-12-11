import streamlit as st
from openai import OpenAI
import json
from pyppeteer import launch
import base64

model = OpenAI()
model.timeout = 10

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

    # print(f"Crawling {url}")
	return url

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


