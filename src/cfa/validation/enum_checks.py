"""
enum_checks.py — Allowed values and schema conformance checks.

Validates that:
  - All categorical columns match the definitions in cfa.generators.schema.FIELD_SPECS.
  - Derived ratings and sentiment labels are mathematically and rule-consistent:
      star_rating (1-2 -> negative, 3 -> neutral, 4-5 -> positive)
      survey response rating (1-4 -> negative, 5-7 -> neutral, 8-10 -> positive)
"""

from __future__ import annotations

import re
import pandas as pd
from sqlalchemy import text
from cfa.generators.schema import (
    FIELD_SPECS, STAR_TO_SENTIMENT, response_rating_to_sentiment
)

_TABLE_NAME_MAP = {
    "Customer": "customers",
    "Product": "products",
    "Channel": "channels",
    "Survey": "surveys",
    "SurveyResponse": "survey_responses",
    "Review": "reviews",
    "SupportTicket": "support_tickets",
    "SupportMessage": "support_messages",
    "Theme": "themes",
    "SentimentLabel": "sentiment_labels",
    "ActionItem": "action_items",
}


def check_allowed_enums(engine) -> list[dict]:
    """
    Check all categorical columns with 'allowed' values defined in FIELD_SPECS.
    Returns a list of violation dicts (empty if all pass).
    """
    violations = []

    with engine.connect() as conn:
        for entity_name, spec in FIELD_SPECS.items():
            table_name = _TABLE_NAME_MAP.get(entity_name, entity_name.lower())

            for col_name, rules in spec.items():
                allowed = rules.get("allowed")
                if not allowed:
                    continue

                allowed_quoted = ", ".join(f"'{v}'" for v in allowed)
                query = f"""
                    SELECT DISTINCT "{col_name}" as invalid_val
                    FROM "{table_name}"
                    WHERE "{col_name}" NOT IN ({allowed_quoted})
                      AND "{col_name}" IS NOT NULL
                """
                invalids = conn.execute(text(query)).fetchall()
                if invalids:
                    violations.append({
                        "table": table_name,
                        "column": col_name,
                        "allowed_values": allowed,
                        "found_invalid_values": [row[0] for row in invalids],
                    })

                # Check pattern / regex if specified
                pattern = rules.get("pattern")
                if pattern:
                    df = pd.read_sql(text(f'SELECT "{col_name}" FROM "{table_name}"'), conn)
                    non_matching = df[~df[col_name].astype(str).str.match(pattern)]
                    if not non_matching.empty:
                        violations.append({
                            "table": table_name,
                            "column": col_name,
                            "pattern": pattern,
                            "non_matching_count": len(non_matching),
                            "sample": non_matching[col_name].head(3).tolist(),
                        })

    return violations


def check_derived_rules_reconciliation(engine) -> list[dict]:
    """
    Verify that derived sentiment labels match their numerical source ratings,
    and arithmetically reconcile ActionItem mention_counts against actual occurrences.
    For clean raw data:
      - Reviews: 1-2 => negative, 3 => neutral, 4-5 => positive
      - SurveyResponses: 1-4 => negative, 5-7 => neutral, 8-10 => positive
      - ActionItem.mention_count matches total mentions across review_themes, response_themes, message_themes
    """
    violations = []

    with engine.connect() as conn:
        # Check reviews
        query_rev = """
            SELECT review_id, star_rating, sentiment_label
            FROM reviews
            WHERE (star_rating IN (1, 2) AND sentiment_label != 'negative')
               OR (star_rating = 3 AND sentiment_label != 'neutral')
               OR (star_rating IN (4, 5) AND sentiment_label != 'positive')
        """
        rev_mismatches = conn.execute(text(query_rev)).fetchall()
        if rev_mismatches:
            violations.append({
                "table": "reviews",
                "rule": "star_rating to sentiment_label derivation",
                "mismatch_count": len(rev_mismatches),
                "samples": [dict(r._mapping) for r in rev_mismatches[:5]],
            })

        # Check survey responses
        query_resp = """
            SELECT response_id, rating, sentiment_label
            FROM survey_responses
            WHERE (rating <= 4 AND sentiment_label != 'negative')
               OR (rating >= 5 AND rating <= 7 AND sentiment_label != 'neutral')
               OR (rating >= 8 AND sentiment_label != 'positive')
        """
        resp_mismatches = conn.execute(text(query_resp)).fetchall()
        if resp_mismatches:
            violations.append({
                "table": "survey_responses",
                "rule": "rating (1-10) to sentiment_label derivation",
                "mismatch_count": len(resp_mismatches),
                "samples": [dict(r._mapping) for r in resp_mismatches[:5]],
            })

        # Arithmetic reconciliation: ActionItem mention counts vs bridge theme counts
        query_actions = """
            SELECT a.action_id, a.theme_id, a.mention_count as recorded_count,
                   COALESCE(counts.total_mentions, 0) as actual_count
            FROM action_items a
            LEFT JOIN (
                SELECT theme_id, COUNT(*) as total_mentions FROM (
                    SELECT theme_id FROM review_themes
                    UNION ALL
                    SELECT theme_id FROM response_themes
                    UNION ALL
                    SELECT theme_id FROM message_themes
                )
                GROUP BY theme_id
            ) counts ON a.theme_id = counts.theme_id
            WHERE a.mention_count != COALESCE(counts.total_mentions, 0)
        """
        action_mismatches = conn.execute(text(query_actions)).fetchall()
        if action_mismatches:
            violations.append({
                "table": "action_items",
                "rule": "arithmetic reconciliation of mention_count against theme bridge records",
                "mismatch_count": len(action_mismatches),
                "samples": [dict(r._mapping) for r in action_mismatches[:5]],
            })

    return violations


def check_date_ordering(engine) -> list[dict]:
    """
    Check temporal ordering and consistency:
      - surveys: end_date >= start_date
      - support_tickets: resolved_at >= created_at (when resolved_at is present)
      - survey_responses: submitted_at is within survey start_date and end_date
      - support_messages: sent_at >= support_tickets.created_at
    """
    violations = []
    with engine.connect() as conn:
        # Survey start/end date ordering
        q_surveys = """
            SELECT survey_id, start_date, end_date
            FROM surveys
            WHERE end_date < start_date
        """
        bad_surveys = conn.execute(text(q_surveys)).fetchall()
        if bad_surveys:
            violations.append({
                "table": "surveys",
                "rule": "end_date >= start_date",
                "violation_count": len(bad_surveys),
                "samples": [dict(r._mapping) for r in bad_surveys[:5]],
            })

        # Support ticket resolution ordering
        q_tickets = """
            SELECT ticket_id, created_at, resolved_at
            FROM support_tickets
            WHERE resolved_at IS NOT NULL AND resolved_at < created_at
        """
        bad_tickets = conn.execute(text(q_tickets)).fetchall()
        if bad_tickets:
            violations.append({
                "table": "support_tickets",
                "rule": "resolved_at >= created_at",
                "violation_count": len(bad_tickets),
                "samples": [dict(r._mapping) for r in bad_tickets[:5]],
            })

        # Survey responses submitted within active survey window
        q_responses = """
            SELECT r.response_id, r.survey_id, r.submitted_at, s.start_date, s.end_date
            FROM survey_responses r
            JOIN surveys s ON r.survey_id = s.survey_id
            WHERE substr(r.submitted_at, 1, 10) < s.start_date
               OR substr(r.submitted_at, 1, 10) > s.end_date
        """
        bad_responses = conn.execute(text(q_responses)).fetchall()
        if bad_responses:
            violations.append({
                "table": "survey_responses",
                "rule": "submitted_at within survey start_date and end_date",
                "violation_count": len(bad_responses),
                "samples": [dict(r._mapping) for r in bad_responses[:5]],
            })

        # Support messages sent after ticket creation
        q_messages = """
            SELECT m.message_id, m.ticket_id, m.sent_at, t.created_at as ticket_created_at
            FROM support_messages m
            JOIN support_tickets t ON m.ticket_id = t.ticket_id
            WHERE m.sent_at < t.created_at
        """
        bad_messages = conn.execute(text(q_messages)).fetchall()
        if bad_messages:
            violations.append({
                "table": "support_messages",
                "rule": "sent_at >= ticket created_at",
                "violation_count": len(bad_messages),
                "samples": [dict(r._mapping) for r in bad_messages[:5]],
            })

    return violations


def check_lifecycle_consistency(engine) -> list[dict]:
    """
    Check lifecycle states and transition logic:
      - support_tickets: resolved/closed tickets must have resolved_at populated;
                         open/in_progress tickets must have resolved_at IS NULL.
      - survey_responses: linked surveys must not be in 'draft' lifecycle state.
    """
    violations = []
    with engine.connect() as conn:
        # Ticket lifecycle consistency
        q_ticket_status = """
            SELECT ticket_id, status, created_at, resolved_at
            FROM support_tickets
            WHERE (status IN ('resolved', 'closed') AND resolved_at IS NULL)
               OR (status IN ('open', 'in_progress') AND resolved_at IS NOT NULL)
        """
        bad_ticket_status = conn.execute(text(q_ticket_status)).fetchall()
        if bad_ticket_status:
            violations.append({
                "table": "support_tickets",
                "rule": "resolved/closed tickets have resolved_at; open/in_progress have NULL resolved_at",
                "violation_count": len(bad_ticket_status),
                "samples": [dict(r._mapping) for r in bad_ticket_status[:5]],
            })

        # Responses to draft surveys
        q_draft_surveys = """
            SELECT r.response_id, s.survey_id, s.lifecycle_state
            FROM survey_responses r
            JOIN surveys s ON r.survey_id = s.survey_id
            WHERE s.lifecycle_state = 'draft'
        """
        bad_draft_surveys = conn.execute(text(q_draft_surveys)).fetchall()
        if bad_draft_surveys:
            violations.append({
                "table": "survey_responses",
                "rule": "responses cannot link to draft surveys",
                "violation_count": len(bad_draft_surveys),
                "samples": [dict(r._mapping) for r in bad_draft_surveys[:5]],
            })

    return violations


def check_database_duplicates(engine) -> list[dict]:
    """
    Verify duplicate business keys are absent in database records:
      - reviews: (customer_id, product_id, reviewed_at)
      - survey_responses: (survey_id, customer_id, submitted_at)
      - support_messages: (ticket_id, sent_at)
    """
    violations = []
    checks = [
        ("reviews", ["customer_id", "product_id", "reviewed_at"]),
        ("survey_responses", ["survey_id", "customer_id", "submitted_at"]),
        ("support_messages", ["ticket_id", "sent_at"]),
    ]

    with engine.connect() as conn:
        for table, cols in checks:
            cols_str = ", ".join(f'"{c}"' for c in cols)
            q = f"""
                SELECT {cols_str}, COUNT(*) as dup_count
                FROM "{table}"
                GROUP BY {cols_str}
                HAVING COUNT(*) > 1
            """
            dups = conn.execute(text(q)).fetchall()
            if dups:
                violations.append({
                    "table": table,
                    "columns": cols,
                    "duplicate_clusters": len(dups),
                    "samples": [dict(r._mapping) for r in dups[:5]],
                })

    return violations
