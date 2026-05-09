from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User, Group
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404  # For displaying in template
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic

from .forms import Signup, ReservationForm, CheckInRequestForm
from .models import Room, Reservation, Customer, Staff  # Import Models


def percentage(part, whole):
    if whole <= 0:
        return 0
    return round((part / whole) * 100)


def get_staffs_group():
    staffs_group, _ = Group.objects.get_or_create(name="Staffs")
    permissions = Permission.objects.filter(content_type__app_label__in=['main', 'payment'])
    staffs_group.permissions.add(*permissions)
    return staffs_group


def get_reservation_staff(user):
    staff = Staff.objects.filter(user=user).first()
    if staff:
        return staff

    if user.is_staff or user.is_superuser:
        first_name = user.first_name or user.username
        last_name = user.last_name or 'Admin'
        email = user.email or 'admin@example.com'
        return Staff.objects.create(
            first_name=first_name,
            middle_name='',
            last_name=last_name,
            contact_no='N/A',
            address='N/A',
            email_address=email,
            user=user,
        )

    raise Http404(_("Your account is not linked to a staff profile."))


def index(request):
    """
    This is the view for homepage.
    This is a function based view.
    """
    page_title = _("Hotel Management System")  # For page title as well as heading
    total_num_rooms = Room.objects.count()
    available_num_rooms = Room.objects.filter(reservation__isnull=True).count()
    reserved_num_rooms = total_num_rooms - available_num_rooms
    total_num_reservations = Reservation.objects.count()
    pending_reservations = Reservation.objects.filter(checkin__isnull=True).count()
    active_reservations = Reservation.objects.filter(
        checkin__isnull=False,
        checkin__checkout__isnull=True,
    ).count()
    completed_reservations = Reservation.objects.filter(checkin__checkout__isnull=False).count()
    total_num_staffs = Staff.objects.count()
    staff_with_accounts = Staff.objects.filter(user__isnull=False).count()
    staff_without_accounts = total_num_staffs - staff_with_accounts
    total_num_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(
        reservation__checkin__isnull=False,
        reservation__checkin__checkout__isnull=True,
    ).distinct().count()
    customers_with_reservations = Customer.objects.filter(reservation__isnull=False).distinct().count()
    last_reserved_by = Reservation.objects.order_by('-reservation_date_time').first()

    return render(
        request,
        'index.html',
        # context is whatever sent to the template.
        # the index of the dictionary i.e. title in 'title': page_title
        # is used as variable in templates
        # where as the next one is the variable of this function
        {
            'title': page_title,
            'total_num_rooms': total_num_rooms,
            'available_num_rooms': available_num_rooms,
            'reserved_num_rooms': reserved_num_rooms,
            'total_num_reservations': total_num_reservations,
            'pending_reservations': pending_reservations,
            'active_reservations': active_reservations,
            'completed_reservations': completed_reservations,
            'total_num_staffs': total_num_staffs,
            'staff_with_accounts': staff_with_accounts,
            'staff_without_accounts': staff_without_accounts,
            'total_num_customers': total_num_customers,
            'active_customers': active_customers,
            'customers_with_reservations': customers_with_reservations,
            'room_occupancy_percent': percentage(reserved_num_rooms, total_num_rooms),
            'available_rooms_percent': percentage(available_num_rooms, total_num_rooms),
            'active_reservation_percent': percentage(active_reservations, total_num_reservations),
            'staff_account_percent': percentage(staff_with_accounts, total_num_staffs),
            'active_customer_percent': percentage(active_customers, total_num_customers),
            'last_reserved_by': last_reserved_by,
        }
    )


@transaction.atomic
def signup(request):
    title = "Signup"
    if request.user.is_authenticated:
        request.session.flush()
    if request.method == 'POST':
        form = Signup(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    staffs_group = get_staffs_group()
                    form.save()
                    staff_id = form.cleaned_data['staff_id']
                    username = form.cleaned_data['username']
                    s = get_object_or_404(Staff, staff_id__exact=staff_id)
                    s.user = get_object_or_404(User, username__iexact=username)
                    s.user.set_password(form.cleaned_data['password1'])
                    s.user.groups.add(staffs_group)
                    s.user.save()
                    s.save()
            except IntegrityError:
                raise Http404
            return redirect('index')
    else:
        form = Signup()

    return render(
        request,
        'signup.html', {
            'form': form, 'title': title},
    )


@permission_required('main.add_reservation', 'login', raise_exception=True)
@transaction.atomic
def reserve(request):
    title = "Add Reservation"
    reservation = Reservation.objects.none()
    if request.method == 'POST':
        reservation_form = ReservationForm(request.POST)
        if reservation_form.is_valid():
            try:
                with transaction.atomic():
                    customer = Customer(
                        first_name=reservation_form.cleaned_data.get('first_name'),
                        middle_name=reservation_form.cleaned_data.get('middle_name'),
                        last_name=reservation_form.cleaned_data.get('last_name'),
                        email_address=reservation_form.cleaned_data.get('email'),
                        contact_no=reservation_form.cleaned_data.get('contact_no'),
                        address=reservation_form.cleaned_data.get('address'),
                    )
                    customer.save()
                    staff = request.user
                    reservation = Reservation(
                        staff=get_reservation_staff(staff),
                        customer=customer,
                        no_of_children=reservation_form.cleaned_data.get('no_of_children'),
                        no_of_adults=reservation_form.cleaned_data.get('no_of_adults'),
                        expected_arrival_date_time=reservation_form.cleaned_data.get('expected_arrival_date_time'),
                        expected_departure_date_time=reservation_form.cleaned_data.get('expected_departure_date_time'),
                        reservation_date_time=timezone.now(),
                    )
                    reservation.save()
                    for room in reservation_form.cleaned_data.get('rooms'):
                        room.reservation = reservation
                        room.save()
            except IntegrityError:
                raise Http404
            return render(
                request,
                'reserve_success.html', {
                    'reservation': reservation,
                }
            )
    else:
        reservation_form = ReservationForm()

    return render(
        request,
        'reserve.html', {
            'title': title,
            'reservation_form': reservation_form,
        }
    )


def reserve_success(request):
    return redirect('reservations')


# For generic ListView or DetailView, the default templates should be stored in templates/{{app_name}}/{{template_name}}
# By default template_name = modelName_list || modelName_detail.
# eg room_list, room_detail
# @permission_required('main.can_view_staff')
class RoomListView(PermissionRequiredMixin, generic.ListView):
    """
    View for list of rooms.
    Implements generic ListView.
    """
    model = Room  # Chooses the model for listing objects
    paginate_by = 5  # By how many objects this has to be paginated
    title = _("Room List")  # This is used for title and heading
    permission_required = 'main.can_view_room'

    # By default only objects of the model are sent as context
    # However extra context can be passed using field extra_context
    # Here title is passed.

    extra_context = {'title': title}

    # By default:
    # template_name = room_list
    # if you want to change it, use field template_name
    # here don't do this, since it is already done as default.
    # for own views, it can be done.

    def get_queryset(self):
        filter_value = self.request.GET.get('filter', 'all')
        if filter_value == 'all':
            filter_value = 0
        elif filter_value == 'avail':
            filter_value = 1
        try:
            new_context = Room.objects.filter(availability__in=[filter_value, 1])
        except ValidationError:
            raise Http404(_("Wrong filter argument given."))
        return new_context

    def get_context_data(self, **kwargs):
        context = super(RoomListView, self).get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter', 'all')
        return context


class RoomDetailView(PermissionRequiredMixin, generic.DetailView):
    """
    View for detail of room
    Implements generic DetailView
    """
    # The remaining are same as previous.
    model = Room
    title = _("Room Information")
    permission_required = 'main.can_view_room'
    extra_context = {'title': title}


class ReservationListView(PermissionRequiredMixin, generic.ListView, generic.FormView):
    """
        View for list of reservations.
        Implements generic ListView.
        """
    model = Reservation
    # queryset field selects the objects to be displayed by the query.
    # Here, the objects are displayed by reservation date time in descending order
    queryset = Reservation.objects.all().order_by('-reservation_date_time')
    title = _("Reservation List")
    paginate_by = 5
    allow_empty = True
    form_class = CheckInRequestForm
    success_url = reverse_lazy('check_in-list')
    permission_required = 'main.can_view_reservation'
    extra_context = {'title': title}

    @transaction.atomic
    def form_valid(self, form):
        try:
            with transaction.atomic():
                checkin = form.save(commit=False)
                checkin.user = self.request.user
                checkin.save()
        except IntegrityError:
            raise Http404
        return super().form_valid(form)


class ReservationDetailView(PermissionRequiredMixin, generic.DetailView):
    """
    View for detail of reservation
    Implements generic DetailView
    """
    model = Reservation
    title = _("Reservation Information")
    permission_required = 'main.can_view_reservation'
    raise_exception = True
    extra_context = {'title': title}


class CustomerDetailView(PermissionRequiredMixin, generic.DetailView):
    """
    View for detail of customer
    Implements generic DetailView
    """
    model = Customer
    title = _("Customer Information")
    permission_required = 'main.can_view_customer'
    raise_exception = True
    extra_context = {'title': title}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        reservations = customer.reservation_set.all().order_by('-reservation_date_time')
        context['reservations'] = reservations
        context['reservation_count'] = reservations.count()
        context['active_reservation_count'] = reservations.filter(
            checkin__isnull=False,
            checkin__checkout__isnull=True,
        ).count()
        context['completed_reservation_count'] = reservations.filter(
            checkin__checkout__isnull=False,
        ).count()
        context['latest_reservation'] = reservations.first()
        return context


class StaffDetailView(PermissionRequiredMixin, generic.DetailView):
    """
    View for detail of staff
    Implements generic DetailView
    """
    model = Staff
    title = _("Staff Information")
    permission_required = 'main.can_view_staff_detail'
    extra_context = {'title': title}


class ProfileView(generic.TemplateView):
    template_name = 'profile.html'
    title = "Profile"
    extra_context = {'title': title}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            from payment.models import CheckIn, CheckOut

            user = self.request.user
            staff_profile = Staff.objects.filter(user=user).first()
            display_name = user.get_full_name() or user.username

            context['display_name'] = display_name
            context['staff_profile'] = staff_profile
            context['user_information'] = user
            context['role_label'] = 'Administrator' if user.is_superuser else 'Staff'
            context['reservations_handled'] = (
                Reservation.objects.filter(staff=staff_profile).count()
                if staff_profile else 0
            )
            context['checkins_processed'] = CheckIn.objects.filter(user=user).count()
            context['checkouts_processed'] = CheckOut.objects.filter(user=user).count()
        else:
            raise Http404("Your are not logged in.")
        return context


class GuestListView(PermissionRequiredMixin, generic.ListView):
    """
    View for list of guests present in hotel.
    """
    model = Customer
    paginate_by = 5
    allow_empty = True
    queryset = Customer.objects.all().filter(Q(reservation__checkin__isnull=False),
                                             Q(reservation__checkin__checkout__isnull=True))
    permission_required = 'main.can_view_customer'
    template_name = 'main/guest_list.html'
    title = 'Guest List View'
    context_object_name = 'guest_list'
    extra_context = {'title': title}
