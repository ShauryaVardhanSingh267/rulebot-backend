"""
RuleBot Backend API
Endpoints:
- GET /health
- POST /chat
- POST /api/bots
- GET /api/bots/<slug>
"""

import os
from flask import Flask, request, jsonify
from rules import match_rule
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok", "message": "RuleBot API is running!"}), 200

@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat endpoint.
    Expected JSON:
    {
      "bot": "cozy-cafe",
      "message": "do you have wifi"
    }
    """
    data = request.get_json()
    if not data or "bot" not in data or "message" not in data:
        return jsonify({
            "error": "Missing 'bot' or 'message' in request body"
        }), 400

    bot_slug = data["bot"]
    user_message = data["message"]

    result = match_rule(bot_slug, user_message)

    return jsonify({
        "bot": bot_slug,
        "message": user_message,
        "matched": result["matched"],
        "answer": result["answer"],
        "confidence": result["confidence"]
    }), 200

@app.route("/api/bots", methods=["POST"])
def create_bot():
    """Create a new bot with Q&A pairs"""
    data = request.get_json()
    
    if not data or not data.get("name") or not data.get("slug"):
        return jsonify({"error": "Missing bot name or slug"}), 400
    
    # Import the database functions we need
    from db import add_bot, add_qna
    
    # Create the bot
    bot_id = add_bot(
        slug=data["slug"],
        name=data["name"], 
        theme=data.get("theme", "arctic")
    )
    
    if not bot_id:
        return jsonify({"error": "Bot with this slug already exists"}), 409
    
    # Add Q&A pairs
    for pair in data.get("pairs", []):
        if pair.get("question") and pair.get("answer"):
            add_qna(bot_id, pair["question"], pair["answer"])
    
    return jsonify({
        "success": True, 
        "link": f"/chat/{data['slug']}"
    })

@app.route("/api/bots/<slug>", methods=["GET"])
def get_bot(slug):
    """Get bot details for the chat page"""
    from db import fetch_bot_by_slug, fetch_qna
    
    bot = fetch_bot_by_slug(slug)
    if not bot:
        return jsonify({"error": "Bot not found"}), 404
    
    pairs = fetch_qna(bot["id"])
    
    return jsonify({
        "name": bot["name"],
        "slug": bot["slug"], 
        "theme": bot["theme"],
        "pairs": [{"question": p["question"], "answer": p["answer"]} for p in pairs]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting RuleBot API on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)