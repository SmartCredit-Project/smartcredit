from accounts.models import FinancialInstitution, User
from credit_applications.models import CreditApplication
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Applicant


class ApplicantTests(APITestCase):

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

        self.other_agent = User.objects.create_user(
            username="autre.agent",
            email="autre.agent@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.other_institution,
        )

        self.applicant_user = User.objects.create_user(
            username="demandeur",
            email="demandeur@example.com",
            password="MotDePasse!2026",
            role=User.Role.APPLICANT,
        )

    def test_agent_can_create_applicant(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("applicant-list"),
            {
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean.dupont@example.com",
                "phone": "+257 12 34 56 78",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Applicant.objects.count(),
            1,
        )

        applicant = Applicant.objects.get()
        self.assertEqual(applicant.institution, self.institution)
        self.assertEqual(applicant.created_by, self.agent)

    def test_applicant_can_complete_own_profile(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("applicant-list"),
            {
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "demandeur@example.com",
                "institution": self.institution.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        applicant = Applicant.objects.get()

        self.assertEqual(applicant.user, self.applicant_user)
        self.assertEqual(applicant.institution, self.institution)

        self.applicant_user.refresh_from_db()
        self.assertEqual(
            self.applicant_user.institution,
            self.institution,
        )

    def test_applicant_cannot_create_second_profile(self):
        Applicant.objects.create(
            user=self.applicant_user,
            first_name="Jean",
            last_name="Dupont",
            email="demandeur@example.com",
        )

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("applicant-list"),
            {
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "autre.email@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_applicant_only_sees_own_profile(self):
        own_profile = Applicant.objects.create(
            user=self.applicant_user,
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            institution=self.institution,
        )

        Applicant.objects.create(
            first_name="Autre",
            last_name="Personne",
            email="autre@example.com",
            institution=self.institution,
        )

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.get(reverse("applicant-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            own_profile.id,
        )

    def test_agent_only_sees_own_applicants(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        Applicant.objects.create(
            first_name="Interne",
            last_name="Client",
            email="interne@example.com",
            institution=self.institution,
            created_by=self.agent,
        )

        Applicant.objects.create(
            first_name="Collegue",
            last_name="Client",
            email="collegue.client@example.com",
            institution=self.institution,
            created_by=same_institution_agent,
        )

        Applicant.objects.create(
            first_name="Externe",
            last_name="Client",
            email="externe@example.com",
            institution=self.other_institution,
            created_by=self.other_agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("applicant-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["email"],
            "interne@example.com",
        )

    def test_agent_sees_applicant_from_assigned_application(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        applicant = Applicant.objects.create(
            first_name="Assigne",
            last_name="Client",
            email="assigne@example.com",
            institution=self.institution,
            created_by=same_institution_agent,
        )

        CreditApplication.objects.create(
            applicant=applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=same_institution_agent,
            assigned_agent=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("applicant-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            applicant.id,
        )

    def test_applicant_cannot_change_institution_after_linking(self):
        applicant = Applicant.objects.create(
            user=self.applicant_user,
            first_name="Jean",
            last_name="Dupont",
            email="demandeur@example.com",
            institution=self.institution,
        )

        self.applicant_user.institution = self.institution
        self.applicant_user.save(update_fields=["institution"])

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.patch(
            reverse("applicant-detail", args=[applicant.id]),
            {"institution": self.other_institution.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        applicant.refresh_from_db()
        self.assertEqual(applicant.institution, self.institution)
