import json
from google import genai
from google.genai import types
from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()

PROFESSION_DESCRIPTIONS = {
    'Data Scientist':            'Builds predictive models and extracts insights from data using statistics and machine learning.',
    'Data Analyst':              'Analyzes data to support business decisions, builds dashboards and reports.',
    'Data Engineer':             'Builds data infrastructure, ETL pipelines, and data warehouses.',
    'Business Analyst':          'Serves as a bridge between business and IT, gathers requirements and analyzes processes.',
    'Machine Learning Engineer': 'Deploys and optimizes ML models in production.',
    'Software Engineer':         'Develops software products and services.',
    'Cloud Engineer':            'Designs and manages cloud infrastructure.',
}

class LLMService:
    '''Service for interacting with the LLM (Gemini) to provide personalized career advice based on the student's profile and other context.'''
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("API_KEY"))
        self.system_prompt = """
You are an expert IT career advisor helping a student choose their career path. 
You have the student's profile: their skills, GPA, field of study, and profession match scores. Use this as context to give personal, relevant advice. 
Rules: 
1) Answer career-related questions using ONLY the student profile context provided above.
2) Do not draw on general knowledge beyond what is explicitly given in the context.
3) If the user asks something not covered by the provided data, say so; 
4) Be concise: 2-4 sentences unless the user asks for detail; 
5) Be personal: reference the student's actual skills and profession match when relevant; 
6) Plain text only: no markdown, no bullet points, no headers, no asterisks; 
7) If the user writes in Russian — respond in Russian, location is Kazakhstan (take it into account). Default is English, location is global.
"""


    def _build_gemini_history(self, history: list) -> list:
        '''Convert our internal message history format to the format expected by Gemini.'''
        gemini_history = []
        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.get("content", ""))]
                )
            )
        return gemini_history
    
    def build_context(
        self,
        skills: list[str],
        skill_scores: dict,
        classification_scores: dict,
        demand_scores: dict,
        roadmap_with_courses: dict,
    ) -> str:
        '''Build a comprehensive context string for the LLM based on the student's profile and other relevant information.'''
        top_profession = list(skill_scores.keys())[0]
        top_2 = list(skill_scores.keys())[1]
        description = PROFESSION_DESCRIPTIONS.get(top_profession, '')

        return f"""
## Student Skills
{', '.join(skills)}

## Recommended Profession
{top_profession} — {description}

## Alternative Profession
{top_2} — {PROFESSION_DESCRIPTIONS.get(top_2, '')}

## Skill Match Scores
{json.dumps(skill_scores, indent=2, ensure_ascii=False)}

## Classifier Scores
{json.dumps(classification_scores, indent=2, ensure_ascii=False)}

## Market Demand
{json.dumps(demand_scores, indent=2, ensure_ascii=False)}

## Personalized Roadmap and Courses
{json.dumps(roadmap_with_courses, indent=2, ensure_ascii=False)}
"""
    def list_models(self):
        for m in self.client.models.list():
            if 'flash' in m.name.lower():
                print(m.name)

    def chat(self, context: str, history: list, message: str) -> str:
        '''Generate a response from the LLM based on the provided context, conversation history, and user message.'''
        gemini_history = []
        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

        full_message = f"Context:\n{context}\n\nQuestion: {message}"

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=gemini_history + [
                        types.Content(role="user", parts=[types.Part(text=full_message)])
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        max_output_tokens=1000,
                    )
                )
                return response.text
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < 2:
                        time.sleep(2 ** attempt) 
                    continue
                raise
        return "Sorry, I'm having trouble generating a response right now. Please try again later."
    
    def chat_stream(self, context: str, history: list, message: str, deep: bool = False):
        '''Generate a streaming response from the LLM, yielding chunks of text as they are generated. If `deep` is True, include the model's thoughts in the stream.'''
        model = "gemini-2.5-pro" if deep else "gemini-2.5-flash-lite" 
        
        full_message = f"Context:\n{context}\n\nQuestion: {message}"
        contents = self._build_gemini_history(history) + [
            types.Content(role="user", parts=[types.Part(text=full_message)])
        ]

        config_kwargs = {
            "system_instruction": self.system_prompt,
            "max_output_tokens": 8192 if deep else 2000, 
        }
        
        if deep:
            config_kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=True)

        config = types.GenerateContentConfig(**config_kwargs)

        for attempt in range(3):
            try:
                response = self.client.models.generate_content_stream(
                    model=model,  
                    contents=contents,
                    config=config,
                )
                
                for chunk in response:
                    if not chunk.candidates:
                        continue
                        
                    for part in chunk.candidates[0].content.parts:
                        is_thought = getattr(part, 'thought', False)
                        
                        if part.text:
                            data = {
                                "type": "thought" if is_thought else "text",
                                "content": part.text
                            }
                            yield f"data: {json.dumps(data)}\n\n"
                            
                yield "data: [DONE]\n\n"
                return
            
            except Exception as e:
                error_msg = str(e).upper()
                if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                raise
                
        error_data = {"type": "text", "content": "Service is currently unavailable. Please try again later."}
        yield f"data: {json.dumps(error_data)}\n\n"
