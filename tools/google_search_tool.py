from agents.tool import function_tool
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()

google_api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=google_api_key)


@function_tool
def google_search(content: str):
    """function that can perform google search for Studying abroad related cotent finding latest information and finding latest and update informationa and opportunities
    args:
        content: str

    return 
        resonse
    """

    grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
    )

    # Configure generation settings
    config = types.GenerateContentConfig(
        tools=[grounding_tool]
    )

    # Make the request
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=content,
        config=config,
    )

    return response.text


# if __name__ == "__main__":
#     response = google_search("Search about the universities of canada their eligibilty criteria and programs they offer")
#     print(response)