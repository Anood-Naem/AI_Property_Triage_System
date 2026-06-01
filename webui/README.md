# AI Property Triage System - WebUI

## Overview

This folder contains the Streamlit WebUI for the AI Property Triage System.

The WebUI allows users to submit real estate property listings, upload property images, receive a structured analysis report, and interact with an AI Assistant that can use the latest generated report, saved reports from the Knowledge Base, and real-time market information.

## Main Features

* Submit a new property listing through a Streamlit form.
* Send listing data to the n8n workflow for processing.
* Support both image URLs and uploaded property images.
* Display a structured property triage report.
* Save generated reports into the Pinecone Knowledge Base.
* Chat with an AI Assistant about the current report.
* Compare the current report with saved past reports.
* Use Sonar / Perplexity for real-time market questions.
* Support Groq for normal assistant chat and image-based assistant responses.
* Maintain saved chat history in a local SQLite database.

## WebUI Flow

1. The user submits a property listing from the form.
2. The WebUI sends the listing data to the n8n webhook.
3. n8n validates the input, extracts property fields, enriches the data using LangGraph, RAG, and Image Analyser services, generates a final report, and returns the response.
4. The WebUI displays the final report.
5. The report is saved silently into the Pinecone Knowledge Base.
6. The AI Assistant can later use the current report and saved reports to answer user questions.

## AI Assistant Routing

The AI Assistant uses routing logic to decide which service should answer the user:

* Groq is used for normal real estate chat, report explanation, saved report comparison, and image-based assistant responses.
* Sonar is used only when the user asks for current or real-time information such as today's market prices, recent trends, current regulations, or updated market data.
* Pinecone Knowledge Base is used when the user asks about saved reports, similar past reports, or internal report comparisons.

## Important Files

* `app.py`
  Starts the Streamlit WebUI and loads the main layout.

* `main_form.py`
  Handles the property listing form, sends requests to n8n, renders the final report, and saves reports to the Knowledge Base.

* `ai_service.py`
  Handles the AI Assistant, chat messages, routing, Groq responses, Sonar responses, current report context, and Knowledge Base context.

* `model_router.py`
  Classifies assistant requests and decides whether to use Groq, Sonar, the current report, and the Knowledge Base.

* `sonar_service.py`
  Connects to Perplexity Sonar for real-time market information and formats citations as sources.

* `knowledgebase_service.py`
  Stores generated reports in Pinecone and retrieves similar saved reports.

* `database.py`
  Manages local chat history using SQLite.

* `sidebar.py`
  Renders saved conversations and chat controls.

* `styles.css`
  Main WebUI styling.

* `report_styles.css`
  Styling for the generated property report.

* `theme.py`
  Handles Streamlit theme-related styling.

## Environment Variables

Create a `.env` file inside the `webui` folder.

Required variables:

```env
GROQ_API_KEY=your_groq_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
```

Do not commit `.env` to GitHub.

## Running the WebUI

From the project root:

```powershell
cd webui
streamlit run app.py
```

Or from the full path:

```powershell
cd C:\Users\ADMIN\PycharmProjects\AI_Property_Triage_System\webui
streamlit run app.py
```

## Required Running Services

Before using the full workflow, make sure these services are running:

* n8n workflow
* RAG service
* Image Analyser service
* LangGraph Agent service
* Guardrails service
* Streamlit WebUI

Example LangGraph service:

```powershell
cd services\langgraph_agent_service
uvicorn app:app --host 0.0.0.0 --port 8004
```

Example Image Analyser service:

```powershell
cd services\image_analyser_service
uvicorn app:app --host 0.0.0.0 --port 8002
```

Example RAG service:

```powershell
cd services\rag_service
uvicorn app:app --host 0.0.0.0 --port 8001
```

## Notes

* Generated reports are saved silently to the Knowledge Base.
* The Knowledge Base success message is hidden from the user interface.
* The user sees only the final property report.
* For real-time market questions, the assistant routes to Sonar and displays sources.
* For saved report comparisons, the assistant retrieves similar reports from Pinecone.
