from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


def has_role(user, roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in roles


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not has_role(request.user, roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


class RoleRequiredMixin(LoginRequiredMixin):
    roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_role(request.user, self.roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


STAFF_ROLES = ("ADMIN", "SALES", "MECHANIC")
