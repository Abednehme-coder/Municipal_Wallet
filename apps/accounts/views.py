from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
# from django_ratelimit.decorators import ratelimit
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, LoginSerializer, ChangePasswordSerializer
from apps.audit.models import AuditLog


class UserRegistrationView(generics.CreateAPIView):
    """User registration view"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create token for immediate login
        token, created = Token.objects.get_or_create(user=user)
        
        # Log registration
        AuditLog.log_action(
            user=user,
            action='USER_CREATED',
            description=f'User {user.email} registered',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'user': UserSerializer(user).data,
                'token': token.key
            }
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
# @ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    """User login view"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        
        # Create or get token
        token, created = Token.objects.get_or_create(user=user)
        
        # Log login
        AuditLog.log_action(
            user=user,
            action='LOGIN',
            description=f'User {user.email} logged in',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': UserSerializer(user).data,
                'token': token.key
            }
        })
    
    return Response({
        'success': False,
        'message': 'Invalid credentials',
        'errors': serializer.errors
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """User logout view"""
    # Log logout
    AuditLog.log_action(
        user=request.user,
        action='LOGOUT',
        description=f'User {request.user.email} logged out',
        request=request
    )
    
    # Delete token
    try:
        request.user.auth_token.delete()
    except:
        pass
    
    logout(request)
    
    return Response({
        'success': True,
        'message': 'Logout successful'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get current user profile"""
    return Response({
        'success': True,
        'data': UserSerializer(request.user).data
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Update user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        user = serializer.save()
        
        # Log profile update
        AuditLog.log_action(
            user=request.user,
            action='USER_UPDATED',
            description=f'User {user.email} updated profile',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': UserSerializer(user).data
        })
    
    return Response({
        'success': False,
        'message': 'Update failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Log password change
        AuditLog.log_action(
            user=user,
            action='USER_UPDATED',
            description=f'User {user.email} changed password',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        })
    
    return Response({
        'success': False,
        'message': 'Password change failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """List all users (admin only)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only show users from the same city unless admin
        if self.request.user.role == 'ADMIN':
            return User.objects.all()
        return User.objects.filter(city=self.request.user.city)
