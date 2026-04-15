from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0002_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="transaction",
            old_name="raw_gemini_response",
            new_name="raw_ocr_response",
        ),
        migrations.AlterField(
            model_name="transaction",
            name="raw_ocr_response",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text="Respuesta cruda del OCR para debugging",
            ),
        ),
    ]
