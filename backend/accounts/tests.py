from applicants.models import Applicant
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
