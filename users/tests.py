from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
)
class EmailTests(SimpleTestCase):
    def test_send_test_email_command(self):
        output = StringIO()

        call_command('send_test_email', 'recipient@example.com', stdout=output)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Munis Business Hub SMTP test')
        self.assertEqual(message.from_email, 'noreply@example.com')
        self.assertEqual(message.to, ['recipient@example.com'])
        self.assertIn('SMTP is configured correctly', message.body)
        self.assertIn('sent successfully', output.getvalue())
