from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from register.models import UserProfile

DEMO_USERS = [
    {
        "name": "Gianne Cruz",
        "email": "gianne@cebucity.ph",
        "phone": "+63 917 554 8921",
        "barangay": "Tisa",
        "avatar": "GC",
        "password": "cebuwirehazard2026",
    },
    {
        "name": "Eduardo Morales",
        "email": "morales.cebu@gmail.com",
        "phone": "+63 920 882 1042",
        "barangay": "Lahug",
        "avatar": "EM",
        "password": "cebuwirehazard2026",
    },
    {
        "name": "Lourdes Alcantara",
        "email": "lourdes.alcantara@yahoo.com",
        "phone": "+63 918 331 4455",
        "barangay": "Guadalupe",
        "avatar": "LA",
        "password": "cebuwirehazard2026",
    },
]

class Command(BaseCommand):
    help = "Seeds demo users and profiles into the database."

    def handle(self, *args, **options):
        for data in DEMO_USERS:
            email = data["email"].lower()
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    "email": email,
                    "first_name": data["name"],
                },
            )
            user.set_password(data["password"])
            user.first_name = data["name"]
            user.email = email
            user.save()

            profile, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": data["name"],
                    "phone": data["phone"],
                    "barangay": data["barangay"],
                    "avatar": data["avatar"],
                },
            )

            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{status} demo user: {data['name']} ({email})"))

        self.stdout.write(self.style.SUCCESS("All demo users seeded successfully."))
