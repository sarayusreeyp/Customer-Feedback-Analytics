"""
models.py — SQLAlchemy schema definitions for SQLite database.

Core entities:
  - customers, products, channels, surveys, themes
  - reviews, survey_responses, support_tickets, support_messages
  - action_items

Bridge tables:
  - review_themes, response_themes, message_themes
"""

from sqlalchemy import (
    MetaData, Table, Column, String, Integer, Float, Boolean,
    ForeignKey, Index
)

metadata = MetaData()

# ── Master Tables ─────────────────────────────────────────────────────────────

customers = Table(
    "customers",
    metadata,
    Column("customer_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("region", String, nullable=False),
    Column("segment", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("lifecycle_state", String, nullable=False),
)

products = Table(
    "products",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("category", String, nullable=False),
)

channels = Table(
    "channels",
    metadata,
    Column("channel_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
)

themes = Table(
    "themes",
    metadata,
    Column("theme_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", String, nullable=True),
)

sentiment_labels = Table(
    "sentiment_labels",
    metadata,
    Column("sentiment_id", String, primary_key=True),
    Column("sentiment_label", String, nullable=False, unique=True),
    Column("polarity", Integer, nullable=False),
    Column("description", String, nullable=True),
)

surveys = Table(
    "surveys",
    metadata,
    Column("survey_id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("survey_type", String, nullable=False),
    Column("product_id", String, ForeignKey("products.product_id"), nullable=False),
    Column("channel_id", String, ForeignKey("channels.channel_id"), nullable=False),
    Column("start_date", String, nullable=False),
    Column("end_date", String, nullable=False),
    Column("lifecycle_state", String, nullable=False),
)

# ── Transaction / Event Tables ────────────────────────────────────────────────

reviews = Table(
    "reviews",
    metadata,
    Column("review_id", String, primary_key=True),
    Column("customer_id", String, ForeignKey("customers.customer_id"), nullable=False),
    Column("product_id", String, ForeignKey("products.product_id"), nullable=False),
    Column("channel_id", String, ForeignKey("channels.channel_id"), nullable=False),
    Column("review_text", String, nullable=False),
    Column("star_rating", Integer, nullable=False),
    Column("sentiment_label", String, nullable=False),
    Column("language", String, nullable=False),
    Column("reviewed_at", String, nullable=False),
    Column("is_ambiguous", Boolean, nullable=False, default=False),
    # Columns populated during downstream Processing (Module 4)
    Column("predicted_sentiment", String, nullable=True),
    Column("predicted_theme", String, nullable=True),
    Index("idx_reviews_prod_date", "product_id", "reviewed_at"),
    Index("idx_reviews_customer", "customer_id"),
    Index("idx_reviews_channel", "channel_id"),
)

survey_responses = Table(
    "survey_responses",
    metadata,
    Column("response_id", String, primary_key=True),
    Column("survey_id", String, ForeignKey("surveys.survey_id"), nullable=False),
    Column("customer_id", String, ForeignKey("customers.customer_id"), nullable=False),
    Column("response_text", String, nullable=False),
    Column("rating", Integer, nullable=False),
    Column("sentiment_label", String, nullable=False),
    Column("language", String, nullable=False),
    Column("submitted_at", String, nullable=False),
    Column("is_ambiguous", Boolean, nullable=False, default=False),
    # Downstream predicted columns
    Column("predicted_sentiment", String, nullable=True),
    Column("predicted_theme", String, nullable=True),
    Index("idx_responses_survey_date", "survey_id", "submitted_at"),
    Index("idx_responses_customer", "customer_id"),
)

support_tickets = Table(
    "support_tickets",
    metadata,
    Column("ticket_id", String, primary_key=True),
    Column("customer_id", String, ForeignKey("customers.customer_id"), nullable=False),
    Column("channel_id", String, ForeignKey("channels.channel_id"), nullable=False),
    Column("product_id", String, ForeignKey("products.product_id"), nullable=True),
    Column("subject", String, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("resolved_at", String, nullable=True),
    Index("idx_tickets_customer", "customer_id"),
    Index("idx_tickets_product", "product_id"),
)

support_messages = Table(
    "support_messages",
    metadata,
    Column("message_id", String, primary_key=True),
    Column("ticket_id", String, ForeignKey("support_tickets.ticket_id"), nullable=False),
    Column("sender_type", String, nullable=False),
    Column("message_text", String, nullable=False),
    Column("sentiment_label", String, nullable=False),
    Column("language", String, nullable=False),
    Column("sent_at", String, nullable=False),
    Column("is_ambiguous", Boolean, nullable=False, default=False),
    # Downstream predicted columns
    Column("predicted_sentiment", String, nullable=True),
    Column("predicted_theme", String, nullable=True),
    Index("idx_messages_ticket_date", "ticket_id", "sent_at"),
)

action_items = Table(
    "action_items",
    metadata,
    Column("action_id", String, primary_key=True),
    Column("theme_id", String, ForeignKey("themes.theme_id"), nullable=False),
    Column("title", String, nullable=False),
    Column("priority", String, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("mention_count", Integer, nullable=False),
    Index("idx_action_items_theme", "theme_id"),
)

# ── Event / State History Table ───────────────────────────────────────────────

status_history = Table(
    "status_history",
    metadata,
    Column("history_id", String, primary_key=True),
    Column("entity_type", String, nullable=False),  # e.g., 'support_ticket', 'customer', 'survey', 'action_item'
    Column("entity_id", String, nullable=False),
    Column("old_status", String, nullable=True),
    Column("new_status", String, nullable=False),
    Column("changed_at", String, nullable=False),
    Column("changed_by", String, nullable=False),
    Index("idx_history_entity", "entity_type", "entity_id"),
)

# ── Bridge Tables (N:M Relationships) ─────────────────────────────────────────

review_themes = Table(
    "review_themes",
    metadata,
    Column("review_id", String, ForeignKey("reviews.review_id"), primary_key=True),
    Column("theme_id", String, ForeignKey("themes.theme_id"), primary_key=True),
    Index("idx_review_themes_theme", "theme_id"),
)

response_themes = Table(
    "response_themes",
    metadata,
    Column("response_id", String, ForeignKey("survey_responses.response_id"), primary_key=True),
    Column("theme_id", String, ForeignKey("themes.theme_id"), primary_key=True),
    Index("idx_response_themes_theme", "theme_id"),
)

message_themes = Table(
    "message_themes",
    metadata,
    Column("message_id", String, ForeignKey("support_messages.message_id"), primary_key=True),
    Column("theme_id", String, ForeignKey("themes.theme_id"), primary_key=True),
    Index("idx_message_themes_theme", "theme_id"),
)
