"""
API Tool for LLM Function Calling

This module provides a tool that LLM can use to execute HTTP requests
with additional context and hints for better decision making.
"""
import json
import requests
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path for utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import make_request


def execute_api_request_with_context(
    url: str,
    method: str = "GET", 
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    context: Optional[str] = None,
    hints: Optional[str] = None,
    **kwargs  # Catch any additional parameters
) -> str:
    """
    Execute HTTP request with additional context and hints.
    
    Args:
        url: Target URL for the request
        method: HTTP method (GET, POST, PUT, DELETE)
        payload: JSON payload for POST/PUT requests
        headers: HTTP headers as key-value pairs
        context: Additional context about what this request should accomplish
        hints: Hints about expected response format or what to look for
    
    Returns:
        JSON string with response details including status, content, and analysis
    """
    try:
        print(f"🌐 [*] Executing API request with context")
        print(f"    URL: {url}")
        print(f"    Method: {method}")
        
        if payload:
            print(f"    Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if headers:
            print(f"    Headers: {json.dumps(headers, indent=2)}")
        
        if context:
            print(f"    Context: {context}")
            
        if hints:
            print(f"    Hints: {hints}")
        
        # Handle additional parameters by merging them into payload
        if kwargs:
            print(f"    Additional params: {kwargs}")
            if payload is None:
                payload = {}
            payload.update(kwargs)
        
        # Execute the request
        if method.upper() == "POST":
            response = make_request(
                url, 
                method="post", 
                json=payload, 
                headers=headers or {}
            )
        elif method.upper() == "PUT":
            response = make_request(
                url, 
                method="put", 
                json=payload, 
                headers=headers or {}
            )
        elif method.upper() == "DELETE":
            response = make_request(
                url, 
                method="delete", 
                headers=headers or {}
            )
        else:  # GET
            response = make_request(
                url, 
                method="get", 
                headers=headers or {}
            )
        
        # Parse response
        try:
            response_json = response.json()
        except:
            response_json = None
        
        # Build comprehensive result
        result = {
            "request": {
                "url": url,
                "method": method.upper(),
                "payload": payload,
                "headers": headers,
                "context": context,
                "hints": hints
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
                "json": response_json,
                "success": 200 <= response.status_code < 300
            },
            "analysis": {
                "content_type": response.headers.get('content-type', ''),
                "content_length": len(response.text),
                "is_json": response_json is not None,
                "has_error": response.status_code >= 400
            }
        }
        
        # Add contextual analysis if hints provided
        if hints and response.text:
            analysis_notes = []
            
            if "password" in hints.lower() or "hasło" in hints.lower():
                if "success" in response.text.lower():
                    analysis_notes.append("Response indicates successful password authentication")
                elif "error" in response.text.lower():
                    analysis_notes.append("Response indicates password error")
            
            if "json" in hints.lower() and response_json:
                analysis_notes.append(f"JSON response with {len(response_json)} field(s)")
            
            if "flag" in hints.lower():
                if "FLG:" in response.text:
                    analysis_notes.append("Response contains flag pattern")
            
            result["analysis"]["hints_analysis"] = analysis_notes
        
        formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
        print(f"📨 [*] API Response analysis:")
        print(formatted_result)
        
        return formatted_result
        
    except Exception as e:
        error_result = {
            "request": {
                "url": url,
                "method": method,
                "payload": payload,
                "context": context,
                "hints": hints
            },
            "error": str(e),
            "success": False
        }
        
        formatted_error = json.dumps(error_result, ensure_ascii=False, indent=2)
        print(f"❌ [-] API Request failed:")
        print(formatted_error)
        
        return formatted_error


# OpenAI Function Definition
API_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "execute_api_request_with_context",
        "description": "Execute HTTP request to any URL with payload, headers, context and hints for better analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to make request to"
                },
                "method": {
                    "type": "string", 
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET"
                },
                "payload": {
                    "type": "object",
                    "description": "JSON payload for POST/PUT requests"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers as key-value pairs"
                },
                "context": {
                    "type": "string",
                    "description": "Context about what this request should accomplish (e.g. 'authenticate with password', 'get user data')"
                },
                "hints": {
                    "type": "string", 
                    "description": "Hints about expected response or what to look for (e.g. 'expect JSON with success field', 'look for flag pattern')"
                },
                "password": {
                    "type": "string",
                    "description": "Password parameter if needed for the request"
                },
                "apikey": {
                    "type": "string", 
                    "description": "API key parameter if needed for the request"
                }
            },
            "required": ["url"],
            "additionalProperties": True
        }
    }
} 