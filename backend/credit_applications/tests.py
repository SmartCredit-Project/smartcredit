from accounts.models import FinancialInstitution, User
from applicants.models import Applicant
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import CreditApplication


def application_payload(applicant, **overrides):
    payload = {
        "applicant": applicant.id,
        "person_age": 30,
        "person_income": 50000,
        "person_home_ownership": "RENT",
        "person_emp_length": 5,
        "loan_intent": "PERSONAL",
        "loan_amnt": 10000,
    }

    payload.update(overrides)

    return payload


class CreditApplicationTests(APITestCase):

    def setUp(self):
        self.institution = FinancialInstitution.objects.create(
            name="Banque Test",
            code="BQT",
        )
        self.other_institution = FinancialInstitution.objects.create(
            name="Autre Banque",
            code="AUT",
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
            institution=self.institution,
        )

        self.applicant = Applicant.objects.create(
            user=self.applicant_user,
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            institution=self.institution,
            created_by=self.agent,
        )

        self.other_applicant = Applicant.objects.create(
            first_name="Autre",
            last_name="Personne",
            email="autre@example.com",
            institution=self.other_institution,
            created_by=self.other_agent,
        )

    def test_agent_can_create_application(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(self.applicant),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        application = CreditApplication.objects.get()

        self.assertEqual(
            application.status,
            CreditApplication.Status.PENDING,
        )
        self.assertAlmostEqual(
            application.loan_percent_income,
            0.2,
        )
        self.assertEqual(
            application.created_by,
            self.agent,
        )
        self.assertEqual(
            application.institution,
            self.institution,
        )

    def test_applicant_can_create_own_application(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(self.applicant),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        application = CreditApplication.objects.get()

        self.assertEqual(
            application.institution,
            self.institution,
        )
        self.assertEqual(
            application.created_by,
            self.applicant_user,
        )

    def test_applicant_cannot_create_for_another_profile(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(self.other_applicant),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_agent_cannot_create_for_other_institution(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(self.other_applicant),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_agent_cannot_create_for_colleague_applicant(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        colleague_applicant = Applicant.objects.create(
            first_name="Collegue",
            last_name="Client",
            email="collegue.client@example.com",
            institution=self.institution,
            created_by=same_institution_agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(colleague_applicant),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_agent_cannot_reassign_to_other_institution_applicant(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.patch(
            reverse(
                "credit-application-detail",
                args=[application.id],
            ),
            {"applicant": self.other_applicant.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        application.refresh_from_db()
        self.assertEqual(application.applicant, self.applicant)

    def test_agent_cannot_reassign_to_colleague_applicant(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        colleague_applicant = Applicant.objects.create(
            first_name="Collegue",
            last_name="Client",
            email="collegue.client@example.com",
            institution=self.institution,
            created_by=same_institution_agent,
        )

        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.patch(
            reverse(
                "credit-application-detail",
                args=[application.id],
            ),
            {"applicant": colleague_applicant.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        application.refresh_from_db()
        self.assertEqual(application.applicant, self.applicant)

    def test_superadmin_reassignment_updates_institution(self):
        superadmin = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="MotDePasse!2026",
        )

        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=superadmin)

        response = self.client.patch(
            reverse(
                "credit-application-detail",
                args=[application.id],
            ),
            {"applicant": self.other_applicant.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        application.refresh_from_db()
        self.assertEqual(application.applicant, self.other_applicant)
        self.assertEqual(application.institution, self.other_institution)

    def test_application_features_are_validated(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("credit-application-list"),
            application_payload(
                self.applicant,
                person_age=15,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("person_age", response.data)

    def test_applicant_can_update_pending_application(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.applicant_user,
        )

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.patch(
            reverse(
                "credit-application-detail",
                args=[application.id],
            ),
            {"loan_amnt": 12000},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_applicant_cannot_update_analyzed_application(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.applicant_user,
            status=CreditApplication.Status.IN_ANALYSIS,
        )

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.patch(
            reverse(
                "credit-application-detail",
                args=[application.id],
            ),
            {"loan_amnt": 12000},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_status_transition(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.patch(
            reverse(
                "credit-application-status",
                args=[application.id],
            ),
            {"status": CreditApplication.Status.IN_ANALYSIS},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        application.refresh_from_db()

        self.assertEqual(
            application.status,
            CreditApplication.Status.IN_ANALYSIS,
        )

    def test_invalid_status_transition_is_rejected(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.patch(
            reverse(
                "credit-application-status",
                args=[application.id],
            ),
            {"status": CreditApplication.Status.ACCEPTED},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_assign_agent(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse(
                "credit-application-assign",
                args=[application.id],
            ),
            {"assigned_agent": self.agent.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        application.refresh_from_db()

        self.assertEqual(application.assigned_agent, self.agent)
        self.assertIsNotNone(application.assigned_at)

    def test_cannot_assign_agent_from_other_institution(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse(
                "credit-application-assign",
                args=[application.id],
            ),
            {"assigned_agent": self.other_agent.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_applicant_only_sees_own_applications(self):
        own_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        CreditApplication.objects.create(
            applicant=self.other_applicant,
            institution=self.other_institution,
            person_age=35,
            person_income=60000,
            person_home_ownership="OWN",
            person_emp_length=8,
            loan_intent="MEDICAL",
            loan_amnt=15000,
            created_by=self.other_agent,
        )

        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.get(reverse("credit-application-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            own_application.id,
        )

    def test_agent_only_sees_own_or_assigned_applications(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        own_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=50000,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=12000,
            created_by=same_institution_agent,
        )

        CreditApplication.objects.create(
            applicant=self.other_applicant,
            institution=self.other_institution,
            person_age=35,
            person_income=60000,
            person_home_ownership="OWN",
            person_emp_length=8,
            loan_intent="MEDICAL",
            loan_amnt=15000,
            created_by=self.other_agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("credit-application-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            own_application.id,
        )

    def test_agent_sees_assigned_application_from_colleague(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        application = CreditApplication.objects.create(
            applicant=self.applicant,
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

        response = self.client.get(
            reverse(
                "credit-application-detail",
                args=[application.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["id"], application.id)

    def test_agent_cannot_access_other_institution_application(self):
        application = CreditApplication.objects.create(
            applicant=self.other_applicant,
            institution=self.other_institution,
            person_age=35,
            person_income=60000,
            person_home_ownership="OWN",
            person_emp_length=8,
            loan_intent="MEDICAL",
            loan_amnt=15000,
            created_by=self.other_agent,
        )

        detail_url = reverse(
            "credit-application-detail",
            args=[application.id],
        )

        self.client.force_authenticate(user=self.agent)

        self.assertEqual(
            self.client.get(detail_url).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                detail_url,
                {"person_income": 70000},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(CreditApplication.objects.filter(pk=application.id).exists())
