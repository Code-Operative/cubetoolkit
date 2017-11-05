import logging

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_safe
from django.db.models import F
import six

from toolkit.members.forms import (VolunteerForm, MemberFormWithoutNotes,
    TrainingRecordForm, GroupTrainingForm)
from toolkit.members.models import Member, Volunteer, TrainingRecord
from toolkit.diary.models import Role

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@permission_required('toolkit.read')
@require_safe
def view_volunteer_list(request):
    # Get all volunteers, sorted by name:
    volunteers = (Volunteer.objects.filter(active=True)
                  .order_by('member__name')
                  .select_related()
                  .prefetch_related('roles'))
    context = {
        'volunteers': volunteers,
        'default_mugshot': settings.DEFAULT_MUGSHOT,
    }
    return render(request, 'volunteer_list.html', context)


@permission_required('toolkit.read')
@require_safe
def view_volunteer_role_report(request):
    # Build dict of role names -> volunteer names
    role_vol_map = {}
    # Query for active volunteers, sorted by name
    volunteer_query = (Role.objects.filter(volunteer__active=True)
                                   .values_list('name', 'volunteer__id',
                                                'volunteer__member__name')
                                   .order_by('volunteer__member__name',
                                             'name'))

    for role, vol_id, vol_name in volunteer_query:
        role_vol_map.setdefault(role, []).append(vol_name)

    # Now sort role_vol_map by role name:
    role_vol_map = sorted(
        six.iteritems(role_vol_map),
        key=lambda role_name_tuple: role_name_tuple[0]
    )
    # (now got a list  of (role, (name1, name2, ...)) tuples, rather than a
    # dict, but that's fine)

    context = {
        'role_vol_map': role_vol_map,
    }
    return render(request, 'volunteer_role_report.html', context)


@permission_required('toolkit.read')
@require_safe
def select_volunteer(request, action, active=True):
    # This view is called to retire / unretire a volunteer. It presents a list
    # of all volunteer names and a button. If the view is called with
    # "action=retire" in the url then it shows a "retire" button linked to the
    # retire url, and if it's called with "action=unretire" it shows a link to
    # the unretire url.
    #
    # The selection of volunteers (retired vs unretired) is decided by the
    # "active" parameter to this method, which is set by the url route,
    # depending on which view was used. This is probably not the simplest way
    # to do this...
    action_urls = {
        'retire': reverse('inactivate-volunteer'),
        'unretire': reverse('activate-volunteer'),
    }

    assert action in action_urls
    assert isinstance(active, bool)

    volunteers = Volunteer.objects.filter(active=active).order_by(
        'member__name').select_related()

    context = {
        'volunteers': volunteers,
        'action': action,
        'action_url': action_urls[action],
    }

    return render(request, 'select_volunteer.html', context)


@permission_required('toolkit.write')
@require_POST
def activate_volunteer(request, set_active=True):
    # Sets the 'active' value for the volunteer with the id passed  in the
    # 'volunteer' parameter of the POST request

    vol_pk = request.POST.get('volunteer', None)

    vol = get_object_or_404(Volunteer, id=vol_pk)

    assert isinstance(set_active, bool)
    vol.active = set_active
    vol.save()

    logger.info(u"Set volunteer.active to {0} for volunteer {1}"
                .format(str(set_active), vol_pk))
    messages.add_message(request, messages.SUCCESS, u"{0} volunteer {1}"
                         .format(u"Unretired" if set_active else u"Retired",
                                 vol.member.name))

    return HttpResponseRedirect(reverse("view-volunteer-list"))


@permission_required('toolkit.write')
def edit_volunteer(request, volunteer_id, create_new=False):
    # If called from the "add" url, then create_new will be True. If called
    # from the edit url then it'll be False

    # Depending on which way this method was called, either create a totally
    # new volunteer object with default values (add) or load the volunteer
    # object with the given volunteer_id from the database:
    if not create_new:
        # Called from "edit" url
        volunteer = get_object_or_404(Volunteer, id=volunteer_id)
        member = volunteer.member
        new_training_record = TrainingRecord(volunteer=volunteer)
    else:
        # Called from "add" url
        volunteer = Volunteer()
        member = Member()
        volunteer.member = Member()
        new_training_record = None

    # Now, if the view was loaded with "GET" then display the edit form, and
    # if it was called with POST then read the updated volunteer data from the
    # form data and update and save the volunteer object:
    if request.method == 'POST':
        # Three forms, one for each set of data
        vol_form = VolunteerForm(
            request.POST,
            request.FILES,
            instance=volunteer
        )
        mem_form = MemberFormWithoutNotes(
            request.POST,
            instance=member
        )
        if vol_form.is_valid() and mem_form.is_valid():
            logger.info(u"Saving changes to volunteer '{0}' (id: {1})".format(
                volunteer.member.name, str(volunteer.pk)))
            mem_form.save()
            volunteer.member = member
            vol_form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                u"{0} volunteer '{1}'".format(
                    u"Created" if create_new else u"Updated", member.name
                )
            )
            # Go to the volunteer list view:
            return HttpResponseRedirect(reverse("view-volunteer-list"))
    else:
        vol_form = VolunteerForm(instance=volunteer)
        mem_form = MemberFormWithoutNotes(instance=volunteer.member)

    if new_training_record:
        training_record_form = TrainingRecordForm(
           prefix="training", instance=new_training_record)
    else:
        training_record_form = None

    context = {
        'pagetitle': 'Add Volunteer' if create_new else 'Edit Volunteer',
        'default_mugshot': settings.DEFAULT_MUGSHOT,
        'volunteer': volunteer,
        'vol_form': vol_form,
        'mem_form': mem_form,
        'training_record_form': training_record_form,
    }
    return render(request, 'form_volunteer.html', context)


@permission_required('toolkit.write')
@require_POST
def add_volunteer_training_record(request, volunteer_id):
    volunteer = get_object_or_404(Volunteer, id=volunteer_id)
    new_record = TrainingRecord(volunteer=volunteer)

    record_form = TrainingRecordForm(
        request.POST,
        instance=new_record,
        prefix="training",
    )

    if not volunteer.active:
        response = {
            'succeeded': False,
            'errors': 'volunteer is not active'
        }
        return JsonResponse(response)
    elif record_form.is_valid():
        record_form.save()
        logger.info(u"Added training record {0} for volunteer '{0}'".format(
            new_record.id, volunteer.member.name))
        # Now make sure the volunteer has that role selected:
        volunteer.roles.add(new_record.role)

        response = {
            'succeeded': True,
            'id': new_record.id,
            'role': str(new_record.role),
            'training_date': new_record.training_date,
            'trainer': new_record.trainer,
            'notes': new_record.notes,
        }
        return JsonResponse(response)
    else:
        response = {
            'succeeded': False,
            'errors': record_form.errors
        }
        return JsonResponse(response)


@permission_required('toolkit.write')
@require_POST
def delete_volunteer_training_record(request, training_record_id):
    record = get_object_or_404(TrainingRecord, id=training_record_id)

    if not record.volunteer.active:
        logger.error(u"Tried to delete training record for inactive volunteer")
        return HttpResponse("Can't delete record for inactive volunteer",
            status=403, content_type="text/plain")

    logger.info(u"Deleting training_record '{0}' for volunteer '{1}'"
        .format(record.id, record.volunteer.member.name))
    record.delete()
    return HttpResponse("OK", content_type="text/plain")


@permission_required('toolkit.read')
@require_safe
def view_volunteer_training_records(request):
    records = (TrainingRecord.objects.filter(volunteer__active=True)
        .filter(volunteer__roles=F('role'))
        .select_related()
        )
    role_map = {}
    for record in records:
        vol_map = role_map.setdefault(record.role, {})
        current = vol_map.get(record.volunteer, None)
        if not current or record.training_date > current.training_date:
            vol_map[record.volunteer] = record
    # Now sort by role ID / volunteer Name, using an obnoxiously complicated
    # comprehension (sorry):
    role_map_list = sorted(
        [
            (role, sorted(
                    [(vol, record) for vol, record in vol_map.items()],
                    key=lambda v_r: v_r[0].member.name
                   )
            ) for role, vol_map in role_map.items()
        ],
        key=lambda r_l: r_l[0].name
    )

    context = {
        'report_data': role_map_list,
    }
    return render(request, 'volunteer_training_report.html', context)


@permission_required('toolkit.write')
def add_volunteer_training_group_record(request):
    if request.method == 'POST':
        form = GroupTrainingForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            trainer = form.cleaned_data['trainer']
            members = form.cleaned_data['volunteers']
            logger.info(
                "Bulk add training records for role '%s', trainer '%s', "
                " members '%s'" % (role, trainer, members))

            for member in members:
                volunteer = member.volunteer
                record = TrainingRecord(
                    role=role,
                    trainer=trainer,
                    training_date=form.cleaned_data['training_date'],
                    notes=form.cleaned_data['notes'],
                    volunteer=volunteer
                )
                record.save()
                volunteer.roles.add(role)
            messages.add_message(request, messages.SUCCESS,
                                 u"Added %d training records for %s" %
                                 (len(form.cleaned_data['volunteers']),
                                 form.cleaned_data['role']))
            return HttpResponseRedirect(
                reverse('add-volunteer-training-group-record'))
    else:  # i.e. request.method == 'GET':
        form = GroupTrainingForm()

    context = {
        'form': form,
    }
    return render(request, 'form_group_training.html', context)
