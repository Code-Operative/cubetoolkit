import smtplib
import email.parser
import email.header

import six
from mock import patch, call

from django.conf import settings
from django.test import TestCase
from django.core import mail

import toolkit.members.tasks
from toolkit.members.models import Member
from .common import MembersTestsMixin


class TestMemberMailoutTask(MembersTestsMixin, TestCase):

    def setUp(self):
        super(TestMemberMailoutTask, self).setUp()
        self.assertTrue(self.client.login(
            username="admin", password="T3stPassword!"))

    def _assert_mail_as_expected(self, msgstr, is_utf8, from_addr, dest_addr,
                                 body_contains, expected_subject):
        message = email.parser.Parser().parsestr(msgstr)

        self.assertEqual(message.get_content_type(), 'text/plain')
        self.assertFalse(message.is_multipart())
        # It's always UTF-8, even if the content is ASCII:
        self.assertEqual(message.get_charsets(), ["utf-8"])
        if is_utf8:
            self.assertEqual(message['Content-Transfer-Encoding'], '8bit')
        else:
            self.assertEqual(message['Content-Transfer-Encoding'], '7bit')
        self.assertEqual(message['From'], from_addr)
        self.assertEqual(message['To'], dest_addr)

        body = message.get_payload()
        if six.PY2:
            # message.get_payload has apparently changed in py3:
            body = body.decode("utf-8")
        subject = email.header.decode_header(message['Subject'])

        self.assertIn(body_contains, body)
        subject = subject[0][0].decode(subject[0][1]) if subject[
            0][1] else subject[0][0]
        self.assertEqual(subject, expected_subject)

    def _assert_mail_sent(self, result, current_task_mock,
                          subject, body, is_utf8):
        current_task_mock.update_state.assert_has_calls([
            call(state='PROGRESS017', meta={'total': 6, 'sent': 1}),
            call(state='PROGRESS034', meta={'total': 6, 'sent': 2}),
            call(state='PROGRESS051', meta={'total': 6, 'sent': 3}),
            call(state='PROGRESS067', meta={'total': 6, 'sent': 4}),
            call(state='PROGRESS084', meta={'total': 6, 'sent': 5}),
            # 101% complete! (ahem)
            call(state='PROGRESS101', meta={'total': 6, 'sent': 6})
        ])

        # Sent 6 mails, plus one summary:
        self.assertEqual(len(mail.outbox), 7)

        # Validate summary:
        summary_mail = mail.outbox[6]
        self.assertEqual(summary_mail.from_email,
                         settings.VENUE['mailout_from_address'])
        self.assertEqual(summary_mail.to,
                         [settings.VENUE['mailout_delivery_report_to']])
        # Check mail twice, to check for each bit of expected text in the body;
        # The mail count:
        self._assert_mail_as_expected(
            str(summary_mail.message()),
            is_utf8,
            settings.VENUE['mailout_from_address'],
            settings.VENUE['mailout_delivery_report_to'],
            u"6 copies of the following were sent out on Cube members list",
            subject
        )
        # And the actual body text:
        self._assert_mail_as_expected(
            str(summary_mail.message()),
            is_utf8,
            settings.VENUE['mailout_from_address'],
            settings.VENUE['mailout_delivery_report_to'],
            body,
            subject
        )

        # Reported success:
        # False => no error, 6 == sent count:
        self.assertEqual(result, (False, 6, 'Ok'))

    @patch("toolkit.members.tasks.current_task")
    def test_send_unicode(self, current_task_mock):
        subject = u"The Subject \u2603!"
        body = u"The Body!\nThat will be \u20ac1, please\nTa \u2603!"
        result = toolkit.members.tasks.send_mailout(subject, body)
        self._assert_mail_sent(result, current_task_mock,
                               subject, body, True)

    @patch("toolkit.members.tasks.current_task")
    def test_send_ascii(self, current_task_mock):
        subject = u"The Subject!"
        body = u"The Body!\nThat will be $1, please\nTa!"
        result = toolkit.members.tasks.send_mailout(subject, body)
        self._assert_mail_sent(result, current_task_mock,
                               subject, body, False)

    @patch("toolkit.members.tasks.current_task")
    def test_send_iso88591_subj(self, current_task_mock):
        subject = u"The \xa31 Subject!"
        body = u"The Body!\nThat will be $1, please\nTa!"
        result = toolkit.members.tasks.send_mailout(subject, body)
        self._assert_mail_sent(result, current_task_mock,
                               subject, body, False)

    @patch("django.core.mail.get_connection")
    @patch("toolkit.members.tasks.current_task")
    def test_connect_fail(self, current_task_mock, connection_mock):
        connection_mock.return_value.open.side_effect = \
            smtplib.SMTPConnectError("Blah", 101)

        result = toolkit.members.tasks.send_mailout(
            u"The \xa31 Subject!", u"The Body!\nThat will be $1, please\nTa!"
        )

        self.assertEqual(
            result,
            (True, 0, "Failed to connect to SMTP server: ('Blah', 101)"))

    @patch("django.core.mail.backends.base.BaseEmailBackend.close")
    @patch("toolkit.members.tasks.current_task")
    def test_disconnect_fail(self, current_task_mock, close_mock):
        subject = u"The Subject \u2603!"
        body = u"The Body!\nThat will be \u20ac1, please\nTa \u2603!"
        close_mock.side_effect = (
                smtplib.SMTPServerDisconnected("Already disconnected?"))

        result = toolkit.members.tasks.send_mailout(subject, body)
        self._assert_mail_sent(result, current_task_mock,
                               subject, body, True)

        close_mock.assert_called_once()

    @patch("django.core.mail.get_connection")
    @patch("toolkit.members.tasks.current_task")
    def test_send_fail(self, current_task_mock, connection_mock):
        exception = smtplib.SMTPException("Something failed", 101)
        connection_mock.return_value.send_messages.side_effect = exception

        result = toolkit.members.tasks.send_mailout(
            u"The \xa31 Subject!", u"The Body!\nThat will be $1, please\nTa!"
        )

        # Overall, operation succeeded:
        self.assertEqual((False, 6, "Ok"), result)

        # Check errors are in the report message:
        report = connection_mock.return_value.send_messages.call_args[0][0][0]
        expected = "6 errors:\n" + "\n".join([str(exception)] * 6)
        self.assertIn(expected, report.body)

    @patch("django.core.mail.get_connection")
    @patch("toolkit.members.tasks.current_task")
    def test_send_fail_disconnected(self, current_task_mock, connection_mock):
        connection_mock.return_value.send_messages.side_effect = (
                smtplib.SMTPServerDisconnected("Something failed"))

        result = toolkit.members.tasks.send_mailout(
            u"The \xa31 Subject!", u"The Body!\nThat will be $1, please\nTa!"
        )

        self.assertEqual(
            result, (True, 0, "Mailout job died: 'Something failed'"))

    @patch("django.core.mail.get_connection")
    @patch("toolkit.members.tasks.current_task")
    def test_random_error(self, current_task_mock, connection_mock):
        # Test a non SMTP error
        connection_mock.return_value.send_messages.side_effect = (
            IOError("something"))

        result = toolkit.members.tasks.send_mailout(
            u"The \xa31 Subject!", u"The Body!\nThat will be $1, please\nTa!"
        )

        # Overall, operation succeeded:
        self.assertEqual(result, (True, 0, "Mailout job died: 'something'"))

    @patch("toolkit.members.tasks.current_task")
    def test_no_recipients(self, current_task_mock):
        Member.objects.all().delete()
        # Test a non SMTP error
        result = toolkit.members.tasks.send_mailout(
            u"The \xa31 Subject!", u"The Body!\nThat will be $1, please\nTa!"
        )

        self.assertEqual(result, (True, 0, "No recipients found"))

    @patch("toolkit.members.tasks.current_task")
    def test_send_unicode_email_address(self, current_task_mock):
        subject = u"The Subject \u2603!"
        body = u"The Body!\nThat will be \u20ac1, please\nTa \u2603!"

        member = Member.objects.get(id=1)
        member.email = u"\u0205ne@\u0205xample.com"
        member.save()

        result = toolkit.members.tasks.send_mailout(subject, body)
        self._assert_mail_sent(result, current_task_mock,
                               subject, body, True)
        self.assertEqual(mail.outbox[0].to, [u'\u0205ne@\u0205xample.com'])

