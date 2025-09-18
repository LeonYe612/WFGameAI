import contextvars

# Context variable to store the current user
current_user = contextvars.ContextVar('current_user', default=None)