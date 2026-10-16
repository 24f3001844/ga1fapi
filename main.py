import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

# Configuration
QUESTION_DATA_URL = "https://exam.sanand.workers.dev/questionData?email=24f3001844%40ds.study.iitm.ac.in&quizSign=P6%2F7rV%2BYfZ9bG5y%2ByVn8DFZ92U4m%2FJDx0o5%2BEjJy2X%2BTErAifh4Y2Us6hcVzleHiBMnQA346Q2U7VVBfaXz5lLEhA9I4943LxVnUGS671WY5842OqCSVcw0JdSmz8DOQWJB5S7Orp8miv9sJu2SFRbDdhZIIlYiGISMNXSgknK44q9FbkfRU01Un0BO4awtSnxvbMbQjkNnFfiml4qYb7OjxCvT5KOuiypbQ9XSP%2B%2BDSYuA9t989EsfeFkTwPPuEGPy3uIw%2BLxdUFfbbBHW1mO10X8TmJaKSLVZr1DI3f1oSfBEynnnj%2ByBtEw1sPtIG9zn2huuFBwQHQBC4KA47og%3D%3D&questionId=q-ledger-agent-server&path=/"

class QuestionRequest(BaseModel):
    question: str

# Cache the ledger data globally or fetch on demand
ledger_cache = None

async def fetch_ledger_data():
    global ledger_cache
    if ledger_cache is not None:
        return ledger_cache
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(QUESTION_DATA_URL, timeout=30.0)
            response.raise_for_status()
            ledger_cache = response.json()
            return ledger_cache
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch ledger data: {str(e)}")

@app.post("/")
async def answer_question(req: QuestionRequest):
    data = await fetch_ledger_data()
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    prompt = f"""
You are an expert data analyst assistant for Acme Appliances. 
You have been given raw ledger/order data from the company's API.
Your job is to answer the user's question accurately based entirely on this data.

Ledger Data Summary/Content:
{str(data)[:15000]}  # Truncate if necessary or pass structured context

User Question: {req.question}

Rules:
- Money must be in USD, rounded correctly to the cent (e.g., 1234.56).
- Product names must match exactly as spelled in the API.
- Return ONLY the precise answer requested, formatted appropriately (plain number, string, list, or JSON as expected).
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You provide exact, concise answers to data queries based on provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    
    answer_text = response.choices[0].message.content.strip()
    
    # Try to parse as JSON/number if possible, otherwise return as string
    try:
        import json
        parsed_answer = json.loads(answer_text)
    except:
        # Try converting to float/int if it looks like a number
        try:
            if "." in answer_text:
                parsed_answer = float(answer_text)
            else:
                parsed_answer = int(answer_text)
        except ValueError:
            parsed_answer = answer_text

    return {"answer": parsed_answer}
