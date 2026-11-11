import os
from io import StringIO
from unittest.mock import patch

from applicants.models import Applicant
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import FinancialInstitution, User


class AuthenticationTests(APITestCase):

    def setUp(self):
        self.institution = FinancialInstitution.objects.create(
            name="Banque Test",
            code="BQT",
        )

    def test_register_creates_applicant_account_with_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "nouveau@example.com",
                "first_name": "Nou",
                "last_name": "Veau",
                "password": "MotDePasse!2026",
                "password_confirm": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(email="nouveau@example.com")

        self.assertEqual(user.username, user.email)
        self.assertEqual(user.role, User.Role.APPLICANT)
        self.assertTrue(user.check_password("MotDePasse!2026"))

    def test_register_cannot_self_assign_admin_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "pirate@example.com",
                "password": "MotDePasse!2026",
                "password_confirm": "MotDePasse!2026",
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(email="pirate@example.com")
        self.assertEqual(user.role, User.Role.APPLICANT)

    def test_register_links_existing_applicant_profile(self):
        profile = Applicant.objects.create(
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            institution=self.institution,
        )

        response = self.client.post(
            reverse("register"),
            {
                "email": "jean.dupont@example.com",
                "password": "MotDePasse!2026",
                "password_confirm": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        profile.refresh_from_db()
        user = User.objects.get(email="jean.dupont@example.com")

        self.assertEqual(profile.user, user)
        self.assertEqual(user.institution, self.institution)

    def test_login_with_email_and_me(self):
        user = User.objects.create_user(
            username="agent",
            email="agent@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        response = self.client.post(
            reverse("login"),
            {
                "email": user.email,
                "password": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(
            response.data["user"]["role"],
            User.Role.CREDIT_AGENT,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(f"Bearer {response.data['access']}")
        )

        me_response = self.client.get(reverse("me"))

        self.assertEqual(
            me_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            me_response.data["email"],
            "agent@example.com",
        )

    def test_login_requires_valid_email(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "agent",
                "password": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class UserManagementTests(APITestCase):

    def setUp(self):
        self.institution = FinancialInstitution.objects.create(
            name="Banque Test",
            code="BQT",
        )
        self.other_institution = FinancialInstitution.objects.create(
            name="Autre Banque",
            code="AUT",
        )

        self.superadmin = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="MotDePasse!2026",
        )

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="MotDePasse!2026",
            role=User.Role.ADMIN,
            institution=self.institution,
        )

        self.agent = User.objects.create_user(
            username="agent",
            email="agent@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        self.other_agent = User.objects.create_user(
            username="agent2",
            email="agent2@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.other_institution,
        )

    def test_superadmin_sees_all_users(self):
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.get(reverse("user-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 4)

    def test_admin_only_sees_own_institution_users(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("user-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 2)

        emails = {row["email"] for row in response.data["results"]}

        self.assertIn("admin@example.com", emails)
        self.assertIn("agent@example.com", emails)
        self.assertNotIn("agent2@example.com", emails)

    def test_admin_cannot_create_another_admin(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("user-list"),
            {
                "email": "nouvel.admin@example.com",
                "role": User.Role.ADMIN,
                "password": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_creates_agent_in_own_institution(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("user-list"),
            {
                "email": "nouvel.agent@example.com",
                "role": User.Role.CREDIT_AGENT,
                "institution": self.other_institution.id,
                "password": "MotDePasse!2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(email="nouvel.agent@example.com")

        self.assertEqual(user.institution, self.institution)
        self.assertEqual(user.role, User.Role.CREDIT_AGENT)
        self.assertEqual(user.username, user.email)

    def test_admin_cannot_deactivate_another_admin(self):
        other_admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="MotDePasse!2026",
            role=User.Role.ADMIN,
            institution=self.institution,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(reverse("user-detail", args=[other_admin.id]))

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        other_admin.refresh_from_db()
        self.assertTrue(other_admin.is_active)

    def test_admin_deactivates_agent(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(reverse("user-detail", args=[self.agent.id]))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.agent.refresh_from_db()
        self.assertFalse(self.agent.is_active)


class AdminLoginTests(TestCase):

    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="MotDePasse!2026",
        )

    def test_admin_login_with_email(self):
        client = Client()

        response = client.post(
            "/admin/login/",
            {
                "username": "root@example.com",
                "password": "MotDePasse!2026",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            int(client.session["_auth_user_id"]),
            self.superadmin.id,
        )

    def test_admin_login_rejects_unknown_email(self):
        client = Client()

        response = client.post(
            "/admin/login/",
            {
                "username": "inconnu@example.com",
                "password": "MotDePasse!2026",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)


class EnsureSuperuserCommandTests(TestCase):

    def _environment(self, **overrides):
        values = {
            "DJANGO_SUPERUSER_EMAIL": "root@example.com",
            "DJANGO_SUPERUSER_PASSWORD": "MotDePasse!2026",
            "DJANGO_SUPERUSER_FIRST_NAME": "Super",
            "DJANGO_SUPERUSER_LAST_NAME": "Admin",
            "DJANGO_SUPERUSER_RESET_PASSWORD": "false",
        }
        values.update(overrides)

        return patch.dict(os.environ, values, clear=False)

    def test_creates_superuser_from_environment(self):
        with self._environment():
            call_command("ensure_superuser", stdout=StringIO())

        user = User.objects.get(email="root@example.com")

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Role.SUPERADMIN)
        self.assertEqual(user.first_name, "Super")
        self.assertEqual(user.last_name, "Admin")
        self.assertTrue(user.check_password("MotDePasse!2026"))

    def test_command_is_idempotent_and_keeps_password(self):
        with self._environment():
            call_command("ensure_superuser", stdout=StringIO())

        with self._environment(DJANGO_SUPERUSER_PASSWORD="AutreMotDePasse!2026"):
            call_command("ensure_superuser", stdout=StringIO())

        self.assertEqual(
            User.objects.filter(email="root@example.com").count(),
            1,
        )

        user = User.objects.get(email="root@example.com")
        self.assertTrue(user.check_password("MotDePasse!2026"))

    def test_adopts_existing_account_and_sets_environment_password(self):
        user = User.objects.create_user(
            username="existing",
            email="root@example.com",
            password="AncienMotDePasse!2026",
            role=User.Role.APPLICANT,
        )

        with self._environment():
            call_command("ensure_superuser", stdout=StringIO())

        user.refresh_from_db()

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.role, User.Role.SUPERADMIN)
        self.assertTrue(user.check_password("MotDePasse!2026"))

    def test_reset_password_flag_updates_existing_superuser(self):
        with self._environment():
            call_command("ensure_superuser", stdout=StringIO())

        with self._environment(
            DJANGO_SUPERUSER_PASSWORD="NouveauMotDePasse!2026",
            DJANGO_SUPERUSER_RESET_PASSWORD="true",
        ):
            call_command("ensure_superuser", stdout=StringIO())

        user = User.objects.get(email="root@example.com")
        self.assertTrue(user.check_password("NouveauMotDePasse!2026"))

    def test_skips_when_credentials_are_missing(self):
        with self._environment(
            DJANGO_SUPERUSER_EMAIL="",
            DJANGO_SUPERUSER_PASSWORD="",
        ):
            call_command("ensure_superuser", stdout=StringIO())

        self.assertFalse(User.objects.filter(email="root@example.com").exists())


class FinancialInstitutionIsolationTests(APITestCase):

    def setUp(self):
        self.institution = FinancialInstitution.objects.create(
            name="Banque Test",
            code="BQT",
        )
        self.other_institution = FinancialInstitution.objects.create(
            name="Autre Banque",
            code="AUT",
        )

        self.agent = User.objects.create_user(
            username="agent",
            email="agent@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        self.applicant = User.objects.create_user(
            username="demandeur",
            email="demandeur@example.com",
            password="MotDePasse!2026",
            role=User.Role.APPLICANT,
        )

        self.unaffiliated_agent = User.objects.create_user(
            username="sans.institution",
            email="sans.institution@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
        )

    def test_agent_only_sees_own_institution(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("institution-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.institution.id,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "institution-detail",
                    args=[self.other_institution.id],
                )
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_applicant_without_institution_sees_active_directory(self):
        self.client.force_authenticate(user=self.applicant)

        response = self.client.get(reverse("institution-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_staff_without_institution_sees_nothing(self):
        self.client.force_authenticate(user=self.unaffiliated_agent)

        response = self.client.get(reverse("institution-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
