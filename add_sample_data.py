#!/usr/bin/env python3
"""
Script to add sample bot and Q&A pairs for testing the rule engine.
Run this after database.py to populate with realistic data.
"""

from db import add_bot, add_qna, fetch_bot_by_slug, fetch_qna

def create_sample_bot():
    """Create a sample business bot with realistic Q&A pairs."""
    
    # Create a coffee shop bot
    print("Creating sample coffee shop bot...")
    bot_id = add_bot(
        slug="cozy-cafe",
        name="Cozy Café Helper", 
        theme="warm",
        visibility="public",
        fallback_message="Sorry, I'm not sure about that. You can call us at (555) 123-BREW or email hello@cozycafe.com!"
    )
    
    if not bot_id:
        print("❌ Failed to create bot")
        return None
    
    print(f"✅ Created bot with ID: {bot_id}")
    
    # Sample Q&A pairs with different priorities and keywords
    sample_qnas = [
        # High priority - most common questions
        {
            "question": "What are your hours?",
            "answer": "We're open Monday-Friday 7am-8pm, Saturday-Sunday 8am-6pm. We're closed on major holidays.",
            "keywords": "hours,open,closed,time,schedule",
            "priority": 10
        },
        {
            "question": "Where are you located?",
            "answer": "We're located at 123 Main Street, downtown next to the bookstore. There's street parking available!",
            "keywords": "location,address,where,directions,parking",
            "priority": 10
        },
        {
            "question": "Do you have WiFi?",
            "answer": "Yes! We have free WiFi. The password is 'CozyCoffee2024'. Perfect for remote work!",
            "keywords": "wifi,internet,password,work,laptop",
            "priority": 9
        },
        
        # Medium priority - menu related
        {
            "question": "What coffee do you serve?",
            "answer": "We serve locally roasted single-origin coffee, espresso drinks, cold brew, and seasonal specials. We also have decaf and oat milk options!",
            "keywords": "coffee,espresso,latte,cappuccino,menu,drinks",
            "priority": 8
        },
        {
            "question": "Do you have food?",
            "answer": "Yes! We have fresh pastries, sandwiches, salads, and daily soup. Everything is made fresh daily by our kitchen team.",
            "keywords": "food,eat,pastries,sandwich,salad,soup,hungry",
            "priority": 7
        },
        {
            "question": "Do you have vegan options?",
            "answer": "Absolutely! We have oat milk, almond milk, vegan pastries, and several plant-based sandwich options.",
            "keywords": "vegan,plant,dairy,milk,oat,almond",
            "priority": 6
        },
        
        # Lower priority - specific services
        {
            "question": "Can I reserve a table?",
            "answer": "We don't take reservations, but you can call ahead if you're bringing a large group (6+ people) and we'll do our best to accommodate!",
            "keywords": "reserve,reservation,table,group,book",
            "priority": 5
        },
        {
            "question": "Do you host events?",
            "answer": "We host small events like book clubs, acoustic music nights, and art shows. Contact us at events@cozycafe.com for details!",
            "keywords": "events,party,music,art,book,host",
            "priority": 4
        },
        {
            "question": "Are you hiring?",
            "answer": "We're always looking for great baristas! Drop off your resume or email it to jobs@cozycafe.com. Experience preferred but we'll train the right person.",
            "keywords": "hiring,job,work,barista,resume,employment",
            "priority": 3
        },
        
        # Edge cases for testing
        {
            "question": "What's your phone number?",
            "answer": "You can reach us at (555) 123-BREW. We answer during business hours!",
            "keywords": "phone,call,contact,number",
            "priority": 6
        },
        {
            "question": "Do you sell gift cards?",
            "answer": "Yes! Gift cards are available in $10, $25, and $50 amounts. Perfect for the coffee lover in your life!",
            "keywords": "gift,card,present,buy,money",
            "priority": 4
        }
    ]
    
    # Add all Q&A pairs
    added_count = 0
    for qna in sample_qnas:
        qna_id = add_qna(
            bot_id=bot_id,
            question=qna["question"],
            answer=qna["answer"],
            keywords=qna["keywords"],
            priority=qna["priority"]
        )
        if qna_id:
            added_count += 1
            print(f"  ✅ Added: {qna['question'][:50]}...")
        else:
            print(f"  ❌ Failed: {qna['question'][:50]}...")
    
    print(f"\n🎉 Successfully added {added_count}/{len(sample_qnas)} Q&A pairs!")
    return bot_id

def create_tech_support_bot():
    """Create a second sample bot for variety."""
    print("\nCreating sample tech support bot...")
    
    bot_id = add_bot(
        slug="tech-helper",
        name="TechCorp Support",
        theme="blue",
        visibility="unlisted",
        fallback_message="I couldn't find an answer to that. Please contact our support team at support@techcorp.com or call 1-800-TECH-HELP."
    )
    
    if not bot_id:
        print("❌ Failed to create tech bot")
        return None
    
    tech_qnas = [
        {
            "question": "How do I reset my password?",
            "answer": "Go to the login page and click 'Forgot Password'. Enter your email and we'll send you a reset link within 5 minutes.",
            "keywords": "password,reset,forgot,login,email",
            "priority": 10
        },
        {
            "question": "What browsers do you support?",
            "answer": "We support Chrome 90+, Firefox 88+, Safari 14+, and Edge 90+. For the best experience, keep your browser updated!",
            "keywords": "browser,chrome,firefox,safari,edge,support",
            "priority": 8
        },
        {
            "question": "How do I cancel my subscription?",
            "answer": "You can cancel anytime in your Account Settings > Billing. Your access continues until the end of your current billing period.",
            "keywords": "cancel,subscription,billing,account,refund",
            "priority": 7
        }
    ]
    
    added_count = 0
    for qna in tech_qnas:
        qna_id = add_qna(bot_id, qna["question"], qna["answer"], qna["keywords"], qna["priority"])
        if qna_id:
            added_count += 1
    
    print(f"✅ Added {added_count} tech support Q&As")
    return bot_id

def display_sample_data():
    """Display the created sample data for verification."""
    print("\n" + "="*60)
    print("SAMPLE DATA SUMMARY")
    print("="*60)
    
    # Show coffee shop bot
    cafe_bot = fetch_bot_by_slug("cozy-cafe")
    if cafe_bot:
        print(f"\n☕ {cafe_bot['name']} (slug: {cafe_bot['slug']})")
        print(f"   Theme: {cafe_bot['theme']}, Visibility: {cafe_bot['visibility']}")
        
        qnas = fetch_qna(cafe_bot['id'])
        print(f"   Q&A Pairs: {len(qnas)}")
        
        print("\n   Sample Q&As:")
        for qna in qnas[:3]:  # Show first 3
            print(f"   • Q: {qna['question']}")
            print(f"     A: {qna['answer'][:60]}...")
            print(f"     Keywords: {qna['keywords']}, Priority: {qna['priority']}\n")
    
    # Show tech bot
    tech_bot = fetch_bot_by_slug("tech-helper")
    if tech_bot:
        print(f"🔧 {tech_bot['name']} (slug: {tech_bot['slug']})")
        qnas = fetch_qna(tech_bot['id'])
        print(f"   Q&A Pairs: {len(qnas)}\n")

if __name__ == "__main__":
    print("🚀 Adding sample data for rule engine testing...\n")
    
    # Create sample bots
    cafe_id = create_sample_bot()
    tech_id = create_tech_support_bot()
    
    if cafe_id or tech_id:
        display_sample_data()
        print("\n✨ Sample data ready! You can now test the rule engine with:")
        print("   - 'cozy-cafe' bot (coffee shop)")
        print("   - 'tech-helper' bot (tech support)")
        print("\nTry questions like:")
        print("   • 'What time do you open?'")
        print("   • 'Do you have wifi?'")
        print("   • 'How do I reset my password?'")
    else:
        print("\n❌ Failed to create sample data")