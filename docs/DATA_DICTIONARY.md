# Data Dictionary — Customer Feedback Analytics (CFA)

This document provides a data dictionary for all core entities in the Customer Feedback Analytics system in accordance with **Step 1** and **Step 9** of the project specification.

For each field, the specification defines:
- **Type**: Data type representation
- **Required / Optional**: Nullability rule
- **Allowed Values / Range**: Value domain or enumeration
- **Units**: Measurement unit (where applicable)
- **Uniqueness**: Primary Key / Unique constraint
- **Validation Rule**: Enforcement rule applied during ingestion and quality gates

---

## 1. Master Data Entities

### 1.1 Customer
Represents a user or business entity providing feedback.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | String | Required | Matches regex `^CUST-\d{4}-\d{6}$` | N/A | **Yes** (PK) | Non-null, immutable, unique identifier |
| `name` | String | Required | Non-empty string | N/A | No | Synthetic customer full name |
| `email` | String | Required | Standard RFC 5322 email format | N/A | **Yes** | Valid synthetic email address |
| `region` | String | Required | `North`, `South`, `East`, `West`, `International` | N/A | No | Must be in allowed region taxonomy |
| `segment` | String | Required | `B2C`, `B2B`, `Enterprise` | N/A | No | Must be in allowed segment taxonomy |
| `created_at` | Date | Required | ISO 8601 Date (`YYYY-MM-DD`) | Days | No | Historical registration date $\le$ current date |
| `lifecycle_state` | String | Required | `draft`, `active`, `closed`, `archived` | N/A | No | Allowed customer lifecycle states |

---

### 1.2 Product
Product catalog reference entity.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | String | Required | Matches regex `^PROD-\d{3}$` | N/A | **Yes** (PK) | Non-null, unique product identifier |
| `name` | String | Required | Non-empty product title | N/A | No | Commercial product name |
| `category` | String | Required | `Smart Home`, `Audio`, `Entertainment`, `Accessories`, `Security`, `Home Appliances`, `Wearables`, `Computing`, `Health` | N/A | No | Must belong to defined product category taxonomy |

---

### 1.3 Channel
Touchpoint through which customer feedback or support requests are submitted.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `channel_id` | String | Required | Matches regex `^CHAN-\d{3}$` | N/A | **Yes** (PK) | Non-null, unique channel code |
| `name` | String | Required | `Website`, `Mobile App`, `Email`, `Phone`, `In-Store`, `Social Media` | N/A | No | Canonical channel display name |
| `type` | String | Required | `digital`, `voice`, `physical` | N/A | No | Must belong to channel types enumeration |

---

### 1.4 Survey
Survey campaign or feedback questionnaire container.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | String | Required | Matches regex `^SUR-\d{4}-\d{6}$` | N/A | **Yes** (PK) | Non-null, unique survey identifier |
| `title` | String | Required | Non-empty text | N/A | No | Descriptive survey campaign title |
| `survey_type` | String | Required | `NPS`, `CSAT`, `CES`, `Product Feedback`, `Post-Purchase` | N/A | No | Must match recognized survey framework |
| `product_id` | String | Required | Valid `product_id` | N/A | No | Foreign Key referencing `products.product_id` |
| `channel_id` | String | Required | Valid `channel_id` | N/A | No | Foreign Key referencing `channels.channel_id` |
| `start_date` | Date | Required | ISO 8601 Date (`YYYY-MM-DD`) | Days | No | Campaign launch date |
| `end_date` | Date | Required | ISO 8601 Date (`YYYY-MM-DD`) | Days | No | Must satisfy `end_date >= start_date` |
| `lifecycle_state` | String | Required | `draft`, `active`, `closed`, `archived` | N/A | No | Campaign operational state |

---

### 1.5 Theme
Taxonomy of feedback topics.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `theme_id` | String | Required | Matches regex `^THEME-\d{6}$` (`THEME-000001` to `THEME-000015`) | N/A | **Yes** (PK) | Non-null, valid 15-item taxonomy key |
| `name` | String | Required | 15 defined themes (e.g., `Product Quality`, `Customer Service`, `Pricing & Value`, etc.) | N/A | No | Canonical theme title |
| `description` | String | Optional | Free text describing scope | N/A | No | Domain guidance for classification |

---

### 1.6 SentimentLabel
Canonical taxonomy of sentiment classifications and polarities.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sentiment_id` | String | Required | Matches regex `^SENT-\d{2}$` (`SENT-01` to `SENT-03`) | N/A | **Yes** (PK) | Non-null, unique sentiment identifier |
| `sentiment_label` | String | Required | `positive`, `neutral`, `negative` | N/A | **Yes** | Unique enum value matching standardized sentiment classes |
| `polarity` | Integer | Required | `-1`, `0`, `1` | Score | No | Numerical directional orientation (-1=negative, 0=neutral, 1=positive) |
| `description` | String | Optional | Free text | N/A | No | Definition and guidelines for the sentiment category |

---

## 2. Transaction / Event Entities

### 2.1 Review
Public or authenticated customer product review.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `review_id` | String | Required | Matches regex `^REV-\d{4}-\d{6}$` | N/A | **Yes** (PK) | Non-null, unique review identifier |
| `customer_id` | String | Required | Valid `customer_id` | N/A | No | Foreign Key referencing `customers.customer_id` |
| `product_id` | String | Required | Valid `product_id` | N/A | No | Foreign Key referencing `products.product_id` |
| `channel_id` | String | Required | Valid `channel_id` | N/A | No | Foreign Key referencing `channels.channel_id` |
| `review_text` | String | Required | Synthetic text | N/A | No | Cannot contain PII or unhandled test markers |
| `star_rating` | Integer | Required | `1` to `5` | Stars | No | Integer in range [1, 5] |
| `sentiment_label` | String | Required | `positive`, `neutral`, `negative` | N/A | No | Derived rule: 1-2=negative, 3=neutral, 4-5=positive |
| `language` | String | Required | `en`, `es`, `fr`, `de` | N/A | No | Allowed language ISO codes |
| `reviewed_at` | DateTime | Required | ISO 8601 Datetime (`YYYY-MM-DD HH:MM:SS`) | Timestamp | No | Event timestamp |
| `is_ambiguous` | Boolean | Required | `True`, `False` | N/A | No | Flags sarcastic or ambiguous submissions |
| `predicted_sentiment` | String | Optional | `positive`, `neutral`, `negative` | N/A | No | Populated by Module 4 NLP inference |
| `predicted_theme` | String | Optional | Valid `theme_id` | N/A | No | Populated by Module 4 NLP classification |

---

### 2.2 SurveyResponse
Individual response submitted to an active survey campaign.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `response_id` | String | Required | Matches regex `^RESP-SUR-\d{4}-\d{6}-\d{3}$` | N/A | **Yes** (PK) | Non-null, unique survey response identifier |
| `survey_id` | String | Required | Valid `survey_id` | N/A | No | Foreign Key referencing `surveys.survey_id` |
| `customer_id` | String | Required | Valid `customer_id` | N/A | No | Foreign Key referencing `customers.customer_id` |
| `response_text` | String | Required | Synthetic text | N/A | No | Cannot contain PII or unhandled test markers |
| `rating` | Integer | Required | `1` to `10` | Score | No | Integer in range [1, 10] |
| `sentiment_label` | String | Required | `positive`, `neutral`, `negative` | N/A | No | Derived rule: 1-4=negative, 5-7=neutral, 8-10=positive |
| `language` | String | Required | `en`, `es`, `fr`, `de` | N/A | No | Allowed language codes |
| `submitted_at` | DateTime | Required | ISO 8601 Datetime | Timestamp | No | Event timestamp within survey active date range |
| `is_ambiguous` | Boolean | Required | `True`, `False` | N/A | No | Flags ambiguous responses |
| `predicted_sentiment` | String | Optional | `positive`, `neutral`, `negative` | N/A | No | Populated by Module 4 NLP inference |
| `predicted_theme` | String | Optional | Valid `theme_id` | N/A | No | Populated by Module 4 NLP classification |

---

### 2.3 SupportTicket
Customer support case container.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ticket_id` | String | Required | Matches regex `^TKT-\d{4}-\d{6}$` | N/A | **Yes** (PK) | Non-null, unique ticket identifier |
| `customer_id` | String | Required | Valid `customer_id` | N/A | No | Foreign Key referencing `customers.customer_id` |
| `channel_id` | String | Required | Valid `channel_id` | N/A | No | Foreign Key referencing `channels.channel_id` |
| `subject` | String | Required | Short summary text | N/A | No | Ticket subject |
| `status` | String | Required | `open`, `in_progress`, `resolved`, `closed` | N/A | No | Ticket lifecycle status |
| `created_at` | DateTime | Required | ISO 8601 Datetime | Timestamp | No | Timestamp of initial ticket opening |
| `resolved_at` | DateTime | Optional | ISO 8601 Datetime | Timestamp | No | Must satisfy `resolved_at >= created_at` when present |

---

### 2.4 SupportMessage
Message exchange under a support ticket.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `message_id` | String | Required | Matches regex `^MSG-TKT-\d{4}-\d{6}-\d{3}$` | N/A | **Yes** (PK) | Non-null, unique message identifier |
| `ticket_id` | String | Required | Valid `ticket_id` | N/A | No | Foreign Key referencing `support_tickets.ticket_id` |
| `sender_type` | String | Required | `customer`, `agent` | N/A | No | Sender role |
| `message_text` | String | Required | Synthetic message body | N/A | No | Cannot contain PII or unhandled test markers |
| `sentiment_label` | String | Required | `positive`, `neutral`, `negative` | N/A | No | Ground-truth message tone |
| `language` | String | Required | `en`, `es`, `fr`, `de` | N/A | No | Allowed language codes |
| `sent_at` | DateTime | Required | ISO 8601 Datetime | Timestamp | No | Timestamp $\ge$ `support_tickets.created_at` |
| `is_ambiguous` | Boolean | Required | `True`, `False` | N/A | No | Ambiguity indicator |
| `predicted_sentiment` | String | Optional | `positive`, `neutral`, `negative` | N/A | No | Populated by Module 4 NLP inference |
| `predicted_theme` | String | Optional | Valid `theme_id` | N/A | No | Populated by Module 4 NLP classification |

---

### 2.5 ActionItem
Operational task generated from recurring theme frequency thresholds.

| Field Name | Type | Required? | Allowed Values / Range | Units | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `action_id` | String | Required | Matches regex `^ACT-\d{4}-\d{6}$` | N/A | **Yes** (PK) | Non-null, unique action identifier |
| `theme_id` | String | Required | Valid `theme_id` | N/A | No | Foreign Key referencing `themes.theme_id` |
| `title` | String | Required | Actionable task title | N/A | No | Derived title matching theme |
| `priority` | String | Required | `high`, `medium`, `low` | N/A | No | Derived rule: $\ge 3\times$ threshold $\rightarrow$ high, $\ge 2\times$ threshold $\rightarrow$ medium, else low |
| `status` | String | Required | `open`, `in_progress`, `done` | N/A | No | Action workflow state |
| `created_at` | Date | Required | ISO 8601 Date (`YYYY-MM-DD`) | Days | No | Generation date |
| `mention_count` | Integer | Required | $\ge 0$ | Count | No | Must be $\ge$ configured threshold |

---

## 3. Bridge Entities (Many-to-Many Relationships)

### 3.1 `review_themes`, `response_themes`, `message_themes`
Bridge tables mapping feedback events to one primary theme and up to two secondary themes.

| Field Name | Type | Required? | Allowed Values / Range | Unique? | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `review_id` / `response_id` / `message_id` | String | Required | Valid parent event ID | Part of Composite PK | Foreign Key referencing parent table |
| `theme_id` | String | Required | Valid `theme_id` from 15-item taxonomy | Part of Composite PK | Foreign Key referencing `themes.theme_id` |
