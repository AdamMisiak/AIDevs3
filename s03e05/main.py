"""
Task S03E05: Connections - Find Shortest Path Between Rafał and Barbara

This script:
1. Connects to the BanAN database API to extract users and connections data
2. Connects to Neo4j cloud instance 
3. Loads data into Neo4j as a graph (Person nodes with KNOWS relationships)
4. Uses Cypher to find the shortest path from Rafał to Barbara
5. Submits the path as comma-separated names to the central server
"""
import os
import sys
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import make_request, find_flag_in_text

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
DATABASE_API_URL = os.getenv("DATABASE_API_URL")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")

# Neo4j Configuration - these need to be defined in your .env file
NEO4J_URI = os.getenv("NEO4J_URI")  # e.g., "neo4j+s://your-instance.databases.neo4j.io"
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")  # usually "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # your password


def execute_database_query(query):
    """Execute a SQL query against the BanAN database API."""
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
        return result
    
    except Exception as e:
        print(f"❌ [-] Error executing database query: {str(e)}")
        return None


def fetch_users_data():
    """Fetch all users from the database."""
    print("👥 [*] Fetching users data...")
    
    query = "SELECT id, username FROM users"
    result = execute_database_query(query)
    
    if not result or 'reply' not in result:
        print("❌ [-] Could not fetch users data")
        return None
    
    users = result['reply']
    print(f"✅ [+] Found {len(users)} users")
    
    # Show first few users as examples
    print("📊 [*] Sample users:")
    for i, user in enumerate(users[:5]):
        print(f"    {i+1}. ID: {user['id']}, Username: '{user['username']}'")
    if len(users) > 5:
        print(f"    ... and {len(users) - 5} more users")
    
    return users


def fetch_connections_data():
    """Fetch all connections from the database."""
    print("🔗 [*] Fetching connections data...")
    
    query = "SELECT user1_id, user2_id FROM connections"
    result = execute_database_query(query)
    
    if not result or 'reply' not in result:
        print("❌ [-] Could not fetch connections data")
        return None
    
    connections = result['reply']
    print(f"✅ [+] Found {len(connections)} connections")
    
    # Show first few connections as examples
    print("📊 [*] Sample connections:")
    for i, conn in enumerate(connections[:5]):
        print(f"    {i+1}. {conn['user1_id']} -> {conn['user2_id']}")
    if len(connections) > 5:
        print(f"    ... and {len(connections) - 5} more connections")
    
    return connections


def create_neo4j_driver():
    """Create and verify Neo4j driver connection."""
    print("🚀 [*] Connecting to Neo4j...")
    
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ [-] Missing Neo4j connection parameters. Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in your .env file")
        return None
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ [+] Connected to Neo4j successfully")
        return driver
    
    except Exception as e:
        print(f"❌ [-] Error connecting to Neo4j: {str(e)}")
        return None


def clear_neo4j_database(driver):
    """Clear all nodes and relationships from Neo4j database."""
    print("🧹 [*] Clearing Neo4j database...")
    
    try:
        with driver.session() as session:
            # Delete all relationships first, then all nodes
            print("🔍 [*] Executing Cypher: MATCH ()-[r]-() DELETE r")
            result1 = session.run("MATCH ()-[r]-() DELETE r")
            print(f"✅ [+] Deleted relationships: {result1.consume().counters.relationships_deleted}")
            
            print("🔍 [*] Executing Cypher: MATCH (n) DELETE n")
            result2 = session.run("MATCH (n) DELETE n")
            print(f"✅ [+] Deleted nodes: {result2.consume().counters.nodes_deleted}")
            
        print("✅ [+] Neo4j database cleared successfully")
    
    except Exception as e:
        print(f"❌ [-] Error clearing Neo4j database: {str(e)}")
        raise


def load_users_to_neo4j(driver, users):
    """Load users as Person nodes into Neo4j."""
    print("👥 [*] Loading users into Neo4j...")
    print(f"📊 [*] Found {len(users)} users to load")
    
    try:
        with driver.session() as session:
            # Create Person nodes with userId (original MySQL ID) and username properties
            cypher_query = "CREATE (p:Person {userId: $userId, username: $username})"
            print(f"🔍 [*] Using Cypher query: {cypher_query}")
            
            created_count = 0
            for user in users:
                print(f"📝 [*] Creating user: ID={user['id']}, username='{user['username']}'")
                result = session.run(
                    cypher_query,
                    userId=user['id'],
                    username=user['username']
                )
                created_count += result.consume().counters.nodes_created
        
        print(f"✅ [+] Loaded {created_count} users into Neo4j")
        
        # Verify the data was loaded
        with driver.session() as session:
            print("🔍 [*] Verifying loaded users with: MATCH (p:Person) RETURN count(p) AS total")
            result = session.run("MATCH (p:Person) RETURN count(p) AS total")
            total_count = result.single()['total']
            print(f"✅ [+] Verification: {total_count} total users in Neo4j")
    
    except Exception as e:
        print(f"❌ [-] Error loading users into Neo4j: {str(e)}")
        raise


def load_connections_to_neo4j(driver, connections):
    """Load connections as KNOWS relationships into Neo4j."""
    print("🔗 [*] Loading connections into Neo4j...")
    print(f"📊 [*] Found {len(connections)} connections to load")
    
    try:
        with driver.session() as session:
            # Create KNOWS relationships between users
            cypher_query = """
                MATCH (u1:Person {userId: $user1_id})
                MATCH (u2:Person {userId: $user2_id})
                CREATE (u1)-[:KNOWS]->(u2)
            """
            print(f"🔍 [*] Using Cypher query:")
            print(f"    MATCH (u1:Person {{userId: $user1_id}})")
            print(f"    MATCH (u2:Person {{userId: $user2_id}})")
            print(f"    CREATE (u1)-[:KNOWS]->(u2)")
            
            created_count = 0
            for i, connection in enumerate(connections):
                if i < 5 or i % 10 == 0:  # Show first 5 and every 10th after that
                    print(f"📝 [*] Creating connection {i+1}/{len(connections)}: {connection['user1_id']} -> {connection['user2_id']}")
                
                result = session.run(cypher_query, 
                    user1_id=connection['user1_id'],
                    user2_id=connection['user2_id']
                )
                created_count += result.consume().counters.relationships_created
        
        print(f"✅ [+] Loaded {created_count} connections into Neo4j")
        
        # Verify the data was loaded
        with driver.session() as session:
            print("🔍 [*] Verifying loaded connections with: MATCH ()-[r:KNOWS]->() RETURN count(r) AS total")
            result = session.run("MATCH ()-[r:KNOWS]->() RETURN count(r) AS total")
            total_count = result.single()['total']
            print(f"✅ [+] Verification: {total_count} total KNOWS relationships in Neo4j")
    
    except Exception as e:
        print(f"❌ [-] Error loading connections into Neo4j: {str(e)}")
        raise


def find_shortest_path(driver):
    """Find the shortest path from Rafał to Barbara using Cypher."""
    print("🔍 [*] Finding shortest path from Rafał to Barbara...")
    
    try:
        with driver.session() as session:
            # First, check if both users exist
            print("🔍 [*] Checking if Rafał exists with: MATCH (p:Person {username: 'Rafał'}) RETURN p.userId, p.username")
            rafal_result = session.run("MATCH (p:Person {username: 'Rafał'}) RETURN p.userId, p.username")
            rafal_record = rafal_result.single()
            if rafal_record:
                print(f"✅ [+] Found Rafał: userId={rafal_record['p.userId']}, username='{rafal_record['p.username']}'")
            else:
                print("❌ [-] Rafał not found in database!")
                return None
            
            print("🔍 [*] Checking if Barbara exists with: MATCH (p:Person {username: 'Barbara'}) RETURN p.userId, p.username")
            barbara_result = session.run("MATCH (p:Person {username: 'Barbara'}) RETURN p.userId, p.username")
            barbara_record = barbara_result.single()
            if barbara_record:
                print(f"✅ [+] Found Barbara: userId={barbara_record['p.userId']}, username='{barbara_record['p.username']}'")
            else:
                print("❌ [-] Barbara not found in database!")
                return None
            
            # Use SHORTEST 1 to find the shortest path
            cypher_query = """
                MATCH (start:Person {username: 'Rafał'})
                MATCH (end:Person {username: 'Barbara'})
                MATCH p = SHORTEST 1 (start)-[:KNOWS*]-(end)
                RETURN [n IN nodes(p) | n.username] AS path, length(p) AS pathLength
            """
            print("🔍 [*] Executing shortest path query:")
            print("    MATCH (start:Person {username: 'Rafał'})")
            print("    MATCH (end:Person {username: 'Barbara'})")
            print("    MATCH p = SHORTEST 1 (start)-[:KNOWS*]-(end)")
            print("    RETURN [n IN nodes(p) | n.username] AS path, length(p) AS pathLength")
            
            result = session.run(cypher_query)
            
            record = result.single()
            if record:
                path = record['path']
                path_length = record['pathLength']
                print(f"✅ [+] Found shortest path (length {path_length}): {' -> '.join(path)}")
                print(f"📊 [*] Path details: {path}")
                return path
            else:
                print("❌ [-] No path found between Rafał and Barbara")
                
                # Let's check what connections Rafał has
                print("🔍 [*] Checking Rafał's connections: MATCH (r:Person {username: 'Rafał'})-[:KNOWS]-(connected) RETURN connected.username")
                rafal_connections = session.run("MATCH (r:Person {username: 'Rafał'})-[:KNOWS]-(connected) RETURN connected.username")
                connections = [record['connected.username'] for record in rafal_connections]
                print(f"📊 [*] Rafał is connected to: {connections}")
                
                # Let's check what connections Barbara has
                print("🔍 [*] Checking Barbara's connections: MATCH (b:Person {username: 'Barbara'})-[:KNOWS]-(connected) RETURN connected.username")
                barbara_connections = session.run("MATCH (b:Person {username: 'Barbara'})-[:KNOWS]-(connected) RETURN connected.username")
                connections = [record['connected.username'] for record in barbara_connections]
                print(f"📊 [*] Barbara is connected to: {connections}")
                
                return None
    
    except Exception as e:
        print(f"❌ [-] Error finding shortest path: {str(e)}")
        import traceback
        print(f"❌ [-] Full traceback: {traceback.format_exc()}")
        return None


def submit_answer(path):
    """Submit the path to the central server."""
    print("📤 [*] Submitting answer...")
    
    # Convert path to comma-separated string
    path_string = ",".join(path)
    print(f"📊 [*] Path as array: {path}")
    print(f"📊 [*] Path as string: '{path_string}'")
    
    payload = {
        "task": "connections",
        "apikey": API_KEY,
        "answer": path_string
    }
    
    print(f"📦 [*] Submission payload:")
    print(f"    task: {payload['task']}")
    print(f"    apikey: {payload['apikey'][:10]}...")
    print(f"    answer: {payload['answer']}")
    print(f"📦 [*] Full payload: {json.dumps(payload, indent=2)}")
    
    try:
        print(f"🌐 [*] Sending POST request to: {CENTRALA_REPORT_URL}")
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ [+] HTTP Status Code: {response.status_code}")
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
        import traceback
        print(f"❌ [-] Full traceback: {traceback.format_exc()}")
        return None


def main():
    """Main execution function."""
    print("🚀 [*] Starting Connections task...")
    
    # Step 1: Fetch data from MySQL database
    users = fetch_users_data()
    if not users:
        print("❌ [-] Could not fetch users data")
        sys.exit(1)
    
    connections = fetch_connections_data()
    if not connections:
        print("❌ [-] Could not fetch connections data")
        sys.exit(1)
    
    # Step 2: Connect to Neo4j
    driver = create_neo4j_driver()
    if not driver:
        print("❌ [-] Could not connect to Neo4j")
        sys.exit(1)
    
    try:
        # Step 3: Clear and load data into Neo4j
        clear_neo4j_database(driver)
        load_users_to_neo4j(driver, users)
        load_connections_to_neo4j(driver, connections)
        
        # Step 4: Find shortest path
        path = find_shortest_path(driver)
        if not path:
            print("❌ [-] Could not find shortest path")
            sys.exit(1)
        
        print(f"📊 [*] Shortest path found: {' -> '.join(path)}")
        
        # Step 5: Submit the answer
        result = submit_answer(path)
        
        print("✅ [+] Task completed successfully!")
    
    finally:
        # Always close the driver
        driver.close()
        print("🔌 [*] Neo4j connection closed")


if __name__ == "__main__":
    main()
