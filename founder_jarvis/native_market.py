"""Call the original OpenJarvis search tool in its installed environment."""
import json
import sys
from openjarvis.tools.web_search import WebSearchTool
QUERY = 'Uzbekistan individual Umrah travel market Saudi Arabia visa direct flights tourism news Instagram travel marketing recent trends'
if __name__ == '__main__':
    result = WebSearchTool(max_results=6).execute(query=QUERY, max_results=6)
    print(json.dumps({'available':bool(result.success), 'content':str(result.content)[:14000]},ensure_ascii=False))
