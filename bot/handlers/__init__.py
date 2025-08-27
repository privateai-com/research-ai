def get_general_router():
    """Lazy import of general router."""
    from .general import router

    return router


def get_settings_router():
    """Lazy import of settings router."""
    from .settings import router

    return router


def get_notifications_router():
    """Lazy import of notifications router."""
    from .notifications import router

    return router


def get_tasks_router():
    """Lazy import of tasks router."""
    from .task import router

    return router


def get_help_router():
    """Lazy import of help router."""
    from .help import router

    return router


# TODO: Add admin routers (requires admin authentication system)
def get_admin_analytics_router():
    """Lazy import of admin analytics router."""
    from .admin.analytics import router

    return router


def get_admin_metrics_router():
    """Lazy import of admin metrics router."""
    from .admin.metrics import router

    return router


def get_admin_settings_router():
    """Lazy import of admin settings router."""
    from .admin.settings import router

    return router


def get_admin_users_router():
    """Lazy import of admin users router."""
    from .admin.users import router

    return router


# TODO: Add zen routers (requires zen mode implementation)
def get_zen_create_router():
    """Lazy import of zen create router."""
    from .zen.create import router

    return router


def get_zen_manage_router():
    """Lazy import of zen manage router."""
    from .zen.manage import router

    return router


def get_zen_view_router():
    """Lazy import of zen view router."""
    from .zen.view import router

    return router


# TODO: Add advanced tasks routers (requires advanced features implementation)
def get_tasks_create_router():
    """Lazy import of tasks create router."""
    from .tasks.create import router

    return router


def get_tasks_manage_router():
    """Lazy import of tasks manage router."""
    from .tasks.manage import router

    return router


def get_tasks_view_router():
    """Lazy import of tasks view router."""
    from .tasks.view import router

    return router


# For backward compatibility
general_router = property(lambda self: get_general_router())
settings_router = property(lambda self: get_settings_router())
notifications_router = property(lambda self: get_notifications_router())
tasks_router = property(lambda self: get_tasks_router())

__all__ = [
    "general_router",
    "settings_router", 
    "notifications_router",
    "tasks_router",
    "get_general_router",
    "get_settings_router",
    "get_notifications_router",
    "get_tasks_router",
    "get_help_router",
    # Admin routers (TODO: enable when admin system is ready)
    # "get_admin_analytics_router",
    # "get_admin_metrics_router", 
    # "get_admin_settings_router",
    # "get_admin_users_router",
    # Zen routers (TODO: enable when zen mode is ready)
    # "get_zen_create_router",
    # "get_zen_manage_router",
    # "get_zen_view_router",
    # Advanced tasks routers (TODO: enable when advanced features are ready)
    # "get_tasks_create_router",
    # "get_tasks_manage_router",
    # "get_tasks_view_router",
]
