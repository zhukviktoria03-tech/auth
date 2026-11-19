from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class JWTLogoutView(APIView):
    authentication_classes = []        # прострочений access не повинен ламати вихід
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError as e:
            raise AuthenticationFailed(str(e))
        return Response({"detail": "ok"}, status=200)