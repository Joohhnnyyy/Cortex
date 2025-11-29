from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json
import os
import logging

# Assuming ai_modules.py and gemini_assistant.py are in the same directory
from ai_modules import AIModules
from gemini_assistant import GeminiAssistant
from demo_mode import DemoAIModules, get_demo_chatbot_response
import web_scraper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialization ---
try:
    gemini_assistant = GeminiAssistant()
    logger.info("Gemini Assistant Initialized.")
except Exception as e:
    logger.error(f"Gemini Assistant initialization failed: {e}")
    gemini_assistant = None
    logger.warning("Running in demo mode without AI features.")

# --- Load your e-commerce data from JSON ---
def load_data(file_path='data/data.json'):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{file_path} not found. Please run generate_mock_data.py.")
        return {}

# Cache data and AI modules
cached_data = load_data()
# Pass the Gemini assistant instance to AIModules
try:
    if cached_data and gemini_assistant:
        cached_ai_modules = AIModules(cached_data, gemini_assistant)
    else:
        logger.info("Using demo mode for AI modules")
        cached_ai_modules = DemoAIModules()
except Exception as e:
    logger.error(f"AIModules initialization failed: {e}")
    logger.info("Falling back to demo mode")
    cached_ai_modules = DemoAIModules()

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app) # Enable CORS for frontend

# --- Frontend Route ---

@app.route('/')
def index():
    """Serve the main dashboard interface."""
    return render_template('index.html')

# --- Dashboard Data API Routes ---

@app.route('/api/overview', methods=['GET'])
def get_day_wise_overview():
    """Provides day-wise financials for the homepage overview."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    
    # Using the growth analysis data for daily revenue visualization
    data = cached_ai_modules.analyze_ecom_growth_and_trends()
    # Ensure dates are JSON-serializable strings
    daily = data.get("daily_sales_data", [])
    serialized_daily = []
    for r in daily:
        # r may contain a pandas.Timestamp under 'date'
        d = r.get('date')
        try:
            # Attempt to convert to ISO string
            if hasattr(d, 'isoformat'):
                dstr = d.isoformat()
            else:
                dstr = str(d)
        except Exception:
            dstr = str(d)
        newr = dict(r)
        newr['date'] = dstr
        serialized_daily.append(newr)

    return jsonify({
        "metrics": data.get("growth_metrics", {}),
        "daily_sales_chart_data": serialized_daily
    })

@app.route('/api/financials/insights', methods=['GET'])
def get_financial_insights_route():
    """Presents raw P&L data and GenAI CA summary."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    return jsonify(cached_ai_modules.get_financial_insights())

@app.route('/api/financials/tax-advice', methods=['GET'])
def get_tax_advice_route():
    """GenAI advice on tax deductions and ITR filing."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    return jsonify(cached_ai_modules.get_tax_deduction_advice())

@app.route('/api/inventory/automation', methods=['GET'])
def get_inventory_automation_route():
    """Low stock alerts and restock action triggers."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    return jsonify(cached_ai_modules.analyze_inventory_and_restock())

@app.route('/api/sku/market-analysis', methods=['GET'])
def get_sku_market_analysis_route():
    """Competitor data and GenAI pricing advice for P001 (mock SKU)."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    
    comp = cached_ai_modules.get_competitor_data()
    # get_competitor_data may return a list (mock scraper) or a dict with error
    if isinstance(comp, dict) and comp.get('error'):
        return jsonify({"error": comp.get('error')}), 500

    competitor_data = comp if isinstance(comp, list) else []

    return jsonify(cached_ai_modules.analyze_sku_market_and_trend(competitor_data, product_id='P001'))


@app.route('/api/competitor/data', methods=['GET'])
def get_competitor_data_route():
    """Return current competitor products list (demo or scraped)."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    comp = cached_ai_modules.get_competitor_data()
    if isinstance(comp, dict) and comp.get('error'):
        return jsonify({"error": comp.get('error')}), 500
    items = comp if isinstance(comp, list) else []
    return jsonify({"products": items, "count": len(items)})


@app.route('/api/competitor/scrape', methods=['POST', 'GET'])
def scrape_competitor_route():
    """Trigger competitor scraping (mock) and save results to `data/competitor_data.json`."""
    try:
        scraped = web_scraper.scrape_competitor_data()
        web_scraper.save_to_json(scraped, filename='competitor_data.json')
        return jsonify({"status": "ok", "saved_to": "data/competitor_data.json", "sample": scraped[:5]})
    except Exception as e:
        logger.error(f"Competitor scraping failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/inventory/trends', methods=['GET'])
def inventory_trends_route():
    """Return recent sales timeseries for a product. Query param: product_id (default P001)"""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500

    product_id = request.args.get('product_id', 'P001')
    days = int(request.args.get('days', 30))
    return jsonify(cached_ai_modules.get_inventory_trends(product_id=product_id, days=days))


@app.route('/api/email/restock', methods=['POST'])
def restock_email_route():
    """Prototype endpoint: accepts restock email payload and either sends via SMTP or saves to file.

    Expected JSON: { to: str, subject: str, body: str }
    """
    payload = request.json or {}
    to = payload.get('to')
    subject = payload.get('subject')
    body = payload.get('body')

    if not to or not subject or not body:
        return jsonify({"error": "Missing to/subject/body in request."}), 400

    # Try to send via SMTP if configured
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587')) if os.getenv('SMTP_PORT') else None
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')

    email_record = {"to": to, "subject": subject, "body": body}

    if smtp_host and smtp_port and smtp_user and smtp_pass:
        try:
            import smtplib
            from email.message import EmailMessage
            msg = EmailMessage()
            msg['From'] = smtp_user
            msg['To'] = to
            msg['Subject'] = subject
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)

            return jsonify({"status": "sent"})
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            # fall through to saving

    # Save to outgoing_emails.json as fallback
    out_path = 'data/outgoing_emails.json'
    try:
        os.makedirs('data', exist_ok=True)
        existing = []
        if os.path.exists(out_path):
            with open(out_path, 'r') as f:
                existing = json.load(f)
        existing.append(email_record)
        with open(out_path, 'w') as f:
            json.dump(existing, f, indent=2)
        return jsonify({"status": "saved", "path": out_path})
    except Exception as e:
        logger.error(f"Failed to save outgoing email: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/loyalty', methods=['GET'])
def get_customer_loyalty_route():
    """Customer list with GenAI loyalty reward recommendations."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    return jsonify(cached_ai_modules.get_active_customer_loyalty_rewards())

@app.route('/api/invoice/<string:purchase_id>', methods=['GET'])
def get_invoice_route(purchase_id):
    """Automated Invoice Generation details."""
    if not cached_ai_modules:
        return jsonify({"error": "System not initialized"}), 500
    return jsonify(cached_ai_modules.get_invoice(purchase_id))

# --- GenAI Chatbot Route ---

@app.route('/ai/chatbot', methods=['POST'])
def ai_chatbot_route():
    """
    Main conversational endpoint for the owner.
    Uses GenAI to answer questions based on current business data.
    """
    user_query = request.json.get('query')
    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    if not cached_ai_modules or not gemini_assistant:
        return jsonify({"response": "AI Assistant is unavailable (API key error or data not loaded)."}), 500
        
    # Provide the Chatbot with the most relevant context (P&L and Inventory)
    business_context = {
        "financial_summary": cached_ai_modules.get_financial_summary(),
        "inventory_status": cached_ai_modules.analyze_inventory_and_restock().get("low_stock_report", [])
    }
    
    if gemini_assistant:
        try:
            response_text = gemini_assistant.chatbot_query(user_query, business_context)
            if isinstance(response_text, str) and response_text.strip().startswith("Sorry, I'm having trouble"):
                logger.warning("Gemini returned fallback apology; switching to demo response")
                response_text = get_demo_chatbot_response(user_query)
        except Exception as e:
            logger.exception(f"Gemini chatbot query error: {e}")
            response_text = get_demo_chatbot_response(user_query)
    else:
        response_text = get_demo_chatbot_response(user_query)
    
    return jsonify({"response": response_text})

@app.route('/api/health', methods=['GET'])
def health_route():
    """Lightweight health check for deploy platforms."""
    try:
        ok = bool(cached_ai_modules)
        return jsonify({"status": "ok", "ai_modules": ok}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Run the app ---
if __name__ == '__main__':
    # Ensure competitor data exists for the prototype to run smoothly
    if not os.path.exists('data/competitor_data.json'):
        logger.warning("Competitor data missing. Please run web_scraper.py once.")
    
    # Use environment variable for debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    app.run(debug=debug_mode, host=host, port=port)
