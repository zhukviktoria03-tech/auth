from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrModerator(BasePermission):
    """P3: читання всім; створити: автентифікований;
    змінити/видалити: власник або група Moderators."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return (
            obj.owner_id == user.id
            or user.groups.filter(name="Moderators").exists()
        )