CREATE TABLE channels (
	channel_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	PRIMARY KEY (channel_id)
);

CREATE TABLE customers (
	customer_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	region VARCHAR NOT NULL, 
	segment VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	lifecycle_state VARCHAR NOT NULL, 
	PRIMARY KEY (customer_id), 
	UNIQUE (email)
);

CREATE TABLE products (
	product_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	PRIMARY KEY (product_id)
);

CREATE TABLE sentiment_labels (
	sentiment_id VARCHAR NOT NULL, 
	sentiment_label VARCHAR NOT NULL, 
	polarity INTEGER NOT NULL, 
	description VARCHAR, 
	PRIMARY KEY (sentiment_id), 
	UNIQUE (sentiment_label)
);

CREATE TABLE status_history (
	history_id VARCHAR NOT NULL, 
	entity_type VARCHAR NOT NULL, 
	entity_id VARCHAR NOT NULL, 
	old_status VARCHAR, 
	new_status VARCHAR NOT NULL, 
	changed_at VARCHAR NOT NULL, 
	changed_by VARCHAR NOT NULL, 
	PRIMARY KEY (history_id)
);

CREATE TABLE themes (
	theme_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	PRIMARY KEY (theme_id)
);

CREATE TABLE action_items (
	action_id VARCHAR NOT NULL, 
	theme_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	priority VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	mention_count INTEGER NOT NULL, 
	PRIMARY KEY (action_id), 
	FOREIGN KEY(theme_id) REFERENCES themes (theme_id)
);

CREATE TABLE reviews (
	review_id VARCHAR NOT NULL, 
	customer_id VARCHAR NOT NULL, 
	product_id VARCHAR NOT NULL, 
	channel_id VARCHAR NOT NULL, 
	review_text VARCHAR NOT NULL, 
	star_rating INTEGER NOT NULL, 
	sentiment_label VARCHAR NOT NULL, 
	language VARCHAR NOT NULL, 
	reviewed_at VARCHAR NOT NULL, 
	is_ambiguous BOOLEAN NOT NULL, 
	predicted_sentiment VARCHAR, 
	predicted_theme VARCHAR, 
	PRIMARY KEY (review_id), 
	FOREIGN KEY(customer_id) REFERENCES customers (customer_id), 
	FOREIGN KEY(product_id) REFERENCES products (product_id), 
	FOREIGN KEY(channel_id) REFERENCES channels (channel_id)
);

CREATE TABLE support_tickets (
	ticket_id VARCHAR NOT NULL, 
	customer_id VARCHAR NOT NULL, 
	channel_id VARCHAR NOT NULL, 
	product_id VARCHAR, 
	subject VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	resolved_at VARCHAR, 
	PRIMARY KEY (ticket_id), 
	FOREIGN KEY(customer_id) REFERENCES customers (customer_id), 
	FOREIGN KEY(channel_id) REFERENCES channels (channel_id), 
	FOREIGN KEY(product_id) REFERENCES products (product_id)
);

CREATE TABLE surveys (
	survey_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	survey_type VARCHAR NOT NULL, 
	product_id VARCHAR NOT NULL, 
	channel_id VARCHAR NOT NULL, 
	start_date VARCHAR NOT NULL, 
	end_date VARCHAR NOT NULL, 
	lifecycle_state VARCHAR NOT NULL, 
	PRIMARY KEY (survey_id), 
	FOREIGN KEY(product_id) REFERENCES products (product_id), 
	FOREIGN KEY(channel_id) REFERENCES channels (channel_id)
);

CREATE TABLE review_themes (
	review_id VARCHAR NOT NULL, 
	theme_id VARCHAR NOT NULL, 
	PRIMARY KEY (review_id, theme_id), 
	FOREIGN KEY(review_id) REFERENCES reviews (review_id), 
	FOREIGN KEY(theme_id) REFERENCES themes (theme_id)
);

CREATE TABLE support_messages (
	message_id VARCHAR NOT NULL, 
	ticket_id VARCHAR NOT NULL, 
	sender_type VARCHAR NOT NULL, 
	message_text VARCHAR NOT NULL, 
	sentiment_label VARCHAR NOT NULL, 
	language VARCHAR NOT NULL, 
	sent_at VARCHAR NOT NULL, 
	is_ambiguous BOOLEAN NOT NULL, 
	predicted_sentiment VARCHAR, 
	predicted_theme VARCHAR, 
	PRIMARY KEY (message_id), 
	FOREIGN KEY(ticket_id) REFERENCES support_tickets (ticket_id)
);

CREATE TABLE survey_responses (
	response_id VARCHAR NOT NULL, 
	survey_id VARCHAR NOT NULL, 
	customer_id VARCHAR NOT NULL, 
	response_text VARCHAR NOT NULL, 
	rating INTEGER NOT NULL, 
	sentiment_label VARCHAR NOT NULL, 
	language VARCHAR NOT NULL, 
	submitted_at VARCHAR NOT NULL, 
	is_ambiguous BOOLEAN NOT NULL, 
	predicted_sentiment VARCHAR, 
	predicted_theme VARCHAR, 
	PRIMARY KEY (response_id), 
	FOREIGN KEY(survey_id) REFERENCES surveys (survey_id), 
	FOREIGN KEY(customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE message_themes (
	message_id VARCHAR NOT NULL, 
	theme_id VARCHAR NOT NULL, 
	PRIMARY KEY (message_id, theme_id), 
	FOREIGN KEY(message_id) REFERENCES support_messages (message_id), 
	FOREIGN KEY(theme_id) REFERENCES themes (theme_id)
);

CREATE TABLE response_themes (
	response_id VARCHAR NOT NULL, 
	theme_id VARCHAR NOT NULL, 
	PRIMARY KEY (response_id, theme_id), 
	FOREIGN KEY(response_id) REFERENCES survey_responses (response_id), 
	FOREIGN KEY(theme_id) REFERENCES themes (theme_id)
);
