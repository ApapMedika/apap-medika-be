import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    JWT Authentication Middleware for API endpoints
    """
    
    def process_request(self, request):
        # Skip JWT authentication for non-API endpoints
        if not request.path.startswith('/api/'):
            return None
        
        # Skip JWT for login, signup, and public endpoints
        public_endpoints = [
            '/api/login/',
            '/api/signup/',
            '/api/jwt/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
        ]
        
        if request.path in public_endpoints:
            return None
        
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get('id')
            
            if not user_id:
                return JsonResponse({'error': 'Invalid token'}, status=401)
            
            # Get user from database
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
            
            # Set user in request
            request.user = user
            request.jwt_payload = payload
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=401)
        except Exception as e:
            return JsonResponse({'error': 'Authentication failed'}, status=401)
        
        return None