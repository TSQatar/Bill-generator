import os
import json
import math
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import pandas as pd
import io

load_dotenv()

# Configure Gemini
GENAI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    # Fallback for development if env var is missing, though user said they have .env
    print("Warning: GOOGLE_API_KEY not found in environment variables.")

genai.configure(api_key=GENAI_API_KEY)

def get_gemini_response(image, prompt):
    """
    Sends image and prompt to Gemini Flash and returns the text response.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content([prompt, image])
    return response.text

def extract_data_from_image(image_file):
    """
    Extracts structured data from the image using Gemini.
    Returns a list of dictionaries: [{title, emoji, details, quantity, price}, ...]
    """
    image = Image.open(image_file)
    
    prompt = """
    You are an expert data extractor. Your task is to extract shopping cart items from the provided screenshot.
    
    For each item, extract the following fields:
    1.  **Short Title**: A concise name for the item (e.g., "Accordion File Bag", "Phone Case").
    2.  **Emoji**: A single relevant emoji matching the item (e.g., 🗂️, 📱, 👟).
    3.  **Details**: A comprehensive yet clean summary of all visible options (Color, Size, Model, Capacity, Dimensions). Avoid generic words like "Details:". Example: "Color: Blue, Size: A4" or "60 Colors, Dual-Tip".
    4.  **Quantity**: The quantity of the item. If not visible, default to 1.
    5.  **Price**: The price of the item as a number (remove currency symbols like QAR, SAR, AED, $, etc.).
    
    Return the result strictly as a JSON array of objects. Do not include markdown formatting (```json ... ```).
    Example format:
    [
        {"title": "Phone Case", "emoji": "📱", "details": "Black, iPhone 13", "quantity": 1, "price": 25.50},
        {"title": "Running Shoes", "emoji": "👟", "details": "Size 42, White", "quantity": 2, "price": 150.00}
    ]
    """
    
    try:
        print(f"DEBUG: Sending request to Gemini model: gemini-2.0-flash")
        response_text = get_gemini_response(image, prompt)
        print(f"DEBUG: Received response from Gemini: {response_text[:100]}...") # Print first 100 chars
        
        # Clean up potential markdown formatting
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_text)
        return data
    except Exception as e:
        print(f"ERROR extracting data: {e}")
        return []

def format_bill_output(items, store_name):
    """
    Formats the extracted items into the specific 'TSQA – Provisional Bill' text format.
    """
    
    # Header
    bill_text = f"🧾 TSQA – Provisional Bill - {store_name}\n📦 Order in Process\n\n"
    
    subtotal = 0.0
    
    for item in items:
        # Parse values
        try:
            qty = int(item.get('quantity', 1))
            price = float(item.get('price', 0.0))
            total_item_price = price # Usually cart screenshots show unit price or total? 
            # Assumption: The price extracted is the price displayed. 
            # If the screenshot shows "Total Price" for the line item, we use that. 
            # If it shows "Unit Price", we might need to multiply. 
            # Usually screenshots show the final price for that line item. 
            # Let's assume the extracted price is the relevant cost to add to subtotal.
            # WAIT: If quantity is 2, usually the displayed price is per unit OR total.
            # Let's assume the extracted price is the UNIT price for now, or the total line price?
            # User prompt said: "Price: List the price. 💰 [Price] QAR"
            # And "Summary Table... Unit Price (QAR), and Qty."
            # So we should treat extracted price as UNIT PRICE.
            
            # However, for the subtotal calculation, we need (Price * Qty).
            line_total = price * qty
            subtotal += line_total
            
            # Item Listing
            bill_text += f"{item.get('emoji', '▫️')} {item.get('title', 'Item')}\n"
            bill_text += f"▫️ {item.get('details', '')}\n"
            if qty > 1:
                bill_text += f"▫️ Qty {qty}\n"
            else:
                bill_text += f"▫️ Qty 1\n" # Default as per requirement
            
            bill_text += f"💰 {price:.2f} QAR\n\n"
            
        except ValueError:
            continue

    # Separator
    bill_text += "──────────────\n"
    
    # Delivery Fee
    bill_text += "🚚 Delivery Fee: (select via Google form)\n"
    
    # Total Calculation
    # "The subtotal must be rounded up to the next whole number (using the ceiling function)."
    rounded_total = math.ceil(subtotal)
    
    bill_text += f"✅ Provisional Total: {rounded_total} QAR + Delivery fee\n\n"
    
    # Closing
    bill_text += "Thank you for shopping with TSQA 💙 Packed with care – delivered with love 🥰\n"
    
    return bill_text, subtotal

def create_summary_dataframe(items):
    """
    Creates a pandas DataFrame for the summary table.
    """
    data = []
    for item in items:
        data.append({
            "Item": f"{item.get('emoji', '')} {item.get('title', '')}\n{item.get('details', '')}",
            "Unit Price (QAR)": item.get('price', 0.0),
            "Qty": item.get('quantity', 1)
        })
    return pd.DataFrame(data)
