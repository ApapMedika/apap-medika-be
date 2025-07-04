from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Bill
from .serializers import (
    BillSerializer, CreateBillSerializer, UpdateBillSerializer,
    PayBillSerializer, BillSummarySerializer, UpdateBillComponentsSerializer,
    BillDetailSerializer
)
from common.permissions import (
    IsAdminUser, IsAdminOrNurseUser, IsPatientUser, IsAdminOrNurseOrPatientUser
)

# ==================== BILL VIEWS ====================

class BillListView(generics.ListCreateAPIView):
    """
    List all bills or create new bill
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['id', 'patient__user__name', 'patient__nik']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateBillSerializer
        return BillSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrNurseOrPatientUser()]  # PBI-BE-B2: POST Create Bill (Admin, Patient, Nurse)
        return [IsAdminUser()]  # List bills - Admin only
    
    def get_queryset(self):
        queryset = Bill.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        return queryset

class BillDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update bill details
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdateBillSerializer
        return BillDetailSerializer
    
    def get_queryset(self):
        queryset = Bill.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        return queryset
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsPatientUser()]  # PBI-BE-B3: PUT Update Bill (Patient)
        return [permissions.IsAuthenticated()]

class BillsByPatientView(generics.ListAPIView):
    """
    GET All Bill by PatientId (PBI-BE-B1)
    Returns the bill for a given patientId
    """
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id']
    ordering = ['-created_at']
    
    def get_queryset(self):
        patient_id = self.kwargs['patient_id']
        
        # Check permissions - Patient can only view their own bills
        if (self.request.user.role == 'PATIENT' and 
            str(self.request.user.patient.user.id) != str(patient_id)):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view your own bills.")
        
        return Bill.objects.filter(
            patient__user__id=patient_id,
            deleted_at__isnull=True
        )

class CreateBillView(APIView):
    """
    POST Create Bill (PBI-BE-B2)
    Bill successfully saved (Admin, Patient, Nurse)
    This API is called when creating an appointment (Admin, Patient)
    Required fields are: appointment id (Admin, Patient)
    This API is called when creating a reservation that is not related to an appointment (Nurse)
    Required fields are reservation id (Nurse)
    """
    permission_classes = [IsAdminOrNurseOrPatientUser]
    
    def post(self, request):
        serializer = CreateBillSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            bill = serializer.save()
            
            return Response({
                'message': 'Bill created successfully',
                'bill': BillSerializer(bill).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateBillView(APIView):
    """
    PUT Update Bill (PBI-BE-B3)
    Bill successfully updated according to the given payload (reservation id, policy id, status)
    """
    permission_classes = [IsPatientUser]
    
    def put(self, request, pk):
        try:
            bill = Bill.objects.get(pk=pk, deleted_at__isnull=True)
        except Bill.DoesNotExist:
            return Response({'error': 'Bill not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if patient owns this bill
        if request.user.role == 'PATIENT' and bill.patient != request.user.patient:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only update your own bills.")
        
        serializer = UpdateBillSerializer(bill, data=request.data, context={'request': request})
        
        if serializer.is_valid():
            updated_bill = serializer.save()
            
            return Response({
                'message': 'Bill updated successfully',
                'bill': BillSerializer(updated_bill).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PayBillView(APIView):
    """
    Process bill payment
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PayBillSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            result = serializer.save()
            
            return Response({
                'message': result['message'],
                'payment_method': result['payment_method'],
                'bill': BillSerializer(result['bill']).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateBillComponentsView(APIView):
    """
    Update all bill components and statuses
    This should be called periodically or after status changes in related services
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        serializer = UpdateBillComponentsSerializer(data={}, context={'request': request})
        
        if serializer.is_valid():
            result = serializer.save()
            
            return Response({
                'message': f'Updated {result["updated_bills"]} bills successfully',
                'updated_bills': result['updated_bills']
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BillSummaryView(APIView):
    """
    Get bill summary statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        queryset = Bill.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=request.user.patient)
        
        # Calculate summary statistics
        total_bills = queryset.count()
        unpaid_bills = queryset.filter(status='UNPAID').count()
        paid_bills = queryset.filter(status='PAID').count()
        
        unpaid_amount = queryset.filter(status='UNPAID').aggregate(
            total=Sum('total_amount_due')
        )['total'] or 0
        
        paid_amount = queryset.filter(status='PAID').aggregate(
            total=Sum('total_amount_due')
        )['total'] or 0
        
        summary_data = {
            'total_bills': total_bills,
            'unpaid_bills': unpaid_bills,
            'paid_bills': paid_bills,
            'total_amount_unpaid': unpaid_amount,
            'total_amount_paid': paid_amount
        }
        
        serializer = BillSummarySerializer(summary_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UnpaidBillsView(generics.ListAPIView):
    """
    Get all unpaid bills
    """
    serializer_class = BillSerializer
    permission_classes = [IsAdminOrNurseUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name', 'patient__nik']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Bill.objects.filter(
            status='UNPAID',
            deleted_at__isnull=True
        )

class BillStatisticsView(APIView):
    """
    Get bill statistics by period
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        period = request.query_params.get('period', 'monthly')
        year = request.query_params.get('year')
        status_filter = request.query_params.get('status')
        
        if not year:
            return Response(
                {'error': 'Year parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Year must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Base queryset
        queryset = Bill.objects.filter(
            created_at__year=year,
            deleted_at__isnull=True
        )
        
        # Filter by status if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        if period == 'monthly':
            # Monthly statistics
            stats = []
            for month in range(1, 13):
                month_bills = queryset.filter(created_at__month=month)
                count = month_bills.count()
                total_amount = month_bills.aggregate(
                    total=Sum('total_amount_due')
                )['total'] or 0
                
                stats.append({
                    'period': f"{year}-{month:02d}",
                    'count': count,
                    'total_amount': float(total_amount)
                })
        
        elif period == 'quarterly':
            # Quarterly statistics
            stats = []
            quarters = [
                (1, [1, 2, 3]),
                (2, [4, 5, 6]),
                (3, [7, 8, 9]),
                (4, [10, 11, 12])
            ]
            
            for quarter, months in quarters:
                quarter_bills = queryset.filter(created_at__month__in=months)
                count = quarter_bills.count()
                total_amount = quarter_bills.aggregate(
                    total=Sum('total_amount_due')
                )['total'] or 0
                
                stats.append({
                    'period': f"{year}-Q{quarter}",
                    'count': count,
                    'total_amount': float(total_amount)
                })
        
        else:
            return Response(
                {'error': 'Period must be "monthly" or "quarterly"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'period': period,
            'year': year,
            'statistics': stats
        }, status=status.HTTP_200_OK)

class BillChartDataView(APIView):
    """
    Get bill chart data for frontend
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        period = request.query_params.get('period', 'monthly')
        year = request.query_params.get('year')
        metric = request.query_params.get('metric', 'count')  # count or amount
        
        if not year:
            return Response(
                {'error': 'Year parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Year must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        labels = []
        paid_data = []
        unpaid_data = []
        
        if period == 'monthly':
            month_names = [
                'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
            ]
            
            for month in range(1, 13):
                if metric == 'count':
                    paid_count = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month=month,
                        status='PAID',
                        deleted_at__isnull=True
                    ).count()
                    
                    unpaid_count = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month=month,
                        status='UNPAID',
                        deleted_at__isnull=True
                    ).count()
                    
                    paid_data.append(paid_count)
                    unpaid_data.append(unpaid_count)
                
                else:  # amount
                    paid_amount = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month=month,
                        status='PAID',
                        deleted_at__isnull=True
                    ).aggregate(total=Sum('total_amount_due'))['total'] or 0
                    
                    unpaid_amount = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month=month,
                        status='UNPAID',
                        deleted_at__isnull=True
                    ).aggregate(total=Sum('total_amount_due'))['total'] or 0
                    
                    paid_data.append(float(paid_amount))
                    unpaid_data.append(float(unpaid_amount))
                
                labels.append(month_names[month - 1])
        
        elif period == 'quarterly':
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            quarter_months = [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9],
                [10, 11, 12]
            ]
            
            for i, months in enumerate(quarter_months):
                if metric == 'count':
                    paid_count = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month__in=months,
                        status='PAID',
                        deleted_at__isnull=True
                    ).count()
                    
                    unpaid_count = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month__in=months,
                        status='UNPAID',
                        deleted_at__isnull=True
                    ).count()
                    
                    paid_data.append(paid_count)
                    unpaid_data.append(unpaid_count)
                
                else:  # amount
                    paid_amount = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month__in=months,
                        status='PAID',
                        deleted_at__isnull=True
                    ).aggregate(total=Sum('total_amount_due'))['total'] or 0
                    
                    unpaid_amount = Bill.objects.filter(
                        created_at__year=year,
                        created_at__month__in=months,
                        status='UNPAID',
                        deleted_at__isnull=True
                    ).aggregate(total=Sum('total_amount_due'))['total'] or 0
                    
                    paid_data.append(float(paid_amount))
                    unpaid_data.append(float(unpaid_amount))
                
                labels.append(quarters[i])
        
        return Response({
            'labels': labels,
            'datasets': [
                {
                    'label': f'Paid Bills {year}',
                    'data': paid_data,
                    'backgroundColor': 'rgba(34, 197, 94, 0.5)',
                    'borderColor': 'rgba(34, 197, 94, 1)',
                    'borderWidth': 1
                },
                {
                    'label': f'Unpaid Bills {year}',
                    'data': unpaid_data,
                    'backgroundColor': 'rgba(239, 68, 68, 0.5)',
                    'borderColor': 'rgba(239, 68, 68, 1)',
                    'borderWidth': 1
                }
            ]
        }, status=status.HTTP_200_OK)

# ==================== PATIENT-SPECIFIC VIEWS ====================

class PatientBillListView(generics.ListAPIView):
    """
    List bills for patient
    """
    serializer_class = BillSerializer
    permission_classes = [IsPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Bill.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )

class PatientBillDetailView(generics.RetrieveAPIView):
    """
    Get bill details for patient
    """
    serializer_class = BillDetailSerializer
    permission_classes = [IsPatientUser]
    
    def get_queryset(self):
        return Bill.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )