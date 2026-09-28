from django.db import transaction

from journal.exceptions import ConflictError
from .models import ScheduleEntry


def find_schedule_conflicts(*, offering, weekday, start_time, end_time, room, effective_from, effective_to, exclude_pk=None):
    queryset = ScheduleEntry.objects.filter(
        is_active=True,
        weekday=weekday,
        start_time__lt=end_time,
        end_time__gt=start_time,
        effective_from__lte=effective_to,
        effective_to__gte=effective_from,
    ).select_related("offering__group", "offering__teacher__user", "room")
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    conflicts = []
    for entry in queryset:
        types = []
        if entry.room_id == room.id:
            types.append("room")
        if entry.offering.teacher_id == offering.teacher_id:
            types.append("teacher")
        if entry.offering.group_id == offering.group_id:
            types.append("group")
        if types:
            conflicts.append({
                "entry_id": entry.id,
                "types": types,
                "group": entry.offering.group.code,
                "teacher": entry.offering.teacher.user.display_name,
                "room": str(entry.room),
                "start_time": str(entry.start_time),
                "end_time": str(entry.end_time),
            })
    return conflicts


@transaction.atomic
def save_schedule_entry(*, instance=None, **values):
    ScheduleEntry.objects.select_for_update().filter(
        weekday=values["weekday"],
        effective_from__lte=values["effective_to"],
        effective_to__gte=values["effective_from"],
    ).exists()
    conflicts = find_schedule_conflicts(
        offering=values["offering"],
        weekday=values["weekday"],
        start_time=values["start_time"],
        end_time=values["end_time"],
        room=values["room"],
        effective_from=values["effective_from"],
        effective_to=values["effective_to"],
        exclude_pk=instance.pk if instance else None,
    )
    if conflicts:
        raise ConflictError({"detail": "Schedule conflict detected.", "conflicts": conflicts})
    if instance:
        for field, value in values.items():
            setattr(instance, field, value)
        instance.save()
        return instance
    return ScheduleEntry.objects.create(**values)

