"""
Task S03E03: Database Query - Find Active Datacenters with Inactive Managers

This script:
1. Connects to the BanAN database API
2. Discovers the database schema (tables and structure)
3. Uses LLM to generate SQL query to find active datacenters managed by inactive managers
4. Executes the query and extracts datacenter IDs
5. Submits the results to the central server
"""
import os
import sys
import json
import re
from dotenv import load_dotenv

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import make_request, find_flag_in_text, ask_llm

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_API_URL = os.getenv("DATABASE_API_URL")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")


def execute_database_query(query):
    """Execute a SQL query against the database API."""
    print(f"🔍 [*] Executing database query: {query}")
    
    payload = {
        "task": "database",
        "apikey": API_KEY,
        "query": query
    }
    
    try:
        response = make_request(
            DATABASE_API_URL,
            method="post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"✅ [+] Query executed successfully")
        print(f"📊 [*] Result: {json.dumps(result, indent=2)}")
        
        return result
    
    except Exception as e:
        print(f"❌ [-] Error executing database query: {str(e)}")
        return None


def discover_database_schema():
    """Discover the database schema by exploring tables and their structure."""
    print("🔍 [*] Discovering database schema...")
    
    # Get list of tables
    print("📋 [*] Getting list of tables...")
    tables_result = execute_database_query("SHOW TABLES")
    
    if not tables_result or 'reply' not in tables_result:
        print("❌ [-] Could not get tables list")
        return None
    
    tables = tables_result['reply']
    print(f"📊 [*] Found tables: {tables}")
    
    # Get structure for each table
    schema_info = {}
    for table in tables:
        table_name = table['Tables_in_banan'] if 'Tables_in_banan' in table else list(table.values())[0]
        print(f"🔍 [*] Getting structure for table: {table_name}")
        
        structure_result = execute_database_query(f"SHOW CREATE TABLE {table_name}")
        
        if structure_result and 'reply' in structure_result:
            schema_info[table_name] = structure_result['reply']
            print(f"✅ [+] Got structure for {table_name}")
        else:
            print(f"❌ [-] Could not get structure for {table_name}")
    
    return schema_info


def generate_sql_query(schema_info):
    """Use LLM to generate SQL query based on the schema."""
    print("🤖 [*] Generating SQL query using LLM...")
    
    # Prepare schema information for the LLM
    schema_description = "Database Schema:\n\n"
    for table_name, structure in schema_info.items():
        schema_description += f"Table: {table_name}\n"
        if isinstance(structure, list) and len(structure) > 0:
            # Extract CREATE TABLE statement
            create_statement = structure[0].get('Create Table', '')
            schema_description += f"Structure: {create_statement}\n\n"
    
    # Create prompt for LLM
    prompt = f"""
    Based on the following database schema, generate a SQL query that returns the DC_ID of active datacenters 
    that are managed by inactive managers.
    
    {schema_description}
    
    Requirements:
    - Find datacenters that are active (likely indicated by a status field)
    - These datacenters should be managed by users who are inactive (likely indicated by a status field in users table)
    - Return only the DC_ID values
    - The query should join the appropriate tables based on the relationships you can infer from the schema
    
    Return ONLY the SQL query, no explanations or formatting. Just the raw SQL query text.
    """
    
    print(f"📝 [*] Sending prompt to LLM...")
    print(f"Prompt: {prompt}")
    
    try:
        sql_query = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model="gpt-4o",
            context="You are a SQL expert. Generate only the SQL query without any additional text or formatting."
        )
        
        # Clean up the response - remove any markdown formatting or extra text
        sql_query = sql_query.strip()
        if sql_query.startswith('```sql'):
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        elif sql_query.startswith('```'):
            sql_query = sql_query.replace('```', '').strip()
        
        print(f"🔧 [*] Generated SQL query: {sql_query}")
        return sql_query
    
    except Exception as e:
        print(f"❌ [-] Error generating SQL query: {str(e)}")
        return None


def extract_datacenter_ids(query_result):
    """Extract datacenter IDs from the query result."""
    print("🔍 [*] Extracting datacenter IDs from result...")
    
    if not query_result or 'reply' not in query_result:
        print("❌ [-] No valid query result to process")
        return []
    
    datacenter_ids = []
    results = query_result['reply']
    
    print(f"📊 [*] Processing {len(results)} result rows")
    
    for row in results:
        # Look for DC_ID or similar field names
        dc_id = None
        for key, value in row.items():
            if 'dc_id' in key.lower() or 'datacenter_id' in key.lower() or 'id' in key.lower():
                dc_id = value
                break
        
        if dc_id is not None:
            datacenter_ids.append(dc_id)
            print(f"✅ [+] Found datacenter ID: {dc_id}")
    
    print(f"📊 [*] Total datacenter IDs found: {len(datacenter_ids)}")
    return datacenter_ids


def submit_answer(datacenter_ids):
    """Submit the datacenter IDs to the central server."""
    print("📤 [*] Submitting datacenter IDs...")
    
    payload = {
        "task": "database",
        "apikey": API_KEY,
        "answer": datacenter_ids
    }
    
    print(f"📦 [*] Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ [+] Submission response: {response.text}")
        
        # Check for flag in response
        try:
            flag = find_flag_in_text(response.text)
            print(f"🚩 [+] Flag found: {flag}")
        except Exception as e:
            print(f"⚠️ [!] No flag found in response")
        
        return response.json()
    
    except Exception as e:
        print(f"❌ [-] Error submitting answer: {str(e)}")
        return None


def main():
    """Main execution function."""
    print("🚀 [*] Starting Database Query task...")
    
    # Step 1: Discover database schema
    schema_info = discover_database_schema()
    if not schema_info:
        print("❌ [-] Could not discover database schema")
        sys.exit(1)
    
    # Step 2: Generate SQL query using LLM
    sql_query = generate_sql_query(schema_info)
    if not sql_query:
        print("❌ [-] Could not generate SQL query")
        sys.exit(1)
    
    # Step 3: Execute the generated query
    query_result = execute_database_query(sql_query)
    if not query_result:
        print("❌ [-] Could not execute SQL query")
        sys.exit(1)
    
    # Step 4: Extract datacenter IDs from result
    datacenter_ids = extract_datacenter_ids(query_result)
    if not datacenter_ids:
        print("❌ [-] No datacenter IDs found in query result")
        sys.exit(1)
    
    print(f"📊 [*] Found {len(datacenter_ids)} datacenter IDs: {datacenter_ids}")
    
    # Step 5: Submit the answer
    result = submit_answer(datacenter_ids)
    
    print("✅ [+] Task completed successfully!")


if __name__ == "__main__":
    main()
