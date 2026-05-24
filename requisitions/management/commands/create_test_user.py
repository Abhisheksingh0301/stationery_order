from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from requisitions.models import Department


class Command(BaseCommand):
    help = "Creates a test department user and a staff superuser."

    def handle(self, *args, **options):
        # Test department user
        username = "admin_dept"
        password = "admin123"
        dept_name = "Administration"

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, password=password)
            Department.objects.create(user=user, department_name=dept_name)
            self.stdout.write(self.style.SUCCESS(
                f"Test user created — username: {username}  password: {password}  department: {dept_name}"
            ))
        else:
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists."))

        # Staff superuser for accessing master pages
        staff_username = "admin"
        staff_password = "admin123"
        if not User.objects.filter(username=staff_username).exists():
            User.objects.create_superuser(username=staff_username, password=staff_password, email="")
            self.stdout.write(self.style.SUCCESS(
                f"Superuser created — username: {staff_username}  password: {staff_password}"
            ))
        else:
            self.stdout.write(self.style.WARNING(f"User '{staff_username}' already exists."))
