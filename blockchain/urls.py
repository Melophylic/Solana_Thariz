# urls.py (fixed)
from django.urls import path
from django.contrib.auth import views as django_auth_views  # Renamed to avoid conflicts
from . import views
from . import auth_views as custom_auth_views  # Renamed to avoid conflicts
from . import realistic_views

urlpatterns = [
    # Dashboard and main functionality
    path('', views.dashboard, name='dashboard'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<str:student_id>/', views.view_student, name='view_student'),
    path('students/<str:student_id>/update/', views.update_student, name='update_student'),
    path('validate/', views.validate_blockchain, name='validate_blockchain'),
    path('generate-key/', views.generate_key, name='generate_key'),
    
    # Authentication URLs
    path('login/', custom_auth_views.login_view, name='login'),  # Our custom login view
    path('logout/', django_auth_views.LogoutView.as_view(next_page='login'), name='logout'),  # Django's built-in view
    path('register/', custom_auth_views.register_view, name='register'),  # Our custom register view
    
    # Admin management
    path('admin/invitations/', custom_auth_views.admin_invitations, name='admin_invitations'),
    path('admin/invitations/generate/', custom_auth_views.generate_invitation, name='generate_invitation'),
    path('admin/approvals/', custom_auth_views.admin_approval, name='admin_approval'),
    
    # Password management - using Django's built-in views with our templates
    path('password_reset/',
            django_auth_views.PasswordResetView.as_view(
                template_name='password_reset.html',
                email_template_name='password_reset_email.html',
                subject_template_name='password_reset_subject.txt'
            ),
            name='password_reset'),
    path('password_reset/done/',
            django_auth_views.PasswordResetDoneView.as_view(
                template_name='password_reset_done.html'
            ),
            name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
            django_auth_views.PasswordResetConfirmView.as_view(
                template_name='password_reset_confirm.html'
            ),
            name='password_reset_confirm'),
    path('reset/done/',
            django_auth_views.PasswordResetCompleteView.as_view(
                template_name='password_reset_complete.html'
            ),
            name='password_reset_complete'),

    path('repair/', views.repair_blockchain_view, name='repair_blockchain'),
    path('advanced-repair/', views.advanced_repair_view, name='advanced_repair'),

    path('realistic/', realistic_views.setup_blockchain, name='setup_blockchain'),
    path('realistic/explorer/', realistic_views.blockchain_explorer, name='blockchain_explorer'),
    path('realistic/block/<int:block_number>/', realistic_views.block_detail, name='block_detail'),
    path('realistic/transaction/<str:tx_hash>/', realistic_views.transaction_detail, name='transaction_detail'),
    path('realistic/students/', realistic_views.student_blockchain_view, name='student_blockchain_view'),
    path('realistic/students/<str:student_id>/', realistic_views.student_record_detail, name='student_record_detail'),
    path('realistic/students/add/', realistic_views.add_student_blockchain, name='add_student_blockchain'),
    path('realistic/students/<str:student_id>/update/', realistic_views.update_student_blockchain, name='update_student_blockchain'),
    path('realistic/students/<str:student_id>/invalidate/', realistic_views.invalidate_student_blockchain, name='invalidate_student_blockchain'),
    path('realistic/mine/', realistic_views.mine_pending_transactions, name='mine_transactions'),
    path('realistic/fix/', realistic_views.create_fix_transaction, name='create_fix_transaction'),
    path('realistic/fix-block3/', realistic_views.fix_block3_issue, name='fix_block3_issue'),
]