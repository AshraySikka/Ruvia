from django.core.management.base import BaseCommand

from notify.scheduler import run_tick


class Command(BaseCommand):
    help = "Plan and send due reminders. Run every 10 minutes from a cron job."

    def handle(self, *args, **options):
        self.stdout.write(str(run_tick()))
