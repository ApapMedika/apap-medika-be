# Generated by Django 4.2 on 2025-06-22 16:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("profiles", "0001_initial"),
        ("bill", "0001_initial"),
        ("hospitalization", "0001_initial"),
        ("insurance", "0001_initial"),
        ("pharmacy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="profiles.patient"
            ),
        ),
        migrations.AddField(
            model_name="bill",
            name="policy",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="insurance.policy",
            ),
        ),
        migrations.AddField(
            model_name="bill",
            name="prescription",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="pharmacy.prescription",
            ),
        ),
        migrations.AddField(
            model_name="bill",
            name="reservation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="hospitalization.reservation",
            ),
        ),
    ]
