import requests
import helpercode
import urllib
import json
import logging
from google import genai
from google.genai import types
from tenacity import retry, wait_random_exponential

PROJECT_ID = helpercode.get_project_id()
AUTH = helpercode.access_secret_version(PROJECT_ID, "CourtListenerAccessKey")
logger = logging.getLogger("LegalEagleAgent")
LOCATION = "us-central1"
MODEL =  "gemini-2.0-flash-exp"

SYSTEM_INSTRUCTION = """You are a legal specialist tasked with summarizing legal judgments. Your summaries must include:
Key Facts: A concise summary of the relevant facts of the case.
Legal Issue(s): A clear statement of the legal question(s) the court addressed.
Judgment: A statement of the court's decision (e.g., affirmed, reversed, remanded).
Prevailing Party: Explicitly state which party (plaintiff or defendant) the judgment favored.
Damages/Remedies (if applicable): If monetary damages or other remedies (e.g., injunctions) were awarded, specify the amount of damages and to whom they were awarded. If no damages were awarded, state "No damages awarded."
Output your summaries in a clear and structured format, using headings for each of the above elements. For example:
Example Output Format:
Case Name: Smith v. Jones Key Facts: [Concise summary of facts] Legal Issue(s): [Statement of legal question(s)] Judgment: [Court's decision] Prevailing Party: [Plaintiff/Defendant] Damages/Remedies: $[Amount] awarded to [Plaintiff/Defendant] / No damages awarded
Further Instructions:
Focus on the core elements of the judgment relevant to the outcome and any awarded damages or remedies.
Avoid legal jargon unless absolutely necessary for clarity, and if used, provide a brief explanation.
Be objective and impartial in your summaries.
If the judgment is complex with multiple issues, prioritize the issues related to damages and the overall outcome.
If damages are not explicitly stated in the provided text, state "Damages not specified in provided text.
Analyse all the data individual cases in the data separately and create responses for each."""

JSON_CONTENT_TYPE = "application/json"

CLIENT = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

generate_config_20 = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    response_mime_type=JSON_CONTENT_TYPE,
    system_instruction=[types.Part.from_text(SYSTEM_INSTRUCTION)],
)

def search_case(params):
    url =  f"https://www.courtlistener.com/api/rest/v4/search/?q={urllib.parse.quote(params['querystring'])}&type=o&order_by=score%20desc&stat_Published=on&filed_after={urllib.parse.quote(params['date'])}"

    headers = {
        "Authorization": AUTH
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    results = []
    recordcount = 0
    while True:
        for result in response.json()['results']:
            results.append({'absolute_url': f"https://www.courtlistener.com{result['absolute_url']}",
                            'caseName': result['caseName'],
                            'docket_id': result['docket_id'],
                            'casedataurl': f"https://www.courtlistener.com/{result['opinions'][0]['local_path']}",
                            'caseData': summarise_case(f"https://www.courtlistener.com{result['absolute_url']}")
                            })
            recordcount += 1
        if response.json()['next']:
            response = requests.get(response.json()['next'], headers=headers)
        else:
            break

    logger.warning(f"Records found in the data = {recordcount} vs {len(results)}")

    logger.warning(f"Here are the records: {results}")
    return results

def summarise_case(url):
    # casetxt = helpercode.get_pdf_text(url)
    casetxt = helpercode.get_text_from_url(url)
    return casetxt

def summarise_cases(urls):
    casetxt = ""
    for url in urls:
        casetxt += helpercode.get_text_from_url(url, AUTH)
    
    
def analyse_case_gemini2(data, prompt):
    logger.warning("Accessing Gemini2 to analyse cases")
    try:
        response = CLIENT.models.generate_content(model=MODEL,
                                                  contents=types.Content(role='user', parts=[types.Part(text=prompt )]),
                                                  config=generate_config_20)
    except Exception as e:
        logger.error(e)
        raise e
    logger.warning("Multi call succeeded")
    logger.warning(response)
    return json.loads(response.text)

function_handler = {
    "search_case": search_case,
}