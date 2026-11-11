from accounts.models import FeatureFlag, FinancialInstitution, User
from applicants.models import Applicant
from credit_applications.models import CreditApplication
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ModelVersion, Prediction


class PredictionTests(APITestCase):

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

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="MotDePasse!2026",
            role=User.Role.ADMIN,
            institution=self.institution,
        )

        self.superadmin = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="MotDePasse!2026",
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
        )

        self.other_applicant_user = User.objects.create_user(
            username="autre.demandeur",
            email="autre.demandeur@example.com",
            password="MotDePasse!2026",
            role=User.Role.APPLICANT,
            institution=self.other_institution,
        )

        self.other_applicant = Applicant.objects.create(
            user=self.other_applicant_user,
            first_name="Autre",
            last_name="Personne",
            email="autre.personne@example.com",
            institution=self.other_institution,
        )

        self.application = CreditApplication.objects.create(
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

        self.other_application = CreditApplication.objects.create(
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

    def test_predict_from_credit_application(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIn("prediction", response.data)
        self.assertIn("result", response.data)
        self.assertIn("default_probability", response.data)
        self.assertIn("default_probability_percentage", response.data)
        self.assertIn("risk_level", response.data)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["decision_threshold"], 0.59)
        self.assertEqual(
            response.data["default_probability_percentage"],
            round(response.data["default_probability"] * 100, 2),
        )

        self.assertEqual(
            Prediction.objects.count(),
            1,
        )

        prediction = Prediction.objects.get()

        self.assertEqual(
            prediction.credit_application,
            self.application,
        )
        self.assertEqual(
            prediction.institution,
            self.institution,
        )

        self.assertEqual(
            prediction.model_version.version,
            "1.0.0",
        )

        self.assertTrue(ModelVersion.objects.filter(is_active=True).exists())

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            CreditApplication.Status.ANALYZED,
        )

    def test_prediction_requires_credit_application(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("credit_application", response.data)

    def test_prediction_with_unknown_application(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": 999999},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("credit_application", response.data)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_prediction_is_rejected_with_zero_income(self):
        application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=30,
            person_income=0,
            person_home_ownership="RENT",
            person_emp_length=5,
            loan_intent="PERSONAL",
            loan_amnt=10000,
            created_by=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("credit_application", response.data)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_prediction_cannot_be_created_twice(self):
        self.client.force_authenticate(user=self.agent)

        first_response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            second_response.data["prediction"],
            first_response.data["id"],
        )
        self.assertEqual(Prediction.objects.count(), 1)

    def test_applicant_can_predict_own_application(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Prediction.objects.count(), 1)

    def test_applicant_cannot_predict_other_applicant_application(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.other_application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(Prediction.objects.count(), 0)

    def test_admin_can_predict_institution_application(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_superadmin_can_predict_any_application(self):
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.other_application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Prediction.objects.get().institution,
            self.other_institution,
        )

    def test_agent_cannot_predict_other_institution_application(self):
        self.client.force_authenticate(user=self.other_agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_feature_flag_can_disable_predictions(self):
        FeatureFlag.objects.update_or_create(
            key="predictions",
            defaults={
                "name": "Prédictions",
                "is_enabled": False,
            },
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(Prediction.objects.count(), 0)

    def test_latest_application_prediction_endpoint(self):
        self.client.force_authenticate(user=self.agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        response = self.client.get(
            reverse(
                "credit-application-prediction",
                args=[self.application.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["credit_application"],
            self.application.id,
        )

    def test_agent_only_sees_own_or_assigned_predictions(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        colleague_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=31,
            person_income=52000,
            person_home_ownership="RENT",
            person_emp_length=6,
            loan_intent="PERSONAL",
            loan_amnt=11000,
            created_by=same_institution_agent,
        )

        self.client.force_authenticate(user=self.agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.client.force_authenticate(user=same_institution_agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": colleague_application.id},
            format="json",
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("prediction-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)

    def test_agent_cannot_predict_colleague_application(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        colleague_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=31,
            person_income=52000,
            person_home_ownership="RENT",
            person_emp_length=6,
            loan_intent="PERSONAL",
            loan_amnt=11000,
            created_by=same_institution_agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": colleague_application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_agent_can_predict_assigned_colleague_application(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        assigned_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=31,
            person_income=52000,
            person_home_ownership="RENT",
            person_emp_length=6,
            loan_intent="PERSONAL",
            loan_amnt=11000,
            created_by=same_institution_agent,
            assigned_agent=self.agent,
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": assigned_application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_dashboard_statistics(self):
        self.client.force_authenticate(user=self.agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        response = self.client.get(reverse("dashboard-overview"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["predictions"]["total"],
            1,
        )

    def test_agent_dashboard_excludes_colleague_data(self):
        same_institution_agent = User.objects.create_user(
            username="collegue",
            email="collegue@example.com",
            password="MotDePasse!2026",
            role=User.Role.CREDIT_AGENT,
            institution=self.institution,
        )

        colleague_application = CreditApplication.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            person_age=31,
            person_income=52000,
            person_home_ownership="RENT",
            person_emp_length=6,
            loan_intent="PERSONAL",
            loan_amnt=11000,
            created_by=same_institution_agent,
        )

        self.client.force_authenticate(user=self.agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.client.force_authenticate(user=same_institution_agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": colleague_application.id},
            format="json",
        )

        self.client.force_authenticate(user=self.agent)

        response = self.client.get(reverse("dashboard-overview"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["users"]["total"], 1)
        self.assertEqual(response.data["applicants"]["total"], 1)
        self.assertEqual(response.data["applications"]["total"], 1)
        self.assertEqual(response.data["predictions"]["total"], 1)
