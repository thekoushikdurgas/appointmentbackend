"""Seed script to populate MongoDB with marketing page content from hardcoded frontend data."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.mongodb import get_mongodb_database, close_mongodb_connection
from app.repositories.marketing_repository import MarketingRepository


async def seed_ai_writer_page(repo: MarketingRepository):
    """Seed AI Email Writer page."""
    data = {
        "page_id": "ai-email-writer",
        "metadata": {
            "title": "AI Email Writer",
            "description": "Turn cold leads into warm conversations with AI-powered email personalization",
            "keywords": ["AI", "email", "personalization", "sales", "outreach"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Turn cold leads into warm conversations.",
            "subtitle": "Hyper-Personalization AI",
            "description": "Stop sending generic templates that get ignored. Our AI analyzes your prospect's LinkedIn profile, company news, and tech stack to craft hyper-relevant emails that actually get replies.",
            "features": [
                "Analyze LinkedIn profiles & company news",
                "Generate context-aware email drafts",
                "45%+ open rate optimization",
                "3x more meetings booked",
                "Integrates with your CRM workflow",
            ],
            "cta_text": "Try the AI Email Writer",
            "cta_href": "/register",
        },
        "sections": {
            "funnel_impact": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "The Compound Effect of AI Personalization",
                "description": "It's not just about writing faster. It's about optimizing every step of your sales funnel. From the first send to the closed deal, AI improves every metric that matters.",
                "steps": [
                    {
                        "title": "99% Inbox Rate",
                        "description": "Unique, non-templated content bypasses spam filters that block generic blasts.",
                        "icon": "Inbox",
                        "color": "blue",
                    },
                    {
                        "title": "3x Response Rate",
                        "description": "Hyper-personalized hooks prove you've done your homework, earning replies.",
                        "icon": "MessageSquare",
                        "color": "indigo",
                    },
                    {
                        "title": "2x Qualified Leads",
                        "description": "Relevant value props filter out tire-kickers and attract serious buyers.",
                        "icon": "Users",
                        "color": "purple",
                    },
                    {
                        "title": "More Meetings",
                        "description": "Clear, context-aware Calls to Action make saying \"yes\" to a demo easy.",
                        "icon": "Calendar",
                        "color": "pink",
                    },
                    {
                        "title": "Higher Revenue",
                        "description": "A predictable pipeline of warm leads directly translates to closed-won deals.",
                        "icon": "DollarSign",
                        "color": "green",
                    },
                ],
            },
            "writer_workflow": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "Your new 3-step writing workflow",
                "description": "From blank page to \"Sent\" in under 30 seconds.",
                "steps": [
                    {
                        "title": "1. Connect Context",
                        "description": "Open the extension on any LinkedIn profile or website. We automatically scrape relevant data.",
                        "icon": "Link",
                    },
                    {
                        "title": "2. Generate Draft",
                        "description": "Select a tone and value prop. Our AI generates a unique, researched message instantly.",
                        "icon": "Sparkles",
                    },
                    {
                        "title": "3. Review & Send",
                        "description": "Make quick edits if needed, then sync directly to your CRM or send via Gmail/Outlook.",
                        "icon": "Send",
                    },
                ],
            },
            "before_after_comparison": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "upgrade_message": "Upgrade to Pro to see real comparison examples and case studies"
                },
                "title": "See the difference AI makes",
                "description": "Generic templates get ignored. Our AI reads the prospect's LinkedIn, company news, and website to write emails that look manually researched.",
                "badge": "The AI Advantage",
                "before": {
                    "label": "Without AI",
                    "content": "Hi {FirstName},\n\nI hope you are doing well.\n\nI would like to introduce our company and see if you have time for a quick chat about synergies.\n\nLet me know when you are free.",
                    "badge": "1.5% Reply Rate",
                    "flags": ["Generic", "Self-centered", "No context"],
                },
                "after": {
                    "label": "With Contact360",
                    "content": "Hi Sarah,\n\nSaw your post about expanding the sales team — congrats on the Series B!\n\nScaling typically breaks data processes. Since you're using Salesforce, our native integration can help your new reps ramp up 2x faster by auto-filling valid contact info.\n\nWorth a 5 min chat?",
                    "badge": "18% Reply Rate",
                    "flags": ["Funding News", "Tech Stack (Salesforce)", "Hiring intent"],
                },
            },
            "writer_integrations": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "Seamlessly integrates with your stack",
                "integrations": [
                    {"name": "Gmail", "color": "red"},
                    {"name": "Outlook", "color": "blue"},
                    {"name": "Salesforce", "color": "blue-light"},
                    {"name": "HubSpot", "color": "orange"},
                    {"name": "Outreach", "color": "purple"},
                    {"name": "Salesloft", "color": "indigo"},
                    {"name": "Pipedrive", "color": "green"},
                ],
            },
            "writer_social_proof": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "partial",
                    "upgrade_message": "Upgrade to Pro to see verified customer testimonials and case studies"
                },
                "title": "Trusted by top performing revenue teams",
                "description": "Join 10,000+ sales professionals who have automated their outreach with Contact360.",
                "testimonials": [
                    {
                        "quote": "I was skeptical about AI emails, but Contact360 proved me wrong. The personalization is scary good. I booked 4 demos in my first week.",
                        "author": "Marcus Chen",
                        "role": "Enterprise SDR",
                        "company": "Adobe",
                        "image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=100&h=100&q=80",
                        "impact": "40% Open Rate",
                    },
                    {
                        "quote": "It captures our brand voice perfectly. We reduced our outreach time by 70% while actually increasing the quality of every email sent.",
                        "author": "Sarah Jenkins",
                        "role": "Head of Growth",
                        "company": "Linear",
                        "image": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
                        "impact": "3x More Meetings",
                    },
                    {
                        "quote": "The ability to pull recent news and weave it into the value prop is a game changer. It does the research I usually skip.",
                        "author": "David Okonjo",
                        "role": "Account Executive",
                        "company": "Vercel",
                        "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
                        "impact": "2 hrs saved/day",
                    },
                ],
            },
            "ai_benefits": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "upgrade_message": "Upgrade to Pro to unlock advanced AI features and benefits"
                },
                "benefits": [
                    {
                        "title": "Kill Writer's Block Forever",
                        "description": "Spend time closing, not staring at a blank cursor. Generate 50 personalized drafts in the time it takes to write one manually.",
                        "icon": "Clock",
                        "color": "blue",
                    },
                    {
                        "title": "Psychological Tone Matching",
                        "description": "Our AI analyzes the prospect's LinkedIn posts to detect their personality type and matches the email tone (Direct, Friendly, Analytical) accordingly.",
                        "icon": "BrainCircuit",
                        "color": "purple",
                    },
                    {
                        "title": "Unique Content = Inbox",
                        "description": "Spam filters block identical templates sent in bulk. AI ensures every single email is unique, boosting your deliverability and domain reputation.",
                        "icon": "Shield",
                        "color": "orange",
                    },
                ],
            },
            "writer_faq": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "Frequently Asked Questions",
                "faqs": [
                    {
                        "question": "Does this work in languages other than English?",
                        "answer": "Yes! Contact360 supports over 25 languages including Spanish, French, German, and Portuguese. It automatically detects the prospect's profile language.",
                    },
                    {
                        "question": "Will I get flagged for spam?",
                        "answer": "No. Unlike other tools that blast identical templates, our AI generates unique content for every single email. This variability is key to maintaining high deliverability.",
                    },
                    {
                        "question": "Can I use my own templates?",
                        "answer": "Absolutely. You can feed the AI your best performing value propositions and case studies. It will then weave them into the personalized context of the prospect.",
                    },
                    {
                        "question": "Does it integrate with LinkedIn Sales Navigator?",
                        "answer": "Yes, our Chrome Extension overlays directly on Sales Navigator, allowing you to generate messages without switching tabs.",
                    },
                ],
            },
            "cta_section": {
                "access_control": {
                    "allowed_roles": [],
                    "restriction_type": "none"
                },
                "title": "Ready to triple your reply rate?",
                "description": "Join 10,000+ sales professionals using Contact360 to write better emails, faster. Start your 14-day free trial today.",
                "cta_text": "Start Writing for Free",
                "cta_note": "No credit card required",
            },
        },
    }
    
    # Check if page exists, update if it does
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated AI Email Writer page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded AI Email Writer page")


async def seed_email_finder_page(repo: MarketingRepository):
    """Seed Email Finder page."""
    data = {
        "page_id": "email-finder",
        "metadata": {
            "title": "Email Finder",
            "description": "Find anyone's professional email in seconds",
            "keywords": ["email", "finder", "enrichment", "contact", "verification"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Find anyone's professional email in seconds.",
            "subtitle": "Email Finder",
            "description": "Connect with decision-makers directly. Enter a First Name, Last Name, and Company Domain to reveal verified professional email addresses instantly. Our waterfall enrichment technology cross-references 15+ data sources.",
            "features": [
                "Enrich data from LinkedIn profiles",
                "Get professional email & direct dials",
                "Real-time confidence scores",
                "99% deliverability guarantee",
                "Export to CSV or sync to CRM",
            ],
            "cta_text": "Start Finding Emails",
            "cta_href": "/register",
        },
        "sections": {},
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Email Finder page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Email Finder page")


async def seed_email_verifier_page(repo: MarketingRepository):
    """Seed Email Verifier page."""
    data = {
        "page_id": "email-verifier",
        "metadata": {
            "title": "Email Verifier",
            "description": "Never bounce again with 99% deliverability",
            "keywords": ["email", "verifier", "validation", "deliverability", "bounce"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Never bounce again with 99% deliverability.",
            "subtitle": "Email Verifier",
            "description": "Protect your sender reputation. Our 7-step verification process pings SMTP servers in real-time to confirm inbox existence without sending a test email. Pay only for 'Safe to Send' results.",
            "features": [
                "Bulk verify lists of up to 100,000 emails",
                "Detect disposable & spam-trap emails",
                "Automatic replacement of invalid contacts",
                "Real-time SMTP handshake verification",
                "Protect sender reputation & domain score",
            ],
            "cta_text": "Verify Your List",
            "cta_href": "/register",
        },
        "sections": {},
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Email Verifier page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Email Verifier page")


async def seed_prospect_finder_page(repo: MarketingRepository):
    """Seed Prospect Finder page."""
    data = {
        "page_id": "prospect-finder",
        "metadata": {
            "title": "Prospect Finder",
            "description": "Build your perfect lead list",
            "keywords": ["prospect", "finder", "leads", "search", "filter"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Build your perfect lead list.",
            "subtitle": "Prospect Finder",
            "description": "Stop wasting time on LinkedIn. Use our advanced search engine to filter through 200 million verified B2B contacts. Filter by Industry, Location, and Job Title to find your perfect match.",
            "features": [
                "50+ advanced search filters",
                "Save searches and get alerted",
                "Export clean, verified data directly",
                "Filter by tech stack, revenue, headcount",
                "Real-time data updates",
            ],
            "cta_text": "Start Prospecting",
            "cta_href": "/register",
        },
        "sections": {},
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Prospect Finder page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Prospect Finder page")


async def seed_chrome_extension_page(repo: MarketingRepository):
    """Seed Chrome Extension page."""
    data = {
        "page_id": "chrome-extension",
        "metadata": {
            "title": "Chrome Extension",
            "description": "Find emails directly on LinkedIn Sales Navigator",
            "keywords": ["chrome", "extension", "linkedin", "sales navigator"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Find emails directly on LinkedIn Sales Navigator.",
            "subtitle": "Chrome Extension",
            "description": "No need to switch tabs. Our Chrome extension overlays verified contact data right where you prospect. Reveal emails, phone numbers, and sync to your CRM in one click.",
            "features": [
                "Works with LinkedIn Free, Premium & Sales Nav",
                "Real-time email verification overlay",
                "One-click export to HubSpot & Salesforce",
                "Mobile phone numbers included",
                "5-star rating on Chrome Web Store",
            ],
            "cta_text": "Add to Chrome - It's Free",
            "cta_href": "/register",
        },
        "sections": {},
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Chrome Extension page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Chrome Extension page")


async def seed_cfo_email_list_page(repo: MarketingRepository):
    """Seed CFO Email List page."""
    data = {
        "page_id": "cfo-email-list",
        "metadata": {
            "title": "CFO Email List",
            "description": "Highly targeted CFO mailing list database",
            "keywords": ["CFO", "email list", "executive", "database", "B2B"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "CFO Email List",
            "subtitle": None,
            "description": "The CFO Mailing List is a highly targeted business contact database that contains the names and emails of top level executives in companies. This list can be used for telemarketing, direct mail, email campaigns, or any other marketing campaign.",
            "features": [],
            "cta_text": "ACCESS NOW",
            "cta_href": "/register",
        },
        "hero_stats": [
            {"value": "160+", "label": "Countries Covered"},
            {"value": "100%", "label": "Verified Database"},
            {"value": "17+Years", "label": "Industry Expertise"},
            {"value": "95%", "label": "Delivery Guaranteed"},
        ],
        "hero_table": {
            "national": {"total_counts": 223919, "email_counts": 199039},
            "international": {"total_counts": 92164, "email_counts": 51842},
        },
        "sections": {
            "cfo_segmentation": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "upgrade_message": "Upgrade to Pro to access advanced segmentation features"
                },
                "title": "Segment Your CFO List for Maximum ROI",
                "description": "A generic list fails. Our platform allows you to slice and dice our CFO database using 50+ unique data points to ensure your message hits home.",
                "cards": [
                    {
                        "title": "Company Revenue",
                        "description": "Target CFOs managing budgets from $10M to $10B+ with precision revenue filters.",
                        "icon": "Building2",
                    },
                    {
                        "title": "Geography",
                        "description": "Access verified financial leaders across US, EMEA, APAC, and 190+ countries.",
                        "icon": "Globe",
                    },
                    {
                        "title": "Industry Focus",
                        "description": "Filter by SaaS, Manufacturing, Healthcare, FinTech, and 140+ specific verticals.",
                        "icon": "Target",
                    },
                    {
                        "title": "Company Size",
                        "description": "Reach CFOs at Fortune 500 enterprises or high-growth Series A startups.",
                        "icon": "PieChart",
                    },
                ],
            },
            "cfo_benefits": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "Why target the Chief Financial Officer?",
                "description": "CFOs are the ultimate gatekeepers of corporate spend. Engaging them early with high-quality data is the fastest way to accelerate your enterprise sales cycle.",
                "benefits": [
                    {
                        "title": "Decision Making Power",
                        "description": "92% of CFOs have the final sign-off on technology and service investments.",
                    },
                    {
                        "title": "Direct Dial Availability",
                        "description": "Our list includes 85% mobile phone coverage for high-priority CFO contacts.",
                    },
                    {
                        "title": "Verified Monthly",
                        "description": "Every CFO record is double-verified every 30 days to prevent data decay.",
                    },
                ],
                "stats": {
                    "total_profiles": "2,482,091",
                    "total_label": "Verified CFO Profiles Available",
                    "accuracy_rate": "99%",
                    "accuracy_label": "Accuracy Rate",
                    "fortune_leaders": "850k+",
                    "fortune_label": "Fortune 1000 Leaders",
                },
            },
            "cfo_testimonials": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "partial",
                    "upgrade_message": "Upgrade to Pro to see verified customer testimonials"
                },
                "testimonials": [
                    {
                        "quote": "Their CFO list was the only one that didn't bounce. We saw a 14% response rate from Fortune 500 finance heads.",
                        "author": "James Miller",
                        "role": "VP Sales, CloudPay",
                    },
                    {
                        "quote": "Targeting CFOs by revenue size changed our outbound game. Contact360's data is unmatched in the industry.",
                        "author": "Elena Rossi",
                        "role": "Growth Director, FinTechX",
                    },
                    {
                        "quote": "Accurate direct dials for CFOs are usually a myth. Contact360 made it a reality for our team.",
                        "author": "David Kwong",
                        "role": "Sales Ops, Stripe",
                    },
                ],
            },
            "cfo_data_quality": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "upgrade_message": "Upgrade to Pro to see detailed data quality metrics"
                },
                "title": "Unmatched CFO Data Quality",
                "description": "The most comprehensive financial leader database in the industry.",
                "cards": [
                    {
                        "title": "Avoid Spam Traps & Bounces",
                        "description": "Standard CFO lists are filled with old data. Because financial leadership turns over every 4.8 years on average, we verify our CFO list every 30 days. We remove retired executives and catch-all addresses that hurt your sender reputation.",
                        "footer_text": "Never buy a generic, stale CFO database again.",
                        "type": "warning",
                        "icon": "ShieldAlert",
                    },
                    {
                        "title": "Proprietary Enrichment",
                        "description": "We don't just give you an email. Every CFO contact comes enriched with their company's tech stack, recent funding news, and departmental headcount growth. This allows your sales team to open conversations with relevant financial insights.",
                        "footer_text": "Data enriched with 50+ unique firmographic signals.",
                        "type": "success",
                        "icon": "PieChart",
                    },
                ],
            },
            "cfo_faq": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none"
                },
                "title": "CFO Email List FAQs",
                "subtitle": "Everything you need to know about our executive data sourcing.",
                "faqs": [
                    {
                        "question": "How accurate is the CFO Email List?",
                        "answer": "We guarantee a 95% deliverability rate on all our CFO records. Our database is double-verified through automated SMTP handshakes and manual research every 30 days to ensure you never waste credits on bounces.",
                    },
                    {
                        "question": "What details are included in each CFO contact?",
                        "answer": "Each record typically includes the full name, direct professional email, verified mobile or direct desk phone number, LinkedIn profile URL, company revenue, employee size, and primary industry.",
                    },
                    {
                        "question": "Is the data GDPR and CCPA compliant?",
                        "answer": "Yes. Contact360 sources data exclusively from public records and legitimate business registries. We adhere to all international data privacy laws, ensuring your outreach remains safe and compliant.",
                    },
                    {
                        "question": "Can I filter the CFO list by specific company revenue?",
                        "answer": "Absolutely. Our advanced segmentation tools allow you to target CFOs based on 50+ data points, including company annual revenue (from $1M to $10B+), recent funding rounds, and current technology stack.",
                    },
                    {
                        "question": "Do you offer sample data for the CFO list?",
                        "answer": "Yes! You can sign up and access 50 free verified leads to test the accuracy of our data. No credit card is required to start your trial.",
                    },
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated CFO Email List page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded CFO Email List page")


async def seed_about_page(repo: MarketingRepository):
    """Seed About page."""
    data = {
        "page_id": "about",
        "metadata": {
            "title": "About Contact360",
            "description": "We're on a mission to democratize B2B data accuracy.",
            "keywords": ["about", "company", "mission", "B2B", "data"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "About Contact360",
            "subtitle": "We're on a mission to democratize B2B data accuracy.",
            "description": "Contact360 is dedicated to providing accurate, verified B2B contact data to help businesses grow.",
            "features": [],
            "cta_text": "Join Our Journey",
            "cta_href": "/register",
        },
        "sections": {
            "about_values": {
                "title": "Our Values",
                "cards": [
                    {
                        "icon": "Shield",
                        "title": "Data Integrity",
                        "description": "We never scrape LinkedIn. Our data is ethically sourced and double-verified.",
                    },
                    {
                        "icon": "Zap",
                        "title": "Real-time Verification",
                        "description": "Our SMTP handshake protocol ensures 99% deliverability rates.",
                    },
                    {
                        "icon": "Users",
                        "title": "Customer First",
                        "description": "We build tools that empower growth teams, not just databases.",
                    },
                ],
            },
            "about_story": {
                "title": "Our Story",
                "description": "Founded in 2024, Contact360 started with a simple observation: B2B data was too expensive and too inaccurate. We built a proprietary engine that verifies data in real-time, ensuring you only pay for contacts that actually exist.",
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated About page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded About page")


async def seed_careers_page(repo: MarketingRepository):
    """Seed Careers page."""
    data = {
        "page_id": "careers",
        "metadata": {
            "title": "Join the Team",
            "description": "Help us build the future of B2B intelligence.",
            "keywords": ["careers", "jobs", "hiring", "team", "opportunities"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Join the Team",
            "subtitle": "Help us build the future of B2B intelligence.",
            "description": "We're looking for talented individuals to join our mission of democratizing B2B data accuracy.",
            "features": [],
            "cta_text": "View Open Positions",
            "cta_href": "/register",
        },
        "sections": {
            "careers_jobs": {
                "title": "Open Positions",
                "jobs": [
                    {
                        "role": "Senior Frontend Engineer",
                        "department": "Engineering",
                        "location": "Remote",
                        "type": "Full-time",
                    },
                    {
                        "role": "Product Designer",
                        "department": "Design",
                        "location": "New York, NY",
                        "type": "Full-time",
                    },
                    {
                        "role": "Growth Marketer",
                        "department": "Marketing",
                        "location": "London, UK",
                        "type": "Full-time",
                    },
                    {
                        "role": "Data Scientist",
                        "department": "Data",
                        "location": "Remote",
                        "type": "Full-time",
                    },
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Careers page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Careers page")


async def seed_api_docs_page(repo: MarketingRepository):
    """Seed API Docs page."""
    data = {
        "page_id": "api-docs",
        "metadata": {
            "title": "Contact360 API",
            "description": "Integrate our verified data directly into your application.",
            "keywords": ["API", "documentation", "integration", "developer", "REST"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Contact360 API",
            "subtitle": "Integrate our verified data directly into your application.",
            "description": "Powerful REST API for accessing verified B2B contact data with sub-200ms response times.",
            "features": [
                "Sub-200ms response times",
                "Bulk endpoints for up to 100k records",
                "RESTful design",
                "Comprehensive documentation",
            ],
            "cta_text": "Read Documentation",
            "cta_href": "/register",
        },
        "sections": {
            "api_example": {
                "title": "Quick Start",
                "code": """curl -X POST https://api.contact360.com/v1/enrich \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "sarah.connor@skynet.com"
  }'""",
            },
            "api_features": {
                "title": "API Features",
                "features": [
                    {
                        "icon": "Zap",
                        "title": "Blazing Fast",
                        "description": "Sub-200ms response times for real-time enrichment.",
                    },
                    {
                        "icon": "Database",
                        "title": "Bulk Endpoints",
                        "description": "Process up to 100k records in a single batch request.",
                    },
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated API Docs page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded API Docs page")


async def seed_integrations_page(repo: MarketingRepository):
    """Seed Integrations page."""
    data = {
        "page_id": "integrations",
        "metadata": {
            "title": "Integrations",
            "description": "Connect Contact360 with your favorite tools.",
            "keywords": ["integrations", "CRM", "salesforce", "hubspot", "tools"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Integrations",
            "subtitle": "Connect Contact360 with your favorite tools.",
            "description": "Seamlessly integrate Contact360 with your existing workflow and tools.",
            "features": [],
            "cta_text": "Get Started",
            "cta_href": "/register",
        },
        "sections": {
            "integrations_list": {
                "title": "Available Integrations",
                "integrations": [
                    "Salesforce",
                    "HubSpot",
                    "Pipedrive",
                    "Zapier",
                    "Slack",
                    "Gmail",
                    "Outlook",
                    "Outreach",
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Integrations page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Integrations page")


async def seed_privacy_page(repo: MarketingRepository):
    """Seed Privacy Policy page."""
    data = {
        "page_id": "privacy",
        "metadata": {
            "title": "Privacy Policy",
            "description": "Our commitment to protecting your privacy and data.",
            "keywords": ["privacy", "policy", "data protection", "GDPR", "CCPA"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Privacy Policy",
            "subtitle": f"Last updated: {datetime.utcnow().strftime('%B %d, %Y')}",
            "description": "This is a placeholder for the Privacy Policy. In a real application, this section would contain detailed legal definitions, user rights, data processing agreements, and compliance information regarding GDPR, CCPA, and other relevant regulations.",
            "features": [],
            "cta_text": None,
            "cta_href": None,
        },
        "sections": {
            "privacy_content": {
                "sections": [
                    {
                        "title": "1. Introduction",
                        "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                    },
                    {
                        "title": "2. Data Usage",
                        "content": "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                    },
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Privacy Policy page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Privacy Policy page")


async def seed_terms_page(repo: MarketingRepository):
    """Seed Terms of Service page."""
    data = {
        "page_id": "terms",
        "metadata": {
            "title": "Terms of Service",
            "description": "Terms and conditions for using Contact360 services.",
            "keywords": ["terms", "service", "conditions", "legal", "agreement"],
            "last_updated": datetime.utcnow(),
            "status": "published",
            "version": 1,
        },
        "hero": {
            "title": "Terms of Service",
            "subtitle": f"Last updated: {datetime.utcnow().strftime('%B %d, %Y')}",
            "description": "This is a placeholder for the Terms of Service. In a real application, this section would contain detailed legal definitions, user rights, data processing agreements, and compliance information regarding GDPR, CCPA, and other relevant regulations.",
            "features": [],
            "cta_text": None,
            "cta_href": None,
        },
        "sections": {
            "terms_content": {
                "sections": [
                    {
                        "title": "1. Introduction",
                        "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                    },
                    {
                        "title": "2. Data Usage",
                        "content": "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                    },
                ],
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"], include_deleted=True)
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Terms of Service page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Terms of Service page")


async def main():
    """Main seed function."""
    import sys
    print("Starting marketing data seed...", flush=True)
    sys.stdout.flush()
    
    try:
        repo = MarketingRepository()
        print("Repository initialized", flush=True)
        
        # Seed product pages
        print("\nSeeding product pages...", flush=True)
        await seed_ai_writer_page(repo)
        await seed_email_finder_page(repo)
        await seed_email_verifier_page(repo)
        await seed_prospect_finder_page(repo)
        await seed_chrome_extension_page(repo)
        await seed_cfo_email_list_page(repo)
        
        # Seed general pages
        print("\nSeeding general pages...", flush=True)
        await seed_about_page(repo)
        await seed_careers_page(repo)
        await seed_api_docs_page(repo)
        await seed_integrations_page(repo)
        await seed_privacy_page(repo)
        await seed_terms_page(repo)
        
        print("\n✓ All marketing pages seeded successfully!", flush=True)
        
    except Exception as e:
        import traceback
        print(f"\n✗ Error seeding data: {e}", flush=True)
        traceback.print_exc()
        raise
    finally:
        await close_mongodb_connection()
        print("MongoDB connection closed", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

