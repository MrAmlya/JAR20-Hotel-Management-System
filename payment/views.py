from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic

from main.models import Facility, Reservation, Staff
from .forms import CheckoutRequestForm
from .models import CheckIn, CheckOut


def percentage(part, whole):
    if whole <= 0:
        return 0
    return round((part / whole) * 100)


def sum_field(queryset, field_name):
    return queryset.aggregate(total=Sum(field_name))['total'] or 0


# Create your views here.
@permission_required('main.can_view_staff', login_url='login')
def payment_index(request):
    title = "Payment Dashboard"
    num_of_reservations = Reservation.objects.count()
    num_of_check_ins = CheckIn.objects.count()
    num_of_check_outs = CheckOut.objects.count()
    pending_check_ins = Reservation.objects.filter(checkin__isnull=True).count()
    active_check_ins = CheckIn.objects.filter(checkout__isnull=True).count()
    completed_check_ins = CheckIn.objects.filter(checkout__isnull=False).count()
    initial_collected = sum_field(CheckIn.objects.all(), 'initial_amount')
    checkout_balance_collected = sum_field(CheckOut.objects.all(), 'pay_amount')
    checkout_billed_amount = sum_field(CheckOut.objects.all(), 'total_amount')
    total_collected = initial_collected + checkout_balance_collected
    last_checked_in = CheckIn.objects.order_by('-check_in_date_time').first()
    last_checked_out = CheckOut.objects.order_by('-check_out_date_time').first()

    return render(
        request,
        'payment_index.html', {
            'title': title,
            'num_of_reservations': num_of_reservations,
            'num_of_check_ins': num_of_check_ins,
            'num_of_check_outs': num_of_check_outs,
            'pending_check_ins': pending_check_ins,
            'active_check_ins': active_check_ins,
            'completed_check_ins': completed_check_ins,
            'initial_collected': initial_collected,
            'checkout_balance_collected': checkout_balance_collected,
            'checkout_billed_amount': checkout_billed_amount,
            'total_collected': total_collected,
            'checkin_percent': percentage(num_of_check_ins, num_of_reservations),
            'active_checkin_percent': percentage(active_check_ins, num_of_check_ins),
            'checkout_percent': percentage(num_of_check_outs, num_of_check_ins),
            'collection_percent': 100 if total_collected > 0 else 0,
            'last_checked_in': last_checked_in,
            'last_checked_out': last_checked_out,
        }
    )


class CheckInListView(PermissionRequiredMixin, generic.ListView, generic.FormView):
    model = CheckIn
    paginate_by = 5
    queryset = CheckIn.objects.all().order_by('-check_in_date_time')
    allow_empty = True
    permission_required = 'main.can_view_customer'
    title = "Check-In List"
    form_class = CheckoutRequestForm
    extra_context = {
        'title': title,
    }
    success_url = reverse_lazy('check_out-list')

    @transaction.atomic
    def form_valid(self, form):
        try:
            with transaction.atomic():
                checkout = form.save(commit=False)
                checkout.user = self.request.user
                checkout.save()
                for room in checkout.check_in.reservation.room_set.all():
                    room.reservation = None
                    room.save()
        except IntegrityError:
            raise Http404
        return super().form_valid(form)


class CheckInDetailView(PermissionRequiredMixin, generic.DetailView):
    model = CheckIn
    permission_required = 'main.can_view_customer'
    title = "Check-In Detail"

    extra_context = {
        'title': title,
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        checkin = context['checkin']
        rooms = checkin.rooms
        facilities = Facility.objects.all()
        staff = Staff.objects.filter(user=checkin.user)
        if not staff.count():
            staff = Staff.objects.none()
        else:
            staff = Staff.objects.get(user=checkin.user)
        context['staff'] = staff
        context['facilities'] = facilities
        context['num_facilities'] = facilities.count()
        if rooms:
            context['rooms'] = checkin.rooms.split(', ')
        return context


class CheckOutListView(PermissionRequiredMixin, generic.ListView):
    model = CheckOut
    paginate_by = 5
    allow_empty = True
    queryset = CheckOut.objects.all().order_by('-check_out_date_time')
    permission_required = 'main.can_view_customer'
    title = "Check-Out List"
    extra_context = {
        'title': title,
    }


class CheckOutDetailView(PermissionRequiredMixin, generic.DetailView):
    model = CheckOut
    permission_required = 'main.can_view_customer'
    title = "Check-Out Detail"
    extra_context = {
        'title': title,
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        checkout = context['checkout']

        staff = Staff.objects.filter(user=checkout.user)
        if not staff.count():
            staff = Staff.objects.none()
        else:
            staff = Staff.objects.get(user=checkout.user)
        context['staff'] = staff

        return context
