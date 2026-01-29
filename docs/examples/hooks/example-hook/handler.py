"""
Example Hook Handler

This handler will be called when matching events occur.
"""


async def handler(event):
    """
    Handle hook events

    Args:
        event: InternalHookEvent instance with:
            - type: Event type (command, session, agent, gateway)
            - action: Event action
            - session_key: Session identifier
            - context: Event context data
            - timestamp: Event timestamp
            - messages: List of messages to return to user
    """
    from loguru import logger

    logger.info(
        f"🎯 Example hook triggered: {event.type}:{event.action} "
        f"(session={event.session_key})"
    )

    # Add a message that will be shown to the user
    event.messages.append(f"✨ Example hook executed for {event.action}!")

    # Access event context
    if event.context:
        logger.debug(f"Event context: {event.context}")
