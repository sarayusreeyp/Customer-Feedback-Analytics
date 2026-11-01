"""
schema.py — Data dictionary and taxonomy definitions.

Single source of truth for:
  - Fixed master data (Products, Channels, Themes)
  - Allowed enum values used across all modules
  - Field-level specs for validation (type, required, uniqueness, allowed values)

No imports from other cfa modules — safe to import anywhere.
"""

# ── Fixed master data ─────────────────────────────────────────────────────────

PRODUCTS = [
    {"product_id": f"PROD-{i+1:03d}", "name": name, "category": cat}
    for i, (name, cat) in enumerate([
        ("SmartHome Hub",              "Smart Home"),
        ("Wireless Earbuds Pro",       "Audio"),
        ("4K Streaming Stick",         "Entertainment"),
        ("Portable Charger 20K",       "Accessories"),
        ("Noise-Cancelling Headphones","Audio"),
        ("Smart Doorbell Camera",      "Security"),
        ("Robot Vacuum V2",            "Home Appliances"),
        ("Air Purifier Slim",          "Home Appliances"),
        ("Smartwatch Series 5",        "Wearables"),
        ("Fitness Tracker Band",       "Wearables"),
        ("Laptop Stand Pro",           "Accessories"),
        ("Mechanical Keyboard TKL",    "Computing"),
        ("Ergonomic Mouse",            "Computing"),
        ("USB-C Hub 7-in-1",           "Accessories"),
        ("Smart LED Bulb Pack",        "Smart Home"),
        ("Mini Projector Pocket",      "Entertainment"),
        ("Bluetooth Speaker Max",      "Audio"),
        ("Webcam 4K Auto-Focus",       "Computing"),
        ("Smart Scale Wi-Fi",          "Health"),
        ("Electric Toothbrush Elite",  "Health"),
    ])
]

CHANNELS = [
    {"channel_id": "CHAN-001", "name": "Website",       "type": "digital"},
    {"channel_id": "CHAN-002", "name": "Mobile App",    "type": "digital"},
    {"channel_id": "CHAN-003", "name": "Email",         "type": "digital"},
    {"channel_id": "CHAN-004", "name": "Phone",         "type": "voice"},
    {"channel_id": "CHAN-005", "name": "In-Store",      "type": "physical"},
    {"channel_id": "CHAN-006", "name": "Social Media",  "type": "digital"},
]

SENTIMENT_LABELS_MASTER = [
    {"sentiment_id": "SENT-01", "sentiment_label": "positive", "polarity": 1,  "description": "Favorable user experience, praise or satisfaction"},
    {"sentiment_id": "SENT-02", "sentiment_label": "neutral",  "polarity": 0,  "description": "Factual feedback, balanced experience or inquiries"},
    {"sentiment_id": "SENT-03", "sentiment_label": "negative", "polarity": -1, "description": "Critical feedback, bug reports, dissatisfaction or complaints"},
]

THEMES = [
    {"theme_id": f"THEME-{i+1:06d}", "name": name, "description": desc}
    for i, (name, desc) in enumerate([
        ("Product Quality",        "Feedback on build, durability, and materials"),
        ("Customer Service",       "Interactions with support staff"),
        ("Pricing & Value",        "Perceived value for money"),
        ("Delivery & Shipping",    "Speed, accuracy, and condition of delivery"),
        ("Website & App UX",       "Usability of digital platforms"),
        ("Return & Refund Policy", "Ease and fairness of returns/refunds"),
        ("Product Availability",   "Stock levels and availability"),
        ("Technical Support",      "Help with technical issues"),
        ("Account & Billing",      "Account management and billing accuracy"),
        ("Communication & Updates","Proactive communication and status updates"),
        ("Packaging",              "Quality and sustainability of packaging"),
        ("Installation & Setup",   "Ease of first-time product setup"),
        ("Performance & Reliability","Product performance and uptime"),
        ("Feature Requests",       "Suggestions for new features"),
        ("Onboarding Experience",  "First-time user guidance"),
    ])
]

# Sampling weights for primary-theme assignment (must sum to 1.0)
THEME_WEIGHTS = [
    0.13,  # Product Quality        — most common feedback topic
    0.13,  # Customer Service
    0.10,  # Pricing & Value
    0.09,  # Delivery & Shipping
    0.08,  # Website & App UX
    0.06,  # Return & Refund Policy
    0.06,  # Product Availability
    0.07,  # Technical Support
    0.05,  # Account & Billing
    0.05,  # Communication & Updates
    0.04,  # Packaging
    0.04,  # Installation & Setup
    0.05,  # Performance & Reliability
    0.03,  # Feature Requests
    0.02,  # Onboarding Experience
]
assert abs(sum(THEME_WEIGHTS) - 1.0) < 1e-9, "THEME_WEIGHTS must sum to 1.0"


# ── Allowed enum values ───────────────────────────────────────────────────────

SENTIMENT_LABELS   = ["positive", "neutral", "negative"]
LANGUAGES          = ["en", "es", "fr", "de"]

LANGUAGE_DISTRIBUTION = {
    "en": 0.95,
    "es": 0.017,
    "fr": 0.017,
    "de": 0.016,
}
SURVEY_TYPES       = ["NPS", "CSAT", "CES", "Product Feedback", "Post-Purchase"]
TICKET_STATUSES    = ["open", "in_progress", "resolved", "closed"]
LIFECYCLE_STATES   = ["draft", "active", "closed", "archived"]
SENDER_TYPES       = ["customer", "agent"]
REGIONS            = ["North", "South", "East", "West", "International"]
SEGMENTS           = ["B2C", "B2B", "Enterprise"]
ACTION_PRIORITIES  = ["high", "medium", "low"]
ACTION_STATUSES    = ["open", "in_progress", "done"]
CHANNEL_TYPES      = ["digital", "voice", "physical"]

ANOMALY_TYPES = [
    "label_contradiction",    # sentiment label opposes the text tone
    "duplicate_response",     # exact copy of another row's text + customer_id
    "pii_leak",               # real-looking name/email embedded in text
    "out_of_taxonomy_theme",  # theme_id not in the 15-item taxonomy
    "test_label_in_input",    # literal "TEST" marker present in a field
]

# Weighted sampling distributions for master data
REGION_WEIGHTS  = [0.25, 0.20, 0.25, 0.20, 0.10]   # aligned with REGIONS
SEGMENT_WEIGHTS = [0.70, 0.20, 0.10]                 # aligned with SEGMENTS

# Lifecycle weights for customers (most are active)
CUSTOMER_LIFECYCLE_WEIGHTS = {
    "draft":    0.02,
    "active":   0.90,
    "closed":   0.05,
    "archived": 0.03,
}

# Rating → sentiment mapping rules (authoritative, used in validation too)
STAR_TO_SENTIMENT = {1: "negative", 2: "negative", 3: "neutral",
                     4: "positive", 5: "positive"}    # review star (1-5)

def response_rating_to_sentiment(rating: int) -> str:
    """Map a 1-10 survey response rating to a sentiment label."""
    if rating >= 8:
        return "positive"
    if rating >= 5:
        return "neutral"
    return "negative"


# ── Field specifications (used by validation/enum_checks.py) ─────────────────

FIELD_SPECS: dict = {
    "Customer": {
        "customer_id":     {"type": "str",  "required": True,  "unique": True,  "pattern": r"CUST-\d{4}-\d{6}"},
        "name":            {"type": "str",  "required": True,  "unique": False},
        "email":           {"type": "str",  "required": True,  "unique": True},
        "region":          {"type": "str",  "required": True,  "allowed": REGIONS},
        "segment":         {"type": "str",  "required": True,  "allowed": SEGMENTS},
        "created_at":      {"type": "date", "required": True},
        "lifecycle_state": {"type": "str",  "required": True,  "allowed": LIFECYCLE_STATES},
    },
    "Product": {
        "product_id": {"type": "str", "required": True, "unique": True, "pattern": r"PROD-\d{3}"},
        "name":       {"type": "str", "required": True},
        "category":   {"type": "str", "required": True},
    },
    "Channel": {
        "channel_id": {"type": "str", "required": True, "unique": True, "pattern": r"CHAN-\d{3}"},
        "name":       {"type": "str", "required": True},
        "type":       {"type": "str", "required": True, "allowed": CHANNEL_TYPES},
    },
    "Survey": {
        "survey_id":       {"type": "str",  "required": True, "unique": True, "pattern": r"SUR-\d{4}-\d{6}"},
        "title":           {"type": "str",  "required": True},
        "survey_type":     {"type": "str",  "required": True, "allowed": SURVEY_TYPES},
        "product_id":      {"type": "str",  "required": True},
        "channel_id":      {"type": "str",  "required": True},
        "start_date":      {"type": "date", "required": True},
        "end_date":        {"type": "date", "required": True},
        "lifecycle_state": {"type": "str",  "required": True, "allowed": LIFECYCLE_STATES},
    },
    "SurveyResponse": {
        "response_id":    {"type": "str",      "required": True,  "unique": True},
        "survey_id":      {"type": "str",      "required": True},
        "customer_id":    {"type": "str",      "required": True},
        "response_text":  {"type": "str",      "required": True},
        "rating":         {"type": "int",      "required": True,  "min": 1, "max": 10},
        "sentiment_label":{"type": "str",      "required": True,  "allowed": SENTIMENT_LABELS},
        "language":       {"type": "str",      "required": True,  "allowed": LANGUAGES},
        "submitted_at":   {"type": "datetime", "required": True},
        "is_ambiguous":   {"type": "bool",     "required": True},
    },
    "Review": {
        "review_id":      {"type": "str",      "required": True,  "unique": True, "pattern": r"REV-\d{4}-\d{6}"},
        "customer_id":    {"type": "str",      "required": True},
        "product_id":     {"type": "str",      "required": True},
        "channel_id":     {"type": "str",      "required": True},
        "review_text":    {"type": "str",      "required": True},
        "star_rating":    {"type": "int",      "required": True,  "min": 1, "max": 5},
        "sentiment_label":{"type": "str",      "required": True,  "allowed": SENTIMENT_LABELS},
        "language":       {"type": "str",      "required": True,  "allowed": LANGUAGES},
        "reviewed_at":    {"type": "datetime", "required": True},
        "is_ambiguous":   {"type": "bool",     "required": True},
    },
    "SupportTicket": {
        "ticket_id":   {"type": "str",      "required": True,  "unique": True, "pattern": r"TKT-\d{4}-\d{6}"},
        "customer_id": {"type": "str",      "required": True},
        "channel_id":  {"type": "str",      "required": True},
        "subject":     {"type": "str",      "required": True},
        "status":      {"type": "str",      "required": True,  "allowed": TICKET_STATUSES},
        "created_at":  {"type": "datetime", "required": True},
        "resolved_at": {"type": "datetime", "required": False},
    },
    "SupportMessage": {
        "message_id":    {"type": "str",      "required": True,  "unique": True},
        "ticket_id":     {"type": "str",      "required": True},
        "sender_type":   {"type": "str",      "required": True,  "allowed": SENDER_TYPES},
        "message_text":  {"type": "str",      "required": True},
        "sentiment_label":{"type": "str",     "required": True,  "allowed": SENTIMENT_LABELS},
        "language":      {"type": "str",      "required": True,  "allowed": LANGUAGES},
        "sent_at":       {"type": "datetime", "required": True},
        "is_ambiguous":  {"type": "bool",     "required": True},
    },
    "Theme": {
        "theme_id":    {"type": "str", "required": True, "unique": True, "pattern": r"THEME-\d{6}"},
        "name":        {"type": "str", "required": True},
        "description": {"type": "str", "required": False},
    },
    "SentimentLabel": {
        "sentiment_id":    {"type": "str", "required": True, "unique": True, "pattern": r"SENT-\d{2}"},
        "sentiment_label": {"type": "str", "required": True, "unique": True, "allowed": SENTIMENT_LABELS},
        "polarity":        {"type": "int", "required": True, "allowed": [-1, 0, 1]},
        "description":     {"type": "str", "required": False},
    },
    "ActionItem": {
        "action_id":    {"type": "str",  "required": True, "unique": True, "pattern": r"ACT-\d{4}-\d{6}"},
        "theme_id":     {"type": "str",  "required": True},
        "title":        {"type": "str",  "required": True},
        "priority":     {"type": "str",  "required": True, "allowed": ACTION_PRIORITIES},
        "status":       {"type": "str",  "required": True, "allowed": ACTION_STATUSES},
        "created_at":   {"type": "date", "required": True},
        "mention_count":{"type": "int",  "required": True, "min": 0},
    },
}
