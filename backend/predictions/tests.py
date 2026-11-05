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
        self.assertIn("default_probability", response.data)
        self.assertIn("risk_level", response.data)
        self.assertIn("message", response.data)

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

    def test_predict_ad_hoc_without_application(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {
                "person_age": 25,
                "person_income": 30000,
                "person_home_ownership": "OWN",
                "person_emp_length": 2,
                "loan_intent": "EDUCATION",
                "loan_amnt": 5000,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        prediction = Prediction.objects.get()

        self.assertIsNone(prediction.credit_application)
        self.assertEqual(
            prediction.institution,
            self.institution,
        )

    def test_prediction_requires_features(self):
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse("prediction-list"),
            {"person_age": 25},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_applicant_cannot_run_prediction(self):
        self.client.force_authenticate(user=self.applicant_user)

        response = self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
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

    def test_agent_only_sees_institution_predictions(self):
        self.client.force_authenticate(user=self.agent)

        self.client.post(
            reverse("prediction-list"),
            {"credit_application": self.application.id},
            format="json",
        )

        self.client.force_authenticate(user=self.other_agent)

        response = self.client.get(reverse("prediction-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 0)

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
