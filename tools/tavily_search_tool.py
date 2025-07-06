from agents.tool import function_tool
from tavily import TavilyClient
from dotenv import load_dotenv
import os
load_dotenv()

tavily_api = os.getenv("TAVILY_API_KEY")

@function_tool
def tavily_search(query: str):
    """
    Tavily search tool for searching on internet
       args:
            query: str
       return:
            response
    """

    tavily_client = TavilyClient(api_key=tavily_api)
    response = tavily_client.search(query="What is mean by genetic disorder", search_depth="advanced")

    return response["results"]