import json
import os
from textwrap import dedent

from dotenv import load_dotenv
from flask import Flask, request
from openai import OpenAI
from readability import Document
import requests

load_dotenv()

app = Flask(__name__)

GPT_MODEL = "gpt-4-1106-preview"

GPT_FACTCHECK_ROLE = {
    "role": "system",
    "content": dedent(
        """\
        You are a fact-checker for the anti-defamation league. Your job is
        to check other sources to see if a claim is correct or not
    """
    ),
}

SITES_CHECKED = 5

openai_client = OpenAI()


@app.route("/check-article", methods=["POST"])
def check_article_api():
    app.logger.info("Starting check article...")

    url = request.get_json().get("url")
    html = get_article_html(url)

    app.logger.info("======\nChecking {}\n======".format(url))

    claims = parse_claims(html)["claims"]

    checked_claims = [check_claim(c["summary"], c["query"]) for c in claims]
    return checked_claims


@app.route("/parse-claims", methods=["POST"])
def parse_claims_api():
    text = request.get_json().get("text")
    return parse_claims(text)


@app.route("/check-claim", methods=["POST"])
def check_claim_api():
    claim = request.get_json().get("claim")
    query = request.get_json().get("query")

    return check_claim(claim, query)


@app.route("/check-site", methods=["POST"])
def check_site_api():
    app.logger.info("Starting check site")

    claim = request.get_json().get("claim")
    url = request.get_json().get("url")

    return check_site(claim, url)


@app.route("/google-search", methods=["POST"])
def google_search_api():
    app.logger.info("Starting google search")

    query = request.get_json().get("query")

    return google_search(query)


def parse_claims(text):
    app.logger.info("Starting parse claims")
    parse_claims_prompt = dedent(
        """\
        Below is an article. Give me a JSON object that represents all the
        claims of fact in this article that need to be fact-checked. The object
        should be formatted like:
        {
            "claims": [
                {
                    // A sentence or two describing the claim
                    "summary": "...",

                    // A quote from the article making the claim
                    "quote": "...",

                    // A query that you will enter into a search engine. The first five
                    // results that are returned should let you determine if the claim
                    // is true or not.
                    "query": "...",
                }
            ]
        }

        Please pick claims that are important and newsworthy, trival claims
        don't need to be fact-checked.

        Here is the text of the article:
    """
    )

    completion = openai_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            GPT_FACTCHECK_ROLE,
            {"role": "user", "content": "{}\n{}".format(parse_claims_prompt, text)},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(completion.choices[0].message.content)
    app.logger.info("=======\nParse claims result is \n{}\n=======".format(result))
    return result


def check_claim(claim, query):
    app.logger.info("Starting check claim")

    search_results = google_search(query)

    citations = {"True": [], "False": [], "Unclear": []}

    site_check_count = 0
    search_result_index = 0
    while site_check_count < SITES_CHECKED:
        site = search_results["items"][search_result_index]
        search_result_index += 1

        check_site_result = check_site(claim, site["link"])

        if not check_site_result["articleLoaded"]:
            continue

        site_check_count += 1

        citation = {"summary": check_site_result["summary"], "link": site["link"]}

        if check_site_result["assessment"] == "Not Found":
            continue

        citations[check_site_result["assessment"]].append(citation)

    check_claim_result = {
        "summary": claim,
        "citations": citations,
    }

    if len(citations["True"]) > 0 and len(citations["False"]) == 0:
        check_claim_result["overallAssessment"] = "True"
    elif len(citations["True"]) == 0 and len(citations["False"]) > 0:
        check_claim_result["overallAssessment"] = "False"
    else:
        check_claim_result["overallAssessment"] = "Unclear"

    return check_claim_result


def google_search(query):
    response = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": os.getenv("GOOGLE_API_KEY"),
            "cx": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
            "q": query,
        },
    )
    return response.json()


def check_site(claim, url):
    readable_html = get_article_html(url)

    check_site_prompt = dedent(
        """\
            Please check if the text of the below article supports a claim you are
            fact-checking.

            Return a JSON object that looks like the following:
            {{
                // This is a string, indicating your overall assessment of whether the
                // claim is supported by the article. It can be True, False, Unclear, or
                // Not Found.
                // Use "True" if the article supports the claim.
                // Use "False" if the article contradicts the claim.
                // Use "Unclear" if the article doesn't clearly support or contradict
                // the claim.
                // Use "Not Found" if the article doesn't mention anything like the
                // claim, or if the article doesn't load.
                "assessment": "True",

                // A one- to two-sentence summary explaining your assessment
                "summary": "Example text...",

                // This is a boolean, indicating whether the article was successfully
                // loaded. If it wasn't, the assessment should be "Not Found".
                "articleLoaded": true,
            }}

        The claim is:
        {}

        The article you are checking is:
        {}
    """
    ).format(claim, readable_html)

    completion = openai_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            GPT_FACTCHECK_ROLE,
            {"role": "user", "content": check_site_prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(completion.choices[0].message.content)
    app.logger.info("Check site result for {} is {}".format(url, result))
    return result


def get_article_html(url):
    response = requests.get(url)
    html = response.text
    readable_html = Document(html).summary()
    return readable_html
