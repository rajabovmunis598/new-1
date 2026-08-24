from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email


class Command(BaseCommand):
    help = 'Send one email through the configured Django email backend.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Email address that receives the test message')

    def handle(self, *args, **options):
        recipient = options['recipient'].strip()
        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError(f'Invalid recipient email: {recipient}') from exc

        try:
            sent_count = send_mail(
                subject='Munis Business Hub SMTP test',
                message=(
                    'SMTP is configured correctly for Munis Business Hub.\n\n'
                    'This is an automated test message.'
                ),
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'Could not send the SMTP test email: {exc}') from exc

        if sent_count != 1:
            raise CommandError('The email backend did not confirm that the message was sent.')

        self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {recipient}.'))
