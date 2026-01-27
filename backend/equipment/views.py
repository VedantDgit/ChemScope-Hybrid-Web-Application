import os
import pandas as pd
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from reportlab.pdfgen import canvas   # ✅ FIXED
from pypdf import PdfReader, PdfWriter
from .models import Dataset


@api_view(['POST'])
def upload_csv(request):
    try:
        # ---------- FILE CHECK ----------
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=400)

        # ---------- SAVE DATASET ----------
        ds = Dataset(filename=file.name)
        ds.file.save(file.name, file)

        # ---------- READ CSV ----------
        df = pd.read_csv(ds.file.path)

        REQUIRED_COLUMNS = ['Type', 'Pressure', 'Temperature']
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                return Response(
                    {'error': f'Missing column: {col}'},
                    status=400
                )

        # ---------- SUMMARY ----------
        summary = {
            "total_rows": int(len(df)),
            "average_pressure": round(df['Pressure'].mean(), 2),
            "average_temperature": round(df['Temperature'].mean(), 2),
            "type_distribution": df['Type'].value_counts().to_dict()
        }

        ds.summary = summary
        ds.save()

        # ---------- PDF GENERATION ----------
        pdf_path = generate_pdf(summary, ds.id)

        protected_pdf_path = protect_pdf(
            input_pdf_path=pdf_path,
            password="chem123",
            dataset_id=ds.id
        )

        ds.report = protected_pdf_path
        ds.save()

        report_url = request.build_absolute_uri(protected_pdf_path)

        return Response({
            "message": "CSV uploaded successfully",
            "data": summary,
            "report": report_url,
            "dataset_id": ds.id
        })

    except Exception as e:
        print("UPLOAD ERROR:", str(e))  # 🔥 SEE THIS IN TERMINAL
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ---------- PDF PROTECTION ----------
def protect_pdf(input_pdf_path, password, dataset_id):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)

    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    protected_path = os.path.join(
        reports_dir,
        f"report_{dataset_id}_protected.pdf"
    )

    with open(protected_path, "wb") as f:
        writer.write(f)

    return f"{settings.MEDIA_URL}reports/report_{dataset_id}_protected.pdf"


# ---------- PDF CREATION ----------
def generate_pdf(data, dataset_id):
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    path = os.path.join(reports_dir, f"report_{dataset_id}.pdf")

    c = canvas.Canvas(path)
    y = 800
    c.setFont('Helvetica-Bold', 14)
    c.drawString(50, y, "Chemical Equipment Data Report")
    y -= 40

    c.setFont('Helvetica', 11)
    for key, value in data.items():
        c.drawString(50, y, f"{key}: {value}")
        y -= 22

    c.save()
    return path


# ---------- HISTORY ----------
@api_view(['GET'])
def datasets_list(request):
    page_size = int(request.GET.get('page_size', 5))
    qs = Dataset.objects.order_by('-uploaded_at')[:page_size]

    items = []
    for d in qs:
        items.append({
            'id': d.id,
            'filename': d.filename,
            'uploaded_at': d.uploaded_at,
            'summary': d.summary,
            'report_url': request.build_absolute_uri(d.report) if d.report else None,
        })

    return Response({'items': items})


# ---------- PREVIEW ----------
@api_view(['GET'])
def dataset_preview(request, pk):
    try:
        ds = Dataset.objects.get(pk=pk)
        df = pd.read_csv(ds.file.path, nrows=10)

        return Response({
            'columns': list(df.columns),
            'rows': df.fillna('').to_dict(orient='records')
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
