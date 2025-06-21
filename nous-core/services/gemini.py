"""
Handles Gemini API integration for:
- PDF to Lexical JSON conversion
- Lexical JSON to narration/plaintext
- Generating search keywords
"""

from google import genai
from google.genai import types
import os
import json
import re

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBhMsWWmv-pnU0ADXZu4LMu6nJ0u6wBrJE")

client = genai.Client(api_key=GEMINI_API_KEY)

# PDF to Lexical JSON (children array only)
def pdf_to_lexical(pdf_path: str, prompt: str) -> dict:
    """
    Sends a PDF and prompt to Gemini and returns Lexical JSON (children array).
    Uses Gemini's native PDF vision support with validation and error correction.
    """
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Try up to 3 times to get valid JSON
    for attempt in range(3):
        try:
            print(f"Gemini API attempt {attempt + 1}/3...")
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",  # Updated to latest model
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
                    prompt
                ]
            )
            raw = response.text.strip()
            
            # Log the raw response for debugging
            print(f"Attempt {attempt + 1} - Raw response length: {len(raw)}")
            print(f"Raw response preview: {raw[:200]}...")
            
            # Clean up the response
            raw = clean_json_response(raw)
            
            # Additional check for problematic patterns before parsing
            if "{'children':" in raw and '{"children":' not in raw:
                print("WARNING: Detected Python dict syntax in response, attempting to fix...")
                # Try to convert Python dict syntax to JSON
                raw = raw.replace("'", '"')
                raw = re.sub(r'(\w+):', r'"\1":', raw)  # Add quotes around unquoted keys
            
            # Parse and validate the JSON
            parsed_json = json.loads(raw)
            
            # Validate the structure
            validated_json = validate_lexical_structure(parsed_json)
            
            # Final safety check - ensure we have actual content
            if not validated_json or len(validated_json) == 0:
                raise ValueError("Validated JSON is empty")
            
            print(f"Successfully parsed {len(validated_json)} nodes")
            return validated_json
            
        except Exception as e:
            # Check for specific Gemini API errors
            if hasattr(e, '__class__') and 'ServerError' in str(e.__class__):
                print(f"Gemini API Server Error (attempt {attempt + 1}): {e}")
                if "500 INTERNAL" in str(e):
                    print("Gemini API is experiencing internal server issues")
                if attempt == 2:  # Last attempt
                    raise Exception("Gemini AI service is currently unavailable. Please try again in a few minutes.")
                continue
            elif hasattr(e, '__class__') and 'QuotaExceeded' in str(e.__class__):
                print(f"Gemini API Quota Exceeded: {e}")
                raise Exception("AI service quota exceeded. Please try again later.")
            elif isinstance(e, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
                print(f"Attempt {attempt + 1} failed (parsing error): {e}")
                print(f"Problematic content: {raw[:500] if 'raw' in locals() else 'N/A'}")
                if attempt == 2:  # Last attempt
                    # Return a fallback structure
                    print("All attempts failed, using fallback structure")
                    return create_fallback_lesson_structure()
            else:
                print(f"Unexpected error (attempt {attempt + 1}): {e}")
                if attempt == 2:  # Last attempt
                    raise Exception(f"AI processing failed after 3 attempts: {str(e)}")
    
    return create_fallback_lesson_structure()

def clean_json_response(raw: str) -> str:
    """Clean up Gemini's response to extract valid JSON"""
    # Remove triple backticks and optional 'json' language tag
    if raw.startswith("```"):
        raw = raw.lstrip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    
    # Remove any text before the first [ or {
    start_idx = min(
        raw.find('[') if raw.find('[') != -1 else len(raw),
        raw.find('{') if raw.find('{') != -1 else len(raw)
    )
    if start_idx < len(raw):
        raw = raw[start_idx:]
    
    # Remove any text after the last ] or }
    end_idx = max(raw.rfind(']'), raw.rfind('}'))
    if end_idx != -1:
        raw = raw[:end_idx + 1]
    
    # Check for malformed object representations (strings that look like objects)
    if "{'children':" in raw or '{"children":' in raw:
        # This indicates the AI returned stringified objects instead of proper JSON
        print("WARNING: Detected stringified objects in response")
        # Try to fix common single quote issues
        raw = raw.replace("'", '"')
        # Remove any remaining problematic patterns
        raw = re.sub(r"{\s*'[^']*':\s*\[", '{"children":[', raw)
    
    return raw

def validate_lexical_structure(data) -> list:
    """Validate and fix common issues in Lexical JSON structure"""
    if not isinstance(data, list):
        # If it's wrapped in an object, extract the children array
        if isinstance(data, dict) and 'children' in data:
            data = data['children']
        else:
            raise ValueError("Expected array of Lexical nodes")
    
    validated_nodes = []
    for node in data:
        if not isinstance(node, dict):
            # Skip non-dict nodes (might be stringified objects that couldn't be parsed)
            print(f"Skipping non-dict node: {node}")
            continue
        
        # Check for stringified object patterns within the node
        for key, value in node.items():
            if isinstance(value, str) and value.startswith("{'") and value.endswith("}"):
                print(f"Found stringified object in {key}: {value}")
                # This shouldn't happen with proper JSON, skip this node
                continue
                
        # Fix common type issues
        if node.get('type') == 'listItem':
            node['type'] = 'listitem'
        
        # Ensure list items have proper structure
        if node.get('type') == 'listitem':
            node = fix_list_item_structure(node)
        
        # Ensure lists have proper structure
        if node.get('type') == 'list':
            node = fix_list_structure(node)
        
        # Ensure text nodes have proper structure
        if node.get('type') == 'text':
            node = fix_text_node_structure(node)
        
        # Ensure all nodes have required fields
        node = ensure_required_fields(node)
        
        validated_nodes.append(node)
    
    return validated_nodes

def fix_list_item_structure(node: dict) -> dict:
    """Fix list item structure issues"""
    # Ensure required fields
    required_fields = {
        'type': 'listitem',
        'version': 1,
        'direction': 'ltr',
        'format': '',
        'indent': 0,
        'value': 1
    }
    
    for field, default_value in required_fields.items():
        if field not in node:
            node[field] = default_value
    
    # Ensure children are text nodes, not paragraphs
    if 'children' in node:
        text_children = []
        for child in node['children']:
            if child.get('type') == 'paragraph' and 'children' in child:
                # Extract text from paragraph
                text_children.extend(child['children'])
            elif child.get('type') == 'text':
                text_children.append(fix_text_node_structure(child))
        node['children'] = text_children
    
    return node

def fix_list_structure(node: dict) -> dict:
    """Fix list structure issues"""
    # Ensure required fields
    required_fields = {
        'type': 'list',
        'version': 1,
        'direction': 'ltr',
        'format': '',
        'indent': 0,
        'start': 1
    }
    
    for field, default_value in required_fields.items():
        if field not in node:
            node[field] = default_value
    
    # Ensure listType and tag are consistent
    if node.get('listType') == 'bullet':
        node['tag'] = 'ul'
    elif node.get('listType') == 'number':
        node['tag'] = 'ol'
    else:
        node['listType'] = 'bullet'
        node['tag'] = 'ul'
    
    # Fix all children to be proper list items
    if 'children' in node:
        fixed_children = []
        for child in node['children']:
            if child.get('type') != 'listitem':
                # Convert to list item
                child = {
                    'type': 'listitem',
                    'version': 1,
                    'direction': 'ltr',
                    'format': '',
                    'indent': 0,
                    'value': 1,
                    'children': [fix_text_node_structure({'type': 'text', 'text': str(child)})]
                }
            else:
                child = fix_list_item_structure(child)
            fixed_children.append(child)
        node['children'] = fixed_children
    
    return node

def fix_text_node_structure(node: dict) -> dict:
    """Fix text node structure issues"""
    required_fields = {
        'type': 'text',
        'version': 1,
        'detail': 0,
        'format': 0,
        'mode': 'normal',
        'style': '',
        'text': ''
    }
    
    for field, default_value in required_fields.items():
        if field not in node:
            node[field] = default_value
    
    # Ensure text is a string
    if not isinstance(node['text'], str):
        node['text'] = str(node['text'])
    
    return node

def ensure_required_fields(node: dict) -> dict:
    """Ensure all nodes have basic required fields"""
    if 'version' not in node:
        node['version'] = 1
    
    if node.get('type') in ['paragraph', 'heading', 'list', 'listitem']:
        if 'direction' not in node:
            node['direction'] = 'ltr'
        if 'format' not in node:
            node['format'] = ''
        if 'indent' not in node:
            node['indent'] = 0
    
    return node

def create_fallback_lesson_structure() -> list:
    """Create a basic lesson structure when parsing fails"""
    return [
        {
            "type": "heading",
            "version": 1,
            "direction": "ltr",
            "format": "",
            "indent": 0,
            "tag": "h1",
            "children": [
                {
                    "type": "text",
                    "version": 1,
                    "detail": 0,
                    "format": 0,
                    "mode": "normal",
                    "style": "",
                    "text": "Lesson Content"
                }
            ]
        },
        {
            "type": "paragraph",
            "version": 1,
            "direction": "ltr",
            "format": "",
            "indent": 0,
            "textFormat": 0,
            "textStyle": "",
            "children": [
                {
                    "type": "text",
                    "version": 1,
                    "detail": 0,
                    "format": 0,
                    "mode": "normal",
                    "style": "",
                    "text": "The lesson content could not be properly parsed from the PDF. Please try uploading the document again or contact support for assistance."
                }
            ]
        }
    ]

# Lexical JSON to narration/plaintext
def lexical_to_narration(lexical_json: dict) -> str:
    """
    Converts Lexical JSON to narration/plaintext using Gemini.
    Ensures that any math expressions are spelled out in English words (as they would be spoken), so that the TTS model pronounces them correctly.
    Also instructs not to use asterisks for intonation, and to use commas or punctuation minimally and only where truly appropriate, since these may be spoken out loud by TTS.
    """
    try:
        prompt = (
            "Convert the following Lexical JSON lesson content into a clear, engaging narration suitable for audio."
            "The Narration must be like how a human Teacher would talk. Talk in a way that attracts attention and easy to understand. "
            "AVOID USING asterisks or similar symbols outside math/scientific expressions or for intonation or emphasis. Only use newline characters."
            "Focus on clarity, flow, and engagement, ensuring it sounds natural when spoken, and is suitable for text-to-speech conversion. "
            "For any math expressions, spell them out in English words as they would be spoken (e.g., 'x squared plus y equals 10'). "
            "Ensure that the narration when spoken won't exceed 10 minutes. Output only the narration text.\n\nLexical JSON:\n" + json.dumps(lexical_json)
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini narration generation failed: {e}")
        if "500 INTERNAL" in str(e):
            raise Exception("AI narration service is temporarily unavailable")
        elif "QuotaExceeded" in str(e):
            raise Exception("AI service quota exceeded for narration generation")
        else:
            raise Exception(f"Narration generation failed: {str(e)}")

# Generate search keywords from Lexical JSON
def get_keywords(lexical_json: dict) -> list:
    """
    Generates 3-5 search keywords from Lexical JSON using Gemini.
    """
    try:
        prompt = (
            "Given the following Lexical JSON lesson content, extract 3-5 relevant search keywords as a JSON array of strings. "
            "Output only the JSON array.\n\nLexical JSON:\n" + json.dumps(lexical_json)
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = response.text.strip()
        # Remove triple backticks and optional 'json' language tag
        if raw.startswith("```"):
            raw = raw.lstrip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        return json.loads(raw)
    except Exception as e:
        print(f"Gemini keywords extraction failed: {e}")
        # Return fallback keywords instead of failing completely
        return ["education", "learning", "lesson"]
