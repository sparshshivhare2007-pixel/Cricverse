import html

def mention_html(user):
    """
    Safe HTML mention for Pyrogram.
    Prevents ENTITY_BOUNDS_INVALID errors.
    """
    name = html.escape(user.first_name or "User")
    return f'<a href="tg://user?id={user.id}">{name}</a>'
