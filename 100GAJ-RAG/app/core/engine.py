import os
from functools import lru_cache
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.settings import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata

from app.core.loader import get_documents
from app.core.settings import CACHE_DIR
from app.core.tools import all_tools

@lru_cache(maxsize=1)
def create_chat_engine():
    """
    Creates the definitive conversational agent with a strict, rule-based flow.
    This version uses a ReActAgent with a highly explicit prompt to ensure reliability.
    """
    print("--- Creating FINAL ReActAgent with Strict Programming ---")
    
    if not os.path.exists(os.path.join(CACHE_DIR, "docstore.json")):
        print("No cache found. Building knowledge base index from scratch...")
        documents = get_documents()
        index = VectorStoreIndex.from_documents(documents, show_progress=True)
        index.storage_context.persist(persist_dir=CACHE_DIR)
        print("Knowledge base index built and cached.")
    else:
        storage_context = StorageContext.from_defaults(persist_dir=CACHE_DIR)
        index = load_index_from_storage(storage_context)
        print("Knowledge base index loaded from cache.")

    query_engine = index.as_query_engine(llm=Settings.llm, similarity_top_k=5)

    rag_tool = QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="company_knowledge_base",
            description="Use for all general questions about 100Gaj company, its services, team, processes, or AI tools."
        ),
    )

    all_engine_tools = [rag_tool] + all_tools
    
    chat_agent = ReActAgent.from_tools(
        tools=all_engine_tools,
        llm=Settings.llm,
        verbose=True,
        system_prompt="""You are a function-calling AI model for 100Gaj's property database.
You have direct access to our property database through the query_property_database tool.
NEVER suggest external websites or services. ALWAYS use our own database.

STRICT EXECUTION RULES:

1. PROPERTY SEARCH COMMANDS (HIGHEST PRIORITY)
IF the user's message contains ANY of these:
- Property types: 'property', 'properties', 'apartment', 'villa', 'house', 'flat'
- Actions: 'rent', 'sale', 'buy', 'find', 'show', 'list', 'search'
- Locations: Any city name (Delhi, Mumbai, Gurgaon, etc.)
- Specifications: price, bedrooms, bathrooms
THEN:
- You MUST call query_property_database()
- You MUST use all provided filters (city, property_type, listing_type)
- You MUST NOT ask for more information
- You MUST NOT suggest external websites
Example: "Find a villa in Gurgaon" → query_property_database(city="Gurgaon", property_type="villa")

2. BROAD SEARCH COMMANDS (NO HESITATION)
IF the user gives a broad command like:
- "show me properties"
- "I want to buy a house"
- "what apartments are available"
THEN:
- You MUST call query_property_database() immediately
- Use whatever filters are mentioned
- Do NOT ask for more specifics
Example: "show me apartments" → query_property_database(property_type="apartment")

3. PROPERTY DETAILS LOOKUP
IF the user asks about a specific property:
- You MUST search using query_property_database()
- Use any known details to filter
Example: "what's the price of Test 1 in Delhi" → query_property_database(city="Delhi")

4. COMPANY INFORMATION
IF and ONLY IF the query is about 100Gaj company, team, or services:
- Use the company_knowledge_base tool

5. CRITICAL PROHIBITIONS
You are ABSOLUTELY FORBIDDEN from:
- Suggesting external websites (99acres, Magicbricks, etc.)
- Claiming you don't have access to property data
- Asking for more information instead of searching
- Making up property information

6. RESPONSE FORMAT
- Only use the data returned by the tools
- Present property information clearly and professionally
- If no properties found, say exactly that and suggest broadening the search

Remember: You ALWAYS have access to our property database through query_property_database. 
NEVER say you don't have access to property data."""
    )
    
    print("--- ReActAgent created successfully. ---")
    return chat_agent

def get_chat_engine():
    """Provides access to the singleton chat engine instance."""
    return create_chat_engine()

def clear_engine_cache():
    """Clears the in-memory cache for the chat engine."""
    create_chat_engine.cache_clear()
    print("In-memory RAG engine cache cleared.")