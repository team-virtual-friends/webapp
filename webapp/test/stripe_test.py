import stripe

# Set your Stripe secret key
stripe.api_key = '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'


def fetch_all_checkout_session_completed_events():
    # Initialize an empty list to store all the events
    all_events = []

    # Define the first batch of events
    events = stripe.Event.list(type="checkout.session.completed", limit=100)

    while events.data:
        all_events.extend(events.data)
        # Stripe returns data in pages (pagination). Use the last item's ID to get the next page.
        events = stripe.Event.list(type="checkout.session.completed", limit=100, starting_after=events.data[-1].id)

    return all_events


# Fetch all events
checkout_events = fetch_all_checkout_session_completed_events()

# Process or print the events as needed
for event in checkout_events:
    print(event)

